"""1N5822 Schottky diode, DO-201AD.

A 3 A, 40 V Schottky rectifier in the axial DO-201AD package: a cylinder
with a lead out of each end and a cathode band.

Assumptions where the description is silent:
- the body is 9.5 mm long and 5.3 mm across, the leads 1.3 mm round and
  25.4 mm long each, straight, as bought (the package's maximum body and
  minimum lead length);
- the cathode band is a 0.15 mm deep, 1.5 mm wide groove, 0.5 mm in from
  the cathode end, standing in for the printed band;
- modelled lying along x, cathode at +x, its axis on the x axis, centred.
"""
import cadquery as cq

# in mm
body_length = 9.5
body_d = 5.3
lead_d = 1.3
lead_length = 25.4  # each
band_w = 1.5
band_depth = 0.15
band_inset = 0.5  # from the cathode end

length = body_length + 2 * lead_length  # overall, lead tip to lead tip
cathode_x = body_length / 2

body = cq.Workplane("YZ", origin=(-body_length / 2, 0, 0)).circle(body_d / 2).extrude(body_length)
band = (cq.Workplane("YZ", origin=(cathode_x - band_inset - band_w, 0, 0))
        .circle(body_d / 2).circle(body_d / 2 - band_depth).extrude(band_w))
leads = (cq.Workplane("YZ", origin=(-length / 2, 0, 0)).circle(lead_d / 2).extrude(length))
result = body.cut(band).union(leads)

regions = {
    "anode_lead": result.faces("<X"),  # the anode lead's tip
    "cathode_lead": result.faces(">X"),
    "body": result.faces("%CYLINDER").filter(
        lambda f: abs(f.BoundingBox().zlen - body_d) < 1e-3),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
