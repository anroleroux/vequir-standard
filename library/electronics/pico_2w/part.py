"""Raspberry Pi Pico 2 W.

The Pico 2 W microcontroller board: a 1 mm board with the RP2350, its flash,
the CYW43439 wireless module under a shield can, a micro-USB port, the
BOOTSEL button, 40 edge pins (through-holes and castellations), three SWD
debug pads and four mounting holes.

The parts are keep-out blocks, so a housing knows where to stay clear: the
chips, button and port on their own, the small parts lumped into larger
blocks, and a block over the pins and debug pads for their solder.

Assumptions where the description is silent:
- the layout is read off a photograph of the top of the board, scaled to its
  51 x 21 mm; places are good to about +-0.5 mm, heights are typical;
- the pin through-holes are 1.0 mm and the castellations 1.0 mm half-holes
  centred on the board's long edges, in line with the through-holes; the
  pins along each edge carry a 2.6 mm wide, 1.0 mm high keep-out strip
  (pads and solder), the holes running through it;
- the three SWD debug pads are 1.0 mm through-holes at 2.54 mm pitch across
  the board, 31.7 mm from the USB end and 2.8 mm off the centre line, under
  a 2.0 x 7.1 x 1.0 mm keep-out;
- the micro-USB receptacle is 8.0 mm wide, 6.0 mm deep and 2.6 mm high, its
  mouth 1.3 mm proud of the board's end, centred across the board;
- the RP2350 (QFN-60) is a 7 x 7 x 0.9 mm block 23.4 mm from the USB end, in
  a 0.7 mm high block lumping its decoupling parts;
- the wireless module's shield can is 10.2 x 12 x 1.6 mm, centred 38 mm from
  the USB end; the antenna beyond it is a copper trace, not modelled;
- the flash (2.4 x 3.8 x 0.8 mm), the BOOTSEL button (4 x 4 x 1.5 mm), the
  crystal (2.5 x 2.8 x 0.8 mm) and the LED are blocks of their own; the
  regulator, inductor, diode and capacitors are lumped into a 1.2 mm high
  power block beside the button, and the parts by the port into a 0.6 mm one;
- the copper of the pads and castellations is not modelled;
- x runs along the board with the USB end at -x, y across it, z up; the
  board is centred on x and y and its underside is on z = 0; seen from
  above with the USB end on the right, pin 1 is at the top right.
"""
import cadquery as cq

# the board, in mm
length = 51.0  # along x
width = 21.0  # along y
pcb_t = 1.0  # board thickness

# the pins
pins_per_side = 20
pin_pitch = 2.54  # along x
pin_rows = 17.78  # the two rows, centre to centre along y
pin_hole = 1.0  # through-hole diameter
castellation = 1.0  # half-hole diameter, centred on the edge

# the mounting holes
mount_hole = 2.1  # diameter
mount_x = 47.0  # apart along the board
mount_y = 11.4  # apart across it

# the debug pads
swd_count = 3
swd_x = 31.7  # from the USB end
swd_y = 2.8  # their centre off the centre line
swd_hole = 1.0  # diameter
swd_keepout = (2.0, 7.1, 1.0)  # over the pads: along x, along y, high

# the pins' keep-out strips, along each long edge
pin_strip_w = 2.6  # in from the edge
pin_strip_l = 50.0  # along x, over all twenty pads
pin_strip_h = 1.0  # pads and solder

# the micro-USB receptacle, at -x
usb = (6.0, 8.0, 2.6)  # deep (x), wide (y), high (z)
usb_overhang = 1.3  # its mouth past the board's end

# the other parts: along x, along y, high; centres (x from the USB end, y off the centre line)
rp2350 = (7.0, 7.0, 0.9)
rp2350_at = (23.4, 0.0)
core = (11.7, 12.3, 0.7)  # the RP2350's decoupling parts, lumped
core_at = (23.35, 1.65)
flash = (2.4, 3.8, 0.8)
flash_at = (16.25, -3.5)
bootsel = (4.0, 4.0, 1.5)
bootsel_at = (12.2, -3.4)
power = (11.9, 8.45, 1.2)  # regulator, inductor, diode and capacitors, lumped
power_at = (11.25, 3.5)
usb_parts = (2.6, 3.8, 0.6)  # the small parts by the port, lumped
usb_parts_at = (6.2, -2.6)
led = (1.0, 1.6, 0.5)
led_at = (4.75, -6.5)
crystal = (2.5, 2.8, 0.8)
crystal_at = (29.9, -4.5)
can = (10.2, 12.0, 1.6)  # the wireless module's shield
can_at = (38.0, 0.0)

height = pcb_t + usb[2]  # overall: the USB receptacle is the tallest part
x0 = -length / 2  # the USB end


def block(size, x, y=0.0):
    """A part on top of the board, its centre x from the USB end."""
    return (cq.Workplane("XY", origin=(x0 + x, y, pcb_t))
            .box(*size, centered=(True, True, False)))


usb_x = -usb_overhang + usb[0] / 2  # from the USB end
strip_y = width / 2 - pin_strip_w / 2
parts = [
    block(usb, usb_x),
    block(rp2350, *rp2350_at),
    block(core, *core_at),
    block(flash, *flash_at),
    block(bootsel, *bootsel_at),
    block(power, *power_at),
    block(usb_parts, *usb_parts_at),
    block(led, *led_at),
    block(crystal, *crystal_at),
    block(can, *can_at),
    block(swd_keepout, swd_x, swd_y),
    block((pin_strip_l, pin_strip_w, pin_strip_h), length / 2, strip_y),
    block((pin_strip_l, pin_strip_w, pin_strip_h), length / 2, -strip_y),
]
result = cq.Workplane("XY").box(length, width, pcb_t, centered=(True, True, False))
for p in parts:
    result = result.union(p)

pin_x = [(i - (pins_per_side - 1) / 2) * pin_pitch for i in range(pins_per_side)]
swd_at = [(x0 + swd_x, swd_y + (i - (swd_count - 1) / 2) * pin_pitch) for i in range(swd_count)]
mount_at = [(sx * mount_x / 2, sy * mount_y / 2) for sx in (-1, 1) for sy in (-1, 1)]


def holes(points, d):
    """Cylinders d across at points, through the board and its keep-outs."""
    return (cq.Workplane("XY", origin=(0, 0, -1)).pushPoints(points)
            .circle(d / 2).extrude(height + 2))


result = (result
          .cut(holes([(x, s * pin_rows / 2) for x in pin_x for s in (-1, 1)], pin_hole))
          .cut(holes([(x, s * width / 2) for x in pin_x for s in (-1, 1)], castellation))
          .cut(holes(mount_at, mount_hole))
          .cut(holes(swd_at, swd_hole)))


def tops(z, y_min, y_max):
    """Top faces at height z whose centre lies between y_min and y_max."""
    return result.faces("+Z").filter(
        lambda f: abs(f.Center().z - z) < 1e-6 and y_min < f.Center().y < y_max)


regions = {
    "usb_end": result.faces("<X"),  # the micro-USB receptacle's mouth
    "mounting_holes": result.faces("%CYLINDER").filter(  # the four 2.1 mm holes' walls
        lambda f: abs(f.BoundingBox().xlen - mount_hole) < 1e-3 and abs(f.BoundingBox().ylen - mount_hole) < 1e-3),
    "pin_strips": tops(pcb_t + pin_strip_h, width / 2 - pin_strip_w, width / 2).add(
        tops(pcb_t + pin_strip_h, -width / 2, -width / 2 + pin_strip_w)),  # the two rows of pins
    "debug_pads": result.faces("+Z").filter(  # the SWD keep-out's top
        lambda f: abs(f.Center().z - pcb_t - swd_keepout[2]) < 1e-6
        and abs(f.Center().x - x0 - swd_x) < swd_keepout[0] / 2),
    "bottom": result.faces("<Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
