"""TSD-1166 LED tactile switch, circle pattern (MicroRobotics TSD-1166-CIR).

A momentary push button with a white LED: a square black body, a 10 mm
round button on top with a white ring, and its legs underneath.

Assumptions where the description is silent (only the 10 mm button is
listed; the drawing was not to hand, so these are guesses from the photos):
- the body is 12 x 12 mm and 7 mm tall;
- the button is 10 mm across and stands 5 mm above the body, its ring a
  0.5 mm wide, 0.2 mm deep groove 3.5 mm in radius on its top face;
- six legs, 0.7 x 0.5 mm, 3.5 mm long, in two rows of three at 5 mm pitch,
  10 mm apart: the four corner legs the switch, the middle two the LED;
- modelled standing up: the button's axis along z, the leg tips on z = 0.
"""
import cadquery as cq

# in mm
body = 12.0  # square, along x and y
body_h = 7.0  # height
cap_d = 10.0  # the button's diameter
cap_h = 5.0  # how far it stands above the body
ring_r = 3.5  # the white ring's mean radius
ring_w = 0.5  # its width
ring_depth = 0.2
leg = (0.7, 0.5)  # leg section, along x and y
leg_length = 3.5  # below the body
leg_pitch = 5.0  # along x
leg_rows = 10.0  # apart, along y

body_bottom = leg_length
body_top = body_bottom + body_h
height = body_top + cap_h  # overall, leg tips to the button's top

legs = (
    cq.Workplane("XY")
    .pushPoints([(x * leg_pitch, s * leg_rows / 2) for x in (-1, 0, 1) for s in (-1, 1)])
    .rect(*leg).extrude(leg_length)
)
case = cq.Workplane("XY", origin=(0, 0, body_bottom)).rect(body, body).extrude(body_h)
cap = cq.Workplane("XY", origin=(0, 0, body_top)).circle(cap_d / 2).extrude(cap_h)
ring = (
    cq.Workplane("XY", origin=(0, 0, height - ring_depth))
    .circle(ring_r + ring_w / 2).circle(ring_r - ring_w / 2).extrude(ring_depth)
)
result = legs.union(case).union(cap).cut(ring)

regions = {
    "button": result.faces("%CYLINDER").filter(  # the button's round side
        lambda f: abs(f.BoundingBox().xlen - cap_d) < 1e-3),
    "body_top": result.faces("+Z").filter(  # round the button, against a panel
        lambda f: abs(f.Center().z - body_top) < 1e-6),
    "legs": result.faces("<Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
