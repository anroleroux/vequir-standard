"""1/4 W axial resistor, formed for a board.

A through-hole carbon-film resistor lying flat on a board, its leads bent
down through two holes 0.4 in (10.16 mm) apart.

Assumptions where the description is silent:
- the body is 6.3 mm long and 2.4 mm across, the leads 0.6 mm round
  (typical 1/4 W sizes); the colour bands are not modelled;
- the leads are bent square and cut 3.0 mm below the board's top;
- modelled with the board's top on z = 0: the body along x, resting on
  z = 0, the leads at x = +-5.08.
"""
import cadquery as cq

# in mm
body_length = 6.3
body_d = 2.4
lead_d = 0.6
pitch = 10.16  # 0.4 in
below = 3.0
hole = 1.0  # a plain perfboard hole takes the leads

axis_z = body_d / 2
lead_xs = [-pitch / 2, pitch / 2]
height = body_d

body = cq.Workplane("YZ", origin=(-body_length / 2, 0, axis_z)).circle(body_d / 2).extrude(body_length)
across = cq.Workplane("YZ", origin=(-pitch / 2, 0, axis_z)).circle(lead_d / 2).extrude(pitch)
down = (cq.Workplane("XY", origin=(0, 0, -below))
        .pushPoints([(x, 0) for x in lead_xs]).circle(lead_d / 2).extrude(below + axis_z))
result = body.union(across).union(down)
for x in lead_xs:
    result = result.union(cq.Workplane("XY").sphere(lead_d / 2).translate((x, 0, axis_z)))

regions = {
    "leads": result.faces("<Z"),
    "body": result.faces("%CYLINDER").filter(lambda f: abs(f.BoundingBox().ylen - body_d) < 1e-3),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
