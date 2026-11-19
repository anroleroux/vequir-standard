"""USB-C breakout board, horizontal (MicroRobotics USBC-HOR).

A 20.2 x 14 mm board with a top-mounted USB-C receptacle at one long edge,
its mouth flush with that edge, a row of eight 2.54 mm pin holes along the
other (CC2, SBU1, D+, D-, CC1, SBU2, VBUS, GND) and a mounting hole in each
corner beside the receptacle.

Assumptions where the description is silent:
- 20.2 mm runs along the pin row (y) and 14 mm from the pin row to the
  receptacle's edge (x); the 4.8 mm height is a 1.6 mm board plus the
  receptacle, 3.2 mm tall;
- the receptacle is a top-mount one: an 8.94 mm wide shell with rounded
  ends, 7.35 mm deep, its 8.34 x 2.66 mm mouth flush with the +x edge,
  centred across the board, a 6.7 x 0.7 mm tongue inside (as on the CN3302);
- the pin holes are 1.0 mm, their row centred, 1.6 mm in from the -x edge;
- the mounting holes are 3.2 mm (M3), their centres 3.0 mm in from the
  board's +x edge and from its sides, as the photo reads;
- the two 5.1 k CC resistors and the pads are not modelled;
- x across the board with the mouth at +x, y along the pin row, z up;
  centred on x and y, underside on z = 0.
"""
import cadquery as cq

# the board, in mm
length = 14.0  # along x: pin row to receptacle edge
width = 20.2  # along y: along the pin row
pcb_t = 1.6  # board thickness

# the USB-C receptacle, at +x
usb_w = 8.94  # shell width, along y
usb_h = 3.2  # shell height, along z
usb_d = 7.35  # shell depth, along x
mouth_w = 8.34
mouth_h = 2.66
mouth_d = 6.5  # opening depth into the shell
tongue_w = 6.7
tongue_t = 0.7
tongue_d = 5.0

# the holes
pins = 8
pin_pitch = 2.54
pin_hole = 1.0
pin_inset = 1.6  # the row's centre line, in from the -x edge
mount_hole = 3.2
mount_inset = 3.0  # each centre, in from the +x edge and from its side

height = pcb_t + usb_h  # overall
usb_x1 = length / 2  # the mouth, flush with the +x edge
usb_axis_z = pcb_t + usb_h / 2  # the mouth's centre height above the underside
pin_x = -length / 2 + pin_inset
pin_ys = [(i - (pins - 1) / 2) * pin_pitch for i in range(pins)]  # CC2 at -y ... GND at +y
mount_holes = [(length / 2 - mount_inset, s * (width / 2 - mount_inset)) for s in (1, -1)]

board = (
    cq.Workplane("XY").box(length, width, pcb_t, centered=(True, True, False))
    .faces(">Z").workplane()
    .pushPoints([(pin_x, y) for y in pin_ys]).hole(pin_hole)
    .faces(">Z").workplane()
    .pushPoints(mount_holes).hole(mount_hole)
)
shell = (
    cq.Workplane("YZ", origin=(usb_x1 - usb_d, 0, usb_axis_z))
    .slot2D(usb_w, usb_h).extrude(usb_d)
)
mouth = cq.Workplane("YZ", origin=(usb_x1, 0, usb_axis_z)).slot2D(mouth_w, mouth_h).extrude(-mouth_d)
tongue = (
    cq.Workplane("YZ", origin=(usb_x1 - mouth_d, 0, usb_axis_z))
    .rect(tongue_w, tongue_t).extrude(tongue_d)
)
result = board.union(shell.cut(mouth).union(tongue))

regions = {
    "usb_end": result.faces("+X").filter(lambda f: abs(f.Center().x - usb_x1) < 1e-6),
    "pin_holes": result.faces("%CYLINDER").filter(lambda f: abs(f.Center().x - pin_x) < 1e-6),
    "mounting_holes": result.faces("%CYLINDER").filter(
        lambda f: abs(f.Center().x - mount_holes[0][0]) < 1e-6),
    "bottom": result.faces("<Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
