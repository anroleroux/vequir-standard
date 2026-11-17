"""MT3608 boost regulator board (MicroRobotics MT3608-2A).

A step-up module: a board with the MT3608 chip, its 22 uH inductor, a
Schottky diode and a blue multi-turn trimmer, and a through-hole pad at
each corner: VIN+ and VIN- at +x, VOUT+ and VOUT- at -x.

Assumptions where the description is silent:
- the board is 36 x 17 mm and 1.6 mm thick, the size sellers list for the
  common MT3608 module; parts' sizes and places are typical, not measured;
- the trimmer is a 3296-style multi-turn pot lying on the board, 9.5 x 10 mm
  and 4.8 mm tall, the tallest part, so the module is 6.4 mm high overall;
- the inductor is a CD54, 5.8 x 5.2 mm and 4.5 mm tall; the MT3608 a SOT-23-6
  body (2.9 x 1.6 x 1.1 mm); the diode an SMA body (4.3 x 2.6 x 2.1 mm);
  the capacitors and resistors are not modelled;
- the four corner holes are 1.2 mm, 2.2 mm in from the board's end and
  2.5 mm in from its side; the pads round them are not modelled;
- x along the board (VIN at +x), y across it, z up; centred on x and y,
  underside on z = 0.
"""
import cadquery as cq

# the board, in mm
length = 36.0  # along x
width = 17.0  # along y
pcb_t = 1.6  # board thickness

# the corner holes
hole = 1.2  # diameter
hole_end = 2.2  # centre, in from the board's end
hole_side = 2.5  # centre, in from the board's side

# the parts: (along x, across, height), and where
pot = (9.5, 10.0, 4.8)  # the trimmer
pot_at = (-7.0, 0.0)
coil = (5.8, 5.2, 4.5)  # the inductor
coil_at = (6.0, 0.0)
chip = (2.9, 1.6, 1.1)  # the MT3608
chip_at = (11.0, -4.0)
diode = (4.3, 2.6, 2.1)  # the Schottky diode
diode_at = (11.3, 4.0)

height = pcb_t + pot[2]  # overall
hole_x = length / 2 - hole_end
hole_y = width / 2 - hole_side
vin_holes = [(hole_x, hole_y), (hole_x, -hole_y)]  # VIN+, VIN-
vout_holes = [(-hole_x, hole_y), (-hole_x, -hole_y)]  # VOUT+, VOUT-

board = (
    cq.Workplane("XY").box(length, width, pcb_t, centered=(True, True, False))
    .faces(">Z").workplane()
    .pushPoints(vin_holes + vout_holes)
    .hole(hole)
)
result = board
for size, (x, y) in ((pot, pot_at), (coil, coil_at), (chip, chip_at), (diode, diode_at)):
    result = result.union(
        cq.Workplane("XY", origin=(x, y, pcb_t)).box(*size, centered=(True, True, False)))

regions = {
    "vin_holes": result.faces("%CYLINDER").filter(lambda f: f.Center().x > 0),
    "vout_holes": result.faces("%CYLINDER").filter(lambda f: f.Center().x < 0),
    "trimmer_top": result.faces("+Z").filter(lambda f: abs(f.Center().z - height) < 1e-6),
    "bottom": result.faces("<Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
