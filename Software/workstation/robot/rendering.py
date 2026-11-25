"""Qt-native rendering adapter: immutable CAD meshes plus MuJoCo body poses.

No OpenGL viewer is embedded in Qt Quick. Physics never touches Qt objects;
meshes load on a worker, and the GUI uploads each rigid mesh once.
"""
from pathlib import Path

import numpy as np
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QVector3D
from PySide6.QtQuick3D import QQuick3DGeometry


def load_render_assets(path):
    with np.load(Path(path)) as data:
        return [(str(name),data[f'vertices_{i}'].copy(),data[f'bounds_{i}'].copy())
                for i,name in enumerate(data['names'])]


def load_mujoco_render_assets(path):
    import mujoco

    model = mujoco.MjModel.from_xml_path(str(Path(path)))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model,data)
    body_triangles = {}
    mesh_type = int(mujoco.mjtGeom.mjGEOM_MESH)

    for geom_id in range(model.ngeom):
        if int(model.geom_type[geom_id]) != mesh_type or int(model.geom_group[geom_id]) == 3:
            continue
        mesh_id = int(model.geom_dataid[geom_id])
        body_id = int(model.geom_bodyid[geom_id])
        vertex_start = int(model.mesh_vertadr[mesh_id])
        vertex_count = int(model.mesh_vertnum[mesh_id])
        face_start = int(model.mesh_faceadr[mesh_id])
        face_count = int(model.mesh_facenum[mesh_id])
        vertices = model.mesh_vert[vertex_start:vertex_start + vertex_count]
        faces = model.mesh_face[face_start:face_start + face_count]
        geom_rotation = data.geom_xmat[geom_id].reshape(3,3)
        body_rotation = data.xmat[body_id].reshape(3,3)
        world_vertices = vertices @ geom_rotation.T + data.geom_xpos[geom_id]
        local_vertices = (world_vertices - data.xpos[body_id]) @ body_rotation
        triangles = local_vertices[faces]
        triangle_normals = np.cross(triangles[:,1] - triangles[:,0],triangles[:,2] - triangles[:,0])
        lengths = np.linalg.norm(triangle_normals,axis=1)
        valid = lengths > 0
        triangle_normals[valid] /= lengths[valid,None]
        triangle_normals[~valid] = 0
        packed = np.column_stack((triangles.reshape(-1,3),np.repeat(triangle_normals,3,axis=0))).astype(np.float32)
        body_triangles.setdefault(body_id,[]).append(packed)

    assets = []
    for body_id, parts in body_triangles.items():
        vertices = np.concatenate(parts)
        vertices[:,:3] *= 1000
        bounds = np.stack((vertices[:,:3].min(axis=0),vertices[:,:3].max(axis=0)))
        name = mujoco.mj_id2name(model,mujoco.mjtObj.mjOBJ_BODY,body_id)
        assets.append((name,vertices,bounds))
    if not assets:
        raise ValueError(f'No visual mesh assets found in MuJoCo model: {path}')
    return assets


class RigidGeometry(QQuick3DGeometry):
    def __init__(self, vertices, bounds, parent=None):
        super().__init__(parent)
        self.setStride(24)
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        attr=QQuick3DGeometry.Attribute
        self.addAttribute(attr.Semantic.PositionSemantic,0,attr.ComponentType.F32Type)
        self.addAttribute(attr.Semantic.NormalSemantic,12,attr.ComponentType.F32Type)
        self.setVertexData(QByteArray(vertices.tobytes()))
        self.setBounds(QVector3D(*map(float,bounds[0])),QVector3D(*map(float,bounds[1])))
