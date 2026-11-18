"""1N5822 Schottky diode, DO-201AD, formed for a board.

A 3 A, 40 V Schottky rectifier in the axial DO-201AD package, mounted
lying flat on a board: the body resting on the board, its leads bent down
through two holes 0.6 in (15.24 mm) apart.

Assumptions where the description is silent:
- the body is 9.5 mm long and 5.3 mm across, the leads 1.3 mm round (the
  package's maximum sizes); the 1.3 mm leads need the board's holes drilled
  out to 1.5 mm;
- the leads are bent square (bend radius not modelled) and cut 3.0 mm
  below the board's top: through a 1.6 mm board and 1.4 mm out;
- the cathode band is a 0.15 mm deep, 1.5 mm wide groove, 0.5 mm in from
  the cathode end, standing in for the printed band;
- modelled with the board's top on z = 0: the body along x, cathode at +x,
  resting on z = 0, the leads at x = +-7.62.
"""
import cadquery as cq

# in mm
body_length = 9.5
body_d = 5.3
lead_d = 1.3
pitch = 15.24  # 0.6 in, between the holes
below = 3.0  # the leads' cut ends, under the board's top
band_w = 1.5
band_depth = 0.15
band_inset = 0.5  # from the cathode end
hole = 1.5  # the board's holes, drilled out for the leads

axis_z = body_d / 2  # the body rests on the board
lead_xs = [-pitch / 2, pitch / 2]  # anode, cathode
height = body_d

body = cq.Workplane("YZ", origin=(-body_length / 2, 0, axis_z)).circle(body_d / 2).extrude(body_length)
band = (cq.Workplane("YZ", origin=(body_length / 2 - band_inset - band_w, 0, axis_z))
        .circle(body_d / 2).circle(body_d / 2 - band_depth).extrude(band_w))
across = cq.Workplane("YZ", origin=(-pitch / 2, 0, axis_z)).circle(lead_d / 2).extrude(pitch)
down = (cq.Workplane("XY", origin=(0, 0, -below))
        .pushPoints([(x, 0) for x in lead_xs]).circle(lead_d / 2).extrude(below + axis_z))
corners = [cq.Workplane("XY").sphere(lead_d / 2).translate((x, 0, axis_z)) for x in lead_xs]
result = body.cut(band).union(across).union(down)
for c in corners:
    result = result.union(c)

regions = {
    "anode_lead": result.faces("<Z").filter(lambda f: f.Center().x < 0),
    "cathode_lead": result.faces("<Z").filter(lambda f: f.Center().x > 0),
    "body": result.faces("%CYLINDER").filter(
        lambda f: abs(f.BoundingBox().ylen - body_d) < 1e-3 and abs(f.BoundingBox().xlen) > 1),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
