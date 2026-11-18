import numpy as np
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry


class FieldGeometry(QQuick3DGeometry):
    """Actual exterior FEM faces, colored by signed source potential."""

    def update_field(self, solver, source):
        mesh = solver.mesh
        if getattr(self, "_mesh", None) is not mesh:
            self._prepare_mesh(mesh)
        faces, xyz, normals = self._faces, self._xyz, self._normals
        value = solver.basis[faces, source]
        scale = max(float(np.max(np.abs(solver.basis[:, source]))), 1e-15)
        signed = value / scale
        neutral = np.array([.84, .87, .9])
        red, blue = np.array([.95, .24, .18]), np.array([.12, .4, .95])
        target = np.where(signed[..., None] >= 0, red, blue)
        colors = neutral + np.abs(signed[..., None]) * (target-neutral)
        vertices = np.concatenate([xyz, np.repeat(normals[:, None], 3, axis=1), colors,
                                   np.ones((*colors.shape[:2], 1))], axis=2).astype(np.float32)
        self.setVertexData(QByteArray(vertices.tobytes()))
        self.update()
        return scale * 1000

    def _prepare_mesh(self, mesh):
        faces = mesh.elements[:, [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]]].reshape(-1, 3)
        unique, counts = np.unique(np.sort(faces, axis=1), axis=0, return_counts=True)
        faces = unique[counts == 1]
        xyz = mesh.nodes[faces][:, :, [0, 2, 1]] * 1000
        normals = np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0])
        backwards = (normals * xyz.mean(axis=1)).sum(axis=1) < 0
        faces[backwards] = faces[backwards][:, [0, 2, 1]]
        xyz = mesh.nodes[faces][:, :, [0, 2, 1]] * 1000
        normals = np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0])
        normals /= np.linalg.norm(normals, axis=1)[:, None]
        self._mesh, self._faces, self._xyz, self._normals = mesh, faces, xyz, normals
        self.clear()
        self.setStride(40)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        attr = QQuick3DGeometry.Attribute
        self.addAttribute(attr.Semantic.PositionSemantic, 0, attr.ComponentType.F32Type)
        self.addAttribute(attr.Semantic.NormalSemantic, 12, attr.ComponentType.F32Type)
        self.addAttribute(attr.Semantic.ColorSemantic, 24, attr.ComponentType.F32Type)
        r, h = mesh.radius*1000, mesh.length*500
        self.setBounds(QVector3D(-r, -h, -r), QVector3D(r, h, r))


class LayerGeometry(QQuick3DGeometry):
    """Opaque cylindrical region with a front quarter removed to expose layers."""

    def __init__(self, inner, outer, length, cutaway):
        super().__init__()
        triangles = []
        half = length*500
        def point(radius, angle, y):
            return np.array([radius*1000*np.cos(angle), y, radius*1000*np.sin(angle)])
        def quad(a, b, c, d):
            triangles.extend([[a,b,c], [a,c,d]])
        for i in range(32):
            if cutaway and 4 <= i < 12:
                continue
            a, b = i*np.pi/16, (i+1)*np.pi/16
            lo, hi = point(outer,a,-half), point(outer,b,-half)
            Lo, Hi = point(outer,a,half), point(outer,b,half)
            quad(lo,Lo,Hi,hi)
            if inner:
                li, ri = point(inner,a,-half), point(inner,b,-half)
                Li, Ri = point(inner,a,half), point(inner,b,half)
                quad(li,ri,Ri,Li)
            else:
                li = ri = np.array([0.,-half,0.])
                Li = Ri = np.array([0.,half,0.])
            if inner:
                quad(Lo,Li,Ri,Hi)
                quad(lo,hi,ri,li)
            else:
                triangles.extend([[Lo,Li,Hi], [lo,hi,li]])
        if cutaway:
            for angle in [np.pi/4, 3*np.pi/4]:
                corners = [point(inner,angle,-half), point(outer,angle,-half),
                           point(outer,angle,half), point(inner,angle,half)]
                quad(*(corners if angle < np.pi/2 else corners[::-1]))
        xyz = np.asarray(triangles)
        normals = np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0])
        normals /= np.linalg.norm(normals,axis=1)[:,None]
        vertices = np.concatenate([xyz,np.repeat(normals[:,None],3,axis=1)],axis=2).astype(np.float32)
        self.setStride(24)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        attr = QQuick3DGeometry.Attribute
        self.addAttribute(attr.Semantic.PositionSemantic,0,attr.ComponentType.F32Type)
        self.addAttribute(attr.Semantic.NormalSemantic,12,attr.ComponentType.F32Type)
        self.setVertexData(QByteArray(vertices.tobytes()))
        self.setBounds(QVector3D(-outer*1000,-half,-outer*1000),QVector3D(outer*1000,half,outer*1000))
