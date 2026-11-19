"""1/4 W axial resistor, inline.

A through-hole carbon-film resistor with straight leads cut short, for
soldering inline in a wire (under heat-shrink).

Assumptions where the description is silent:
- the body is 6.3 mm long and 2.4 mm across, the leads 0.6 mm round
  (typical 1/4 W sizes, as the board-mounted resistor_025w);
- each lead is cut to 3.0 mm, straight out of the body's end;
- the heat-shrink and the wires' joints are not modelled;
- modelled along x, centred, its axis on the x axis.
"""
import cadquery as cq

# in mm
body_length = 6.3
body_d = 2.4
lead_d = 0.6
lead_length = 3.0  # each, after cutting

length = body_length + 2 * lead_length  # overall

body = cq.Workplane("YZ", origin=(-body_length / 2, 0, 0)).circle(body_d / 2).extrude(body_length)
leads = cq.Workplane("YZ", origin=(-length / 2, 0, 0)).circle(lead_d / 2).extrude(length)
result = body.union(leads)

regions = {
    "lead_ends": result.faces("<X or >X"),
    "body": result.faces("%CYLINDER").filter(lambda f: abs(f.BoundingBox().ylen - body_d) < 1e-3),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
