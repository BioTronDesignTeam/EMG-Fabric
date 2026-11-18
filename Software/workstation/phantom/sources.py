"""Shared positions for the distributed muscle-current sources and UI markers."""
from math import cos, sin, pi

from .anatomy import DEFAULT_ANATOMY

AXIAL_OFFSET = .015
SOURCE_SPREAD = .009


def source_markers(anatomy=DEFAULT_ANATOMY):
    return [dict(index=i, label=f'M{i+1}',
                 xMm=anatomy.source_radius*cos(i*pi/2)*1000,
                 yMm=anatomy.source_radius*sin(i*pi/2)*1000,
                 positiveZMm=AXIAL_OFFSET*1000,
                 negativeZMm=-AXIAL_OFFSET*1000,
                 sigmaMm=SOURCE_SPREAD*1000)
            for i in range(4)]
