# BioMechDesignTeam_EMG
Code base for EMG Fabric sub-team on UWaterloo BioMechatronics Design Team

## Integrated workstation

From `Software/`, create a Python 3.10+ virtual environment and install the new
PySide6 application independently of the legacy scripts:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m workstation
```

The workstation includes an electrical finite-element forearm phantom, a
MuJoCo-driven CAD hand, contextual tools, and a selectable 2/4/8/16-channel FEA-derived
synthetic EMG monitor. Drag a scene to orbit and scroll to zoom. Open the Phantom
inspector to change the electrode array angle, axial position, and spacing;
electrode markers can also be dragged across the forearm surface. A stepped slider selects 2, 4, 8, or 16 bipolar electrode pairs (one channel
per pair). Pairs move as an equally spaced array, at `360° / pair count`. Source activation controls drive the
signals; field colors show the selected source's unit-current potential, not
instantaneous EMG. The monitor expands without replacing either scene. Scroll the monitor to inspect
all channels at higher counts; changing count clears the previous layout's plot
history. Counts can also change while acquisition is paused.

Synthetic acquisition runs on a separate thread at 2 kSPS per channel, in 20 ms
blocks. The bounded display queue feeds a two-second plot at approximately 30 Hz.
The plot's vertical half-range is 0.025 mV per channel; larger peaks are clipped
for display. Preprocessing, ML, recording, and live hardware are subsequent
milestones.
Hardware diagnostics remain unavailable until measured by a real connection.

### Electrical phantom model

`workstation/phantom/` contains a conforming three-region 3D tetrahedral mesh, conductivity
assignment, sparse P1 FEM assembly/solve, surface interpolation, field geometry,
and asynchronous UI controller. The default cylinder has 2,093 nodes and 10,368
tetrahedra, 37.8 mm radius and a chosen 240 mm segment length. Anatomy cutaway
mode shows a central bone cylinder, muscle annulus, and skin shell; the viewport
button switches to the intact FEA potential surface. Both modes use the same
dimensions as the solver.

Dimensions are derived from human pQCT/ultrasound cohort means reported in
[Iivarinen et al., Table 1](https://doi.org/10.1111/j.1600-0846.2012.00652.x)
(N=11). The reported circular bone radii are 6.8 and 7.1 mm. One equivalent core
preserves their combined area: `sqrt(6.8² + 7.1²) = 9.831 mm`. The muscle outer
radius is 36.2 mm, yielding a derived annulus thickness of 26.369 mm. Skin
thickness is `40.9 − 39.3 = 1.6 mm`. To implement three layers, the reported
3.1 mm subcutaneous fat layer is omitted, reducing the total radius to 37.8 mm.
These are transformed means from a small cohort, not population-wide averages;
the muscle annulus thickness is a model derivation, not a direct local measurement. Muscle conductivity
is anisotropic along the cylinder axis. Conductivities in `materials.py` are
illustrative constants, not calibrated human measurements.

The weak equation is `integral(grad(v) · sigma · grad(phi)) = v.T I`, with an
insulating exterior. Each muscle source is a pair of normalized smooth nodal
loads, +1 and −1 microamp, separated axially by 30 mm. Zero net injected current
makes the insulated problem compatible. One pinned node fixes the arbitrary
constant potential; electrode differences are independent of that reference.
For field colors, the solution is shifted to a zero volume-weighted mean.
See the [FEniCS pure-Neumann formulation](https://olddocs.fenicsproject.org/dolfin/latest/python/demos/neumann-poisson/demo_neumann-poisson.py.html)
for the boundary compatibility and nullspace principles.

Four independent muscle-source solutions form a cached lead field. The chosen
number of electrodes changes the measurement channels, not the number of muscle
sources. Surface triangular
shape functions sample bipolar potentials in mV; moving electrodes updates the
lead field without refactorizing the unchanged tissue system. Independent
synthetic muscle currents are mixed through this field at 2 kSPS. Cross-talk is
the fraction of CH1 power from non-target sources under equal, independent source
power, rather than a measured physiological metric. The inspector reports the
signed CH1 target sensitivity, full N×4 lead field, mesh size, solve duration,
and relative algebraic residual.

This is an electrical volume-conductor approximation, not patient-specific
anatomy or mechanical stress FEA. It omits electrode area/contact impedance,
action-potential propagation, and frequency-dependent tissue properties.
Numerical residuals do not establish anatomical accuracy or mesh convergence.
A full angular, axial, and radial convergence study remains necessary before
quantitative interpretation; the previous four-region refinement result does not
apply to this updated geometry.

`pyproject.toml` defines the workstation dependencies. The existing
`requirements.txt` belongs to the older scripts and is not needed for this app.
`docs/` is intentionally empty.

### Responsiveness

The plot uses an in-place circular buffer and vectorized min/max decimation.
Waveform images are prepared at 30 Hz; the render callback only blits the cached
image. At 960×120, a local benchmark reduced plot-render callback time from about
4.8 ms to 0.05 ms, with image preparation taking about 2 ms on the GUI thread.
This measures plotting cost, not end-to-end FPS. Electrode changes coalesce into
30 Hz analysis updates with separate property notifications, and dragging uses
an analytic cylinder intersection instead of a mesh-wide pick on every move.
Field source switching reuses cached surface topology.

# Brief Introduction
We are currently using ESP-NOW framework for communication. There is a sender and receiver.

Sender:
- Has the MAC address of the receiver.
- Defines the data structure of the message to be sent.

Receiver:
- Must have the same data structure as the sender.

Note:
- When using ESP-NOW, only the following GPIO pins are available to use:
- 32, 33, 34, 35, 36, 37, 38, 39

# ML
There is an colab extension in vscode so we no longer need the web colab

### FEA cross-section

Click **Slice** in the digital forearm viewport to open an integrated transverse
cross-section below the 3D scene. The position slider spans −120 to +120 mm;
a translucent plane in the 3D scene marks the requested position. The source
selector is shared with the main FEA view. Bone, muscle, and skin boundaries
are outlined on the section. The robot and signal monitor remain visible.

Each slice intersects the existing tetrahedra and interpolates their solved P1
potential at intersection vertices. It does not solve a separate 2D model.
Slice generation runs in the background, coalesces rapid requests, and discards
stale results. Surface and slice colors share a fixed, whole-volume symmetric
scale for each selected 1 µA source. The slice reports its own minimum/maximum;
a nearly neutral central plane is expected for the symmetric axial dipole model.

Internal muscle sources are visible by default using an explicitly labeled
X-ray overlay, so opaque tissue does not hide their true internal positions.
Orange/violet markers show the positive/negative centers at z=+15/−15 mm, with
M1–M4 labels and connecting lines. Click a marker to select that source; the
**Internal sources** checkbox hides the overlay. Marker sizes are illustrative:
the solver still uses distributed Gaussian current regions (σ=9 mm), not implanted
metal electrodes. The shared source constants drive both the solver and markers.

The cross-section shows numbered source positions: filled orange/violet within
0.5 mm of the respective center plane, hollow when projected from another axial
position. Clicking a cross-section marker selects the corresponding source.

### MuJoCo hand simulation

The hand viewport now displays the supplied Bionic Hand Delta 1.1 CAD geometry
at actual MuJoCo body poses. Physics runs on a separate fixed-step worker at
500 Hz; the Qt Quick 3D adapter receives pose snapshots at up to 60 Hz and uploads
its full-detail rigid meshes once. It does not embed MuJoCo's default viewer.

Use **CAD rest**, **Flex test**, or **Spread** in the viewport, or open **Joint
controls** / the Robot navigation icon to select and adjust individual targets.
The global Pause button pauses both acquisition and physics. Reset physics
returns the simulation to the supplied CAD pose; CAD rest commands that pose
through the position actuators. Gesture inference remains unconnected.

The articulated model is a prototype: 20 bearing-derived hinge candidates,
19 source controller channels, and provisional rigid-part ownership, travel,
mass/inertia, friction, collision proxies and servo gains. The extra thumb middle
hinge has no `med01` channel and remains available for manual testing. Self-contact
is disabled pending a mechanical ownership review; environment contacts use
simplified proxies. This is not a verified hardware dynamics model.

[Robot model details](workstation/robot/models/bionic_hand_delta_1_1/README.md)
include the original fixed URDF, the articulated URDF, runtime MJCF, conversion
manifest, bearing evidence, ownership map and preserved source license. Re-run
`python -m pip install -e .` from `Software/` to install the added MuJoCo dependency.
