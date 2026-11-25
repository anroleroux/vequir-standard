"""5 mm IR LED.

A 5 mm (T-1 3/4) through-hole LED, 940 nm infrared: a cylindrical body with
a hemispherical dome, a flange at its base with a flat on the cathode side,
and two leads 2.54 mm apart.

Assumptions where the description is silent (typical catalogue sizes):
- the body is 5.0 mm across and 8.6 mm from the flange's underside to the
  dome's top; the flange is 5.8 mm across and 1.0 mm thick, its flat 0.4 mm
  in from the rim;
- the leads are 0.5 mm square and cut to `lead` = 1.0 mm below the flange
  (an assembly bends and wires them; the bends are not modelled);
- modelled standing up: the flange's underside on z = 0, the dome toward
  +z, the leads below, along x (anode at -x, cathode at +x, the flat at +x).
"""
import cadquery as cq

# in mm
body_d = 5.0
height = 8.6  # flange underside to dome top
flange_d = 5.8
flange_t = 1.0
flat_in = 0.4  # the flange's flat, in from its rim (the cathode side)
lead = 1.0  # below the flange, cut short
lead_w = 0.5  # square
lead_pitch = 2.54

dome_r = body_d / 2
can_h = height - dome_r  # flange underside to where the dome starts
flange = (cq.Workplane("XY").circle(flange_d / 2).extrude(flange_t)
          .cut(cq.Workplane("XY", origin=(flange_d / 2 - flat_in, -flange_d / 2, 0))
               .box(flat_in, flange_d, flange_t, centered=False)))
body = cq.Workplane("XY").circle(body_d / 2).extrude(can_h)
dome = cq.Workplane("XY").sphere(dome_r).translate((0, 0, can_h))
dome = dome.cut(cq.Workplane("XY", origin=(0, 0, can_h - dome_r)).box(
    body_d * 2, body_d * 2, dome_r, centered=(True, True, False)))
leads = (cq.Workplane("XY", origin=(0, 0, -lead))
         .pushPoints([(-lead_pitch / 2, 0), (lead_pitch / 2, 0)])
         .rect(lead_w, lead_w).extrude(lead))
result = flange.union(body).union(dome).union(leads)

regions = {
    "flange_top": result.faces("%PLANE").filter(  # against a panel's inside
        lambda f: f.normalAt().z > 0.999 and abs(f.Center().z - flange_t) < 1e-6),
    "leads": result.faces("<Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
