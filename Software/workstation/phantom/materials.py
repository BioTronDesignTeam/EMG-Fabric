import numpy as np


# Illustrative configurable model constants in S/m, not calibrated human data.
DEFAULTS = dict(bone=.02, muscle_transverse=.12, muscle_axial=.4,
                skin=.2)


def conductivity(mesh, values=None):
    values = DEFAULTS if values is None else values
    # Ring mean radius identifies each conforming material region. Centroid
    # radii would incorrectly classify thin polygonal outer layers.
    radius = np.linalg.norm(mesh.nodes[mesh.elements, :2], axis=2).mean(axis=1)
    tissue = np.select([radius <= mesh.anatomy.bone_radius + 1e-12, radius <= mesh.anatomy.muscle_radius + 1e-12],
                       [0, 1], default=2)
    transverse = np.choose(tissue, [values['bone'], values['muscle_transverse'],
                                   values['skin']])
    axial = np.where(tissue == 1, values['muscle_axial'], transverse)
    return np.column_stack([transverse, transverse, axial]), tissue
