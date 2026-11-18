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
