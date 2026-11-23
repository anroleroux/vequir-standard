"""5 V active buzzer, 12 x 9 mm (MicroRobotics, low profile PCB).

A round body 12 mm across and 9 mm tall, as the seller's drawing gives:
a cap on a slightly narrower base, a 2.5 mm sound hole in the middle of
the top, and two pins 7 mm apart underneath.

Assumptions where the description is silent:
- the base is the bottom 2.5 mm of the body, 0.3 mm smaller in radius than
  the cap above it, as the drawing shows a step;
- the sound hole is 1.0 mm deep;
- the pins are 0.6 mm round and 5.5 mm long below the body, as the drawing
  scales; the + pin is at +x;
- modelled standing up: axis along z, the pins' tips on z = 0.
"""
import cadquery as cq

# in mm
diameter = 12.0  # the cap
body_h = 9.0  # body height, base to top
base_h = 2.5  # the narrower base, at the bottom
base_step = 0.3  # on the radius
sound_hole = 2.5  # diameter
sound_depth = 1.0
pin_d = 0.6
pin_length = 5.5  # below the body
pin_pitch = 7.0

body_bottom = pin_length
height = body_bottom + body_h  # overall

pins = (
    cq.Workplane("XY")
    .pushPoints([(pin_pitch / 2, 0), (-pin_pitch / 2, 0)])
    .circle(pin_d / 2).extrude(pin_length)
)
base = cq.Workplane("XY", origin=(0, 0, body_bottom)).circle(diameter / 2 - base_step).extrude(base_h)
cap = (
    cq.Workplane("XY", origin=(0, 0, body_bottom + base_h))
    .circle(diameter / 2).extrude(body_h - base_h)
)
hole = cq.Workplane("XY", origin=(0, 0, height - sound_depth)).circle(sound_hole / 2).extrude(sound_depth)
result = pins.union(base).union(cap).cut(hole)

regions = {
    "top": result.faces("+Z").filter(lambda f: abs(f.Center().z - height) < 1e-6),
    "sound_hole": result.faces("%CYLINDER").filter(
        lambda f: abs(f.BoundingBox().xlen - sound_hole) < 1e-3),
    "pins": result.faces("<Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
