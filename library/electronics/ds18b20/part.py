"""DS18B20 temperature sensor, TO-92.

The bare DS18B20 in its TO-92 package: a body round at the back and flat
at the front, its three leads (GND, DQ, VDD) straight down from the bottom.

Assumptions where the description is silent:
- the TO-92 body is 4.6 mm wide across the flat, 3.6 mm deep from the flat
  to the back and 4.6 mm tall (the package drawing's typical values); the
  back is an arc of a 4.8 mm circle;
- the leads are 0.45 mm square, at 1.27 mm pitch, 14 mm long, in line
  1.0 mm behind the flat;
- modelled standing up: the leads' tips on z = 0, the flat facing -y,
  x across the leads (GND at -x).
"""
import cadquery as cq

# in mm
width = 4.6  # across the flat, along x
depth = 3.6  # flat to back, along y
body_h = 4.6  # body height
back_d = 4.8  # the round back's diameter
lead = 0.45  # square
lead_pitch = 1.27
lead_length = 14.0
lead_y = 1.0  # behind the flat

body_bottom = lead_length
height = body_bottom + body_h
flat_y = -depth / 2  # the flat face's plane
back_centre = flat_y + depth - back_d / 2  # the round back's centre, along y

body = (
    cq.Workplane("XY", origin=(0, back_centre, body_bottom)).circle(back_d / 2).extrude(body_h)
    .intersect(cq.Workplane("XY", origin=(0, 0, body_bottom))
               .center(0, flat_y + depth / 2).rect(width, depth).extrude(body_h))
)
leads = (
    cq.Workplane("XY")
    .pushPoints([(i * lead_pitch, flat_y + lead_y) for i in (-1, 0, 1)])
    .rect(lead, lead).extrude(lead_length)
)
result = body.union(leads)

regions = {
    "flat": result.faces("<Y").filter(lambda f: f.Center().z > body_bottom),
    "leads": result.faces("<Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
