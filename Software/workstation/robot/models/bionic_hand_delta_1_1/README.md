# Bionic Hand Delta 1.1 — CAD articulation prototype

Source: **Bionic Hand Delta 1.1 excl. PCBs.step**, supplied Nilheim Mechatronics /
Will Cogley Bionic Hand Delta 1.1 distribution. Attribution: Nilheim Mechatronics /
Will Cogley. The supplied CC BY-NC-SA 4.0 license is preserved in
`SOURCE_LICENSE.html` and applies to the derived CAD assets.

## Deliverables

- `bionic_hand_delta_1_1.urdf`: original fixed visual assembly, 1,116 CAD instances.
- `hand_articulated.urdf`: 21 rigid links, 20 revolute joint candidates and
  provisional inertias/collision boxes. All original visual meshes are retained.
- `hand_simulation.xml`: runtime MuJoCo model, 20 position actuators, 2 ms physics
  step, gravity and environment collision proxies. Self-contact is masked out.
- `render_meshes.npz`: welded full-detail rigid meshes for native Qt Quick 3D
  rendering; this cache does not change physics geometry or the full-detail URDF.
- `cad_hinge_evidence.json`: cylinder-face geometry extracted from named CAD parts.
- `articulation.json`: joint origins/axes, source control channel mapping,
  per-part rigid ownership with inference method, and explicit assumptions.
- `manifest.json`: original source hash, STEP names/assembly paths, mesh metadata.
- `joint_requirements.json`: checklist for physical verification of 19 channels.

Coordinates are metres in URDF/MJCF and millimetres in the Qt render cache. All
joint frames are aligned with the original CAD axes at zero. Zero joint values
preserve the supplied, partly bent CAD pose; this is not a calibrated open hand.

## Inference and limits

Five repeated finger mechanisms were identified. Cylinders of radius 6 mm in
lateral MCP links, 2 mm in proximal MCP links and 2.1 mm in middle/distal shells
supply hinge lines. Matching halves share a hinge axis. Remaining small parts
are initially assigned by nearest skeletal segment; repeated-component rigid
fits transfer reference-finger ownership when alignment error is below 2 mm.
This is an inspectable inference, not an imported CAD mate/constraint tree.

The supplied Arduino interface has 19 channels, while the CAD reveals 20 hinge
candidates. The thumb middle joint is exposed for manual testing without inventing
a `med01` channel or an unverified coupling. Travel is limited to ±0.6 rad for
flexion and ±0.25 rad laterally about the CAD pose. These are prototype test
bounds, not measured hard stops. Masses (18–32 g/link), bounding-box inertias,
friction, damping, motor armature, torque limits and PD gains are provisional.
Belt/pulley mechanisms are represented by rigid ownership, not closed-loop belt
or tendon dynamics. Self-collisions must be reviewed after ownership calibration.

The runtime is `hand_simulation.xml`; generic URDF importers may apply different
collision/contact defaults. Manual physics tests are available in the main GUI.
No hardware commands or gesture inference are attached.

## Reproduce

The application only needs its `pyproject.toml` runtime dependencies. Regenerating
CAD assets requires a separate environment:

```sh
python -m pip install cadquery-ocp trimesh scipy mujoco
python Software/tools/step_to_urdf.py \
  "$HOME/Downloads/Bionic Hand Delta 1.1/CAD/Bionic Hand Delta 1.1 excl. PCBs.step" \
  Software/workstation/robot/models/bionic_hand_delta_1_1
python Software/tools/extract_hand_hinges.py \
  "$HOME/Downloads/Bionic Hand Delta 1.1/CAD/Bionic Hand Delta 1.1 excl. PCBs.step" \
  Software/workstation/robot/models/bionic_hand_delta_1_1/cad_hinge_evidence.json
python Software/tools/build_articulated_hand.py
```

The articulation builder uses the preserved cylinder evidence. Replacing the
source CAD also requires re-extracting/reviewing that evidence and ownership.
Keep the entire asset directory together: URDF/MJCF use relative mesh paths.

## Verification

The original fixed conversion exported 1,116 instances without skips, with CAD
mesh bounds within 0.3 mm. At zero, every articulated visual geometry matches the
original fixed URDF's world pose (maximum translation difference below 1e-9 m).
MuJoCo imports both descriptions. Position-actuator and GUI tests verify finite
motion, target tracking, pause/resume and worker shutdown. These checks establish
software integration, not physical calibration or mechanical validation.
