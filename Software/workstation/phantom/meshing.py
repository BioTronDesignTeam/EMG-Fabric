from dataclasses import dataclass

import numpy as np

from .anatomy import DEFAULT_ANATOMY, Anatomy


@dataclass
class Mesh:
    nodes: np.ndarray
    elements: np.ndarray
    sectors: int
    layers: int
    per_slice: int
    anatomy: Anatomy = DEFAULT_ANATOMY

    @property
    def radius(self): return self.anatomy.radius

    @property
    def length(self): return self.anatomy.length


def make_mesh(sectors=32, layers=13, anatomy=DEFAULT_ANATOMY):
    """Conforming linear tetrahedra from a layered polygonal cylinder, SI units.

    Explicit ring triangulation preserves tissue interfaces. A globally ordered
    prism split ensures adjacent prisms use the same face diagonals.
    """
    if sectors < 8 or layers < 3:
        raise ValueError("At least 8 sectors and 3 axial slices are required")
    b, m = anatomy.bone_radius, anatomy.muscle_radius
    radii = [b, b+(m-b)/3, b+2*(m-b)/3, m, anatomy.radius]
    points = [[0., 0.]]
    for r in radii:
        points.extend([[r * np.cos(a), r * np.sin(a)]
                       for a in np.arange(sectors) * 2 * np.pi / sectors])
    triangles = []
    for j in range(sectors):
        k = (j + 1) % sectors
        triangles.append([0, 1 + j, 1 + k])
        for ring in range(len(radii) - 1):
            a, b = 1 + ring * sectors + j, 1 + ring * sectors + k
            A, B = a + sectors, b + sectors
            triangles.extend([[a, b, B], [a, A, B]])
    points = np.asarray(points)
    n = len(points)
    nodes = np.vstack([np.column_stack([points, np.full(n, z)])
                       for z in np.linspace(-anatomy.length/2, anatomy.length/2, layers)])
    elements = []
    for layer in range(layers - 1):
        for triangle in triangles:
            a, b, c = np.sort(triangle) + layer * n
            A, B, C = a + n, b + n, c + n
            elements.extend([[a, b, c, C], [a, b, B, C], [a, A, B, C]])
    return Mesh(nodes, np.asarray(elements), sectors, layers, n, anatomy)
