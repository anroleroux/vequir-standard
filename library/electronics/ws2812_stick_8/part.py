"""RGB WS2812 stick, 8 x 1 (MicroRobotics WS2812-STICK-8x1).

Eight 5050 WS2812 LEDs in a row along a black board, a small decoupling
capacitor beside each, and two mounting holes.

Assumptions where the description is silent:
- the board is 51.1 x 10.2 mm and 1.6 mm thick, the size of the stick this
  one copies (Adafruit's NeoPixel Stick, 3.2 mm thick over the LEDs);
- the LEDs are 5.0 x 5.0 x 1.6 mm, at 6.35 mm (0.25 in) pitch, centred
  along the board, their row 0.7 mm in from its -y edge;
- the capacitors are 0603 (1.6 x 0.8 x 0.5 mm), one beside each LED on the
  +y side, their centres 3.3 mm from the board's centre line;
- the mounting holes are 2.0 mm, on the capacitors' line, between the
  second and third LEDs from each end;
- the pads at the ends (DIN, DOUT, 5V, GND) are not modelled;
- x along the board, y across it, z up with the LEDs on top; centred on x
  and y, underside on z = 0.
"""
import cadquery as cq

# in mm
length = 51.1  # along x
width = 10.2  # along y
pcb_t = 1.6  # board thickness
leds = 8
led = 5.0  # square
led_h = 1.6  # height
pitch = 6.35  # LED to LED, along x
led_margin = 0.7  # from the -y edge to the LEDs' row
cap = (1.6, 0.8, 0.5)  # 0603 capacitor
cap_y = 3.3  # its centre line, from the board's centre line (+y)
hole = 2.0  # mounting hole diameter

led_y = -width / 2 + led_margin + led / 2  # the LEDs' centre line
led_xs = [(i - (leds - 1) / 2) * pitch for i in range(leds)]
hole_xs = [(led_xs[1] + led_xs[2]) / 2, (led_xs[-2] + led_xs[-3]) / 2]
height = pcb_t + led_h  # overall
cap_top = pcb_t + cap[2]  # the tallest part beside the LEDs

board = (
    cq.Workplane("XY").box(length, width, pcb_t, centered=(True, True, False))
    .faces(">Z").workplane()
    .pushPoints([(x, cap_y) for x in hole_xs]).hole(hole)
)
lights = (
    cq.Workplane("XY", origin=(0, 0, pcb_t))
    .pushPoints([(x, led_y) for x in led_xs])
    .rect(led, led).extrude(led_h)
)
caps = (
    cq.Workplane("XY", origin=(0, 0, pcb_t))
    .pushPoints([(x, cap_y) for x in led_xs])
    .rect(cap[0], cap[1]).extrude(cap[2])
)
result = board.union(lights).union(caps)

regions = {
    "led_tops": result.faces("+Z").filter(lambda f: abs(f.Center().z - height) < 1e-6),
    "mounting_holes": result.faces("%CYLINDER"),
    "bottom": result.faces("<Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
