"""Exact transverse intersections of the solved linear tetrahedral field."""
import numpy as np
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry


def intersect_section(solver, axial_mm, source):
    mesh = solver.mesh
    z = float(np.clip(axial_mm / 1000, -mesh.length/2, mesh.length/2))
    xyz = mesh.nodes[mesh.elements]
    lower, upper = xyz[:, :, 2].min(axis=1), xyz[:, :, 2].max(axis=1)
    # Use one side at mesh-aligned planes to avoid duplicate coplanar faces.
    if np.isclose(z, -mesh.length/2, atol=1e-12, rtol=0):
        selected = (lower <= z) & (upper > z)
    else:
        selected = (lower < z) & (upper >= z)
    triangles, potentials = [], []
    for tet in mesh.elements[selected]:
        points = mesh.nodes[tet]
        values = solver.basis[tet, source]
        distance = points[:, 2]-z
        vertices = [(points[i, :2], values[i]) for i in range(4) if abs(distance[i]) < 1e-12]
        for a, b in [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]:
            if distance[a]*distance[b] < 0:
                t = distance[a]/(distance[a]-distance[b])
                vertices.append((points[a,:2]+t*(points[b,:2]-points[a,:2]),
                                 values[a]+t*(values[b]-values[a])))
        if len(vertices) < 3:
            continue
        xy = np.array([v[0] for v in vertices])
        value = np.array([v[1] for v in vertices])
        _, unique = np.unique(np.round(xy, 12), axis=0, return_index=True)
        xy, value = xy[unique], value[unique]
        if len(xy) < 3:
            continue
        center = xy.mean(axis=0)
        order = np.argsort(np.arctan2(xy[:,1]-center[1],xy[:,0]-center[0]))
        xy, value = xy[order], value[order]
        for j in range(1,len(xy)-1):
            triangle = xy[[0,j,j+1]]
            if abs(np.linalg.det(triangle[1:]-triangle[:1])) > 1e-18:
                triangles.append(triangle)
                potentials.append(value[[0,j,j+1]])
    return np.asarray(triangles), np.asarray(potentials)


class SectionGeometry(QQuick3DGeometry):
    def __init__(self):
        super().__init__()
        self.setStride(40)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        attr = QQuick3DGeometry.Attribute
        self.addAttribute(attr.Semantic.PositionSemantic,0,attr.ComponentType.F32Type)
        self.addAttribute(attr.Semantic.NormalSemantic,12,attr.ComponentType.F32Type)
        self.addAttribute(attr.Semantic.ColorSemantic,24,attr.ComponentType.F32Type)

    def apply_section(self, result):
        vertices, stats, r = result
        self.setVertexData(QByteArray(vertices))
        self.setBounds(QVector3D(-r,-.1,-r),QVector3D(r,.1,r))
        self.update()
        return stats


def prepare_section(solver, axial_mm, source):
    xy, values = intersect_section(solver, axial_mm, source)
    # One scale across every slice and the outer surface. Moving the slice
    # must not auto-normalize a nearly zero plane into a saturated field.
    scale = max(float(np.max(abs(solver.basis[:,source]))),1e-15)
    signed = values/scale
    target = np.where(signed[...,None] >= 0, [.95,.24,.18], [.12,.4,.95])
    colors = np.array([.84,.87,.9])+abs(signed[...,None])*(target-[.84,.87,.9])
    positions = np.stack((xy[:,:,0]*1000,np.zeros_like(values),-xy[:,:,1]*1000),axis=2)
    normals = np.broadcast_to([0.,1.,0.], positions.shape)
    vertices = np.concatenate((positions,normals,colors,np.ones((*values.shape,1))),axis=2).astype(np.float32)
    stats = dict(min=f'{values.min()*1000:.5f}',max=f'{values.max()*1000:.5f}',
                 scale=f'{scale*1000:.5f}',triangles=len(xy))
    return vertices.tobytes(), stats, solver.mesh.radius*1000


class SectionOutlines(QQuick3DGeometry):
    def __init__(self, anatomy, sectors=32):
        super().__init__()
        lines=[]
        for radius in [anatomy.bone_radius,anatomy.muscle_radius,anatomy.radius]:
            for i in range(sectors):
                for angle in [i*2*np.pi/sectors,(i+1)*2*np.pi/sectors]:
                    lines.append([radius*1000*np.cos(angle),.05,radius*1000*np.sin(angle)])
        self.setStride(12)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Lines)
        attr=QQuick3DGeometry.Attribute
        self.addAttribute(attr.Semantic.PositionSemantic,0,attr.ComponentType.F32Type)
        self.setVertexData(QByteArray(np.asarray(lines,dtype=np.float32).tobytes()))
        r=anatomy.radius*1000
        self.setBounds(QVector3D(-r,0,-r),QVector3D(r,.1,r))
