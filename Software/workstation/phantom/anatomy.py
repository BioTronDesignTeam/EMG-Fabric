"""Three-region, cohort-derived circular forearm approximation (SI units).

Iivarinen (2014), Diagnostics of human forearm soft tissues using indentation
and suction measurements, chapter 6, pp.31–33. Eleven volunteers (9 men,
2 women; age 31 ± 7 years). Circular mean radii: skin 40.9, fat 39.3,
muscle 36.2, radius 6.8, ulna 7.1 mm. Primary source:
https://doi.org/10.1111/j.1600-0846.2012.00652.x (Table 1)

We preserve combined bone area in one equivalent circular core. Skin thickness
is 40.9−39.3 = 1.6 mm. The requested three-layer reduction omits 3.1 mm of
subcutaneous fat instead of calling it muscle; muscle outer radius stays 36.2 mm.
This is a small cohort mean transformed into a simplified geometry, not a
population-wide average. The 240 mm modeled segment length is a design choice.
"""
from dataclasses import dataclass
from math import hypot


@dataclass(frozen=True)
class Anatomy:
    bone_radius: float = hypot(.0068, .0071)
    muscle_radius: float = .0362
    skin_thickness: float = .0016
    length: float = .24

    @property
    def radius(self):
        return self.muscle_radius + self.skin_thickness

    @property
    def muscle_thickness(self):
        return self.muscle_radius - self.bone_radius

    @property
    def source_radius(self):
        return (self.bone_radius + self.muscle_radius) / 2


DEFAULT_ANATOMY = Anatomy()
