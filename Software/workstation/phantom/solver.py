import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu

from .materials import conductivity
from .meshing import make_mesh
from .sources import AXIAL_OFFSET, SOURCE_SPREAD


class PhantomSolver:
    """P1 tetrahedral FEM: integral grad(v).sigma.grad(phi) = v.T I.

    Exterior is insulating (natural zero-flux). Balanced current dipoles ensure
    compatibility; pinning node zero removes only the constant-potential gauge.
    Four independent 1 microamp dipoles form a reusable linear lead-field basis.
    """

    def __init__(self, sectors=32, layers=13, materials=None):
        started = time.perf_counter()
        self.mesh = mesh = make_mesh(sectors, layers)
        xyz = mesh.nodes[mesh.elements]
        shape = np.concatenate([np.ones((*xyz.shape[:2], 1)), xyz], axis=2)
        gradients = np.linalg.inv(shape)[:, 1:, :]
        self.volumes = np.abs(np.linalg.det(xyz[:, 1:] - xyz[:, :1])) / 6
        if np.any(self.volumes <= 0):
            raise ValueError('Degenerate finite element')
        sigma, self.tissue = conductivity(mesh, materials)
        local = np.einsum('eai,ea,eaj,e->eij', gradients, sigma,
                          gradients, self.volumes)
        rows = np.repeat(mesh.elements, 4, axis=1).ravel()
        cols = np.tile(mesh.elements, (1, 4)).ravel()
        self.stiffness = coo_matrix((local.ravel(), (rows, cols)),
                                    shape=(len(mesh.nodes), len(mesh.nodes))).tocsc()
        # Smooth distributed dipoles avoid mesh-dependent nodal point singularities.
        self.rhs = np.zeros((len(mesh.nodes), 4))
        self.source_positions = []
        nodal_volume = np.bincount(mesh.elements.ravel(),
                                  weights=np.repeat(self.volumes / 4, 4),
                                  minlength=len(mesh.nodes))
        muscle_nodes = (np.linalg.norm(mesh.nodes[:, :2], axis=1) > mesh.anatomy.bone_radius + 1e-10) & (np.linalg.norm(mesh.nodes[:, :2], axis=1) < mesh.anatomy.muscle_radius - 1e-10)
        for source in range(4):
            angle = source * np.pi / 2
            center = np.array([mesh.anatomy.source_radius * np.cos(angle), mesh.anatomy.source_radius * np.sin(angle), 0.])
            self.source_positions.append(center)
            for sign in [-1, 1]:
                position = center + np.array([0, 0, sign * AXIAL_OFFSET])
                weight = np.exp(-np.sum((mesh.nodes - position) ** 2, axis=1) / (2 * SOURCE_SPREAD ** 2)) * muscle_nodes * nodal_volume
                self.rhs[:, source] += sign * 1e-6 * weight / weight.sum()
        self.basis = np.zeros_like(self.rhs)
        factor = splu(self.stiffness[1:, 1:])
        self.basis[1:] = factor.solve(self.rhs[1:])
        # Display relative to the volume-weighted mean, avoiding a misleading
        # all-positive field caused by the arbitrary pinned endpoint reference.
        self.basis -= (nodal_volume @ self.basis / nodal_volume.sum())[None, :]
        residual = self.stiffness @ self.basis - self.rhs
        self.residual = float(np.linalg.norm(residual) / np.linalg.norm(self.rhs))
        self.elapsed_ms = (time.perf_counter() - started) * 1000

    def surface_sample(self, angle, axial):
        """Interpolate P1 values on the actual outer triangular mesh faces."""
        m = self.mesh
        u = (angle % 360) / 360 * m.sectors
        j = int(u) % m.sectors
        k = (j + 1) % m.sectors
        u -= int(u)
        v = np.clip((axial + m.length / 2) / m.length * (m.layers - 1), 0, m.layers - 1 - 1e-10)
        layer = int(v)
        v -= layer
        if j > k:
            j, k, u = k, j, 1 - u
        outer = m.per_slice - m.sectors
        a = layer * m.per_slice + outer + j
        b = layer * m.per_slice + outer + k
        A, B = a + m.per_slice, b + m.per_slice
        if u >= v:
            return (1-u)*self.basis[a] + (u-v)*self.basis[b] + v*self.basis[B]
        return (1-v)*self.basis[a] + (v-u)*self.basis[A] + u*self.basis[B]

    def lead_field(self, angle=0., axial_mm=0., spacing_mm=20., channels=4):
        """Equally spaced bipolar pairs; mV per 1 µA source (N × 4)."""
        if channels not in (2, 4, 8, 16):
            raise ValueError('Electrode pair count must be 2, 4, 8, or 16')
        half = spacing_mm / 2000
        z = axial_mm / 1000
        return np.array([1000 * (self.surface_sample(angle + c*360/channels, z + half)
                                - self.surface_sample(angle + c*360/channels, z - half))
                         for c in range(channels)])

    def surface_field(self, source):
        m = self.mesh
        nodes = []
        for layer in range(m.layers):
            for sector in range(m.sectors):
                index = layer*m.per_slice + m.per_slice-m.sectors + sector
                nodes.append([*m.nodes[index], self.basis[index, source]*1000])
        return np.asarray(nodes)
