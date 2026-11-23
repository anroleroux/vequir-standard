"""Radial MLCC capacitor, 5.08 mm pitch, formed for a board.

A through-hole multilayer ceramic capacitor: a small epoxy-dipped block on
two radial leads 0.2 in (5.08 mm) apart, standing on a board.

Assumptions where the description is silent:
- the body is 4.0 x 2.5 mm and 3.5 mm tall, its edges rounded 0.6 mm
  (typical of a 100 nF dipped MLCC); the leads 0.5 mm round;
- the body stands 1.0 mm above the board on its leads, which go through
  and are cut 3.0 mm below the board's top;
- modelled with the board's top on z = 0, the leads along x at +-2.54.
"""
import cadquery as cq

# in mm
body = (4.0, 2.5, 3.5)  # along x, across, tall
fillet = 0.6
lead_d = 0.5
pitch = 5.08  # 0.2 in
standoff = 1.0
below = 3.0
hole = 1.0

lead_xs = [-pitch / 2, pitch / 2]
height = standoff + body[2]

block = (cq.Workplane("XY", origin=(0, 0, standoff)).box(*body, centered=(True, True, False))
         .edges().fillet(fillet))
leads = (cq.Workplane("XY", origin=(0, 0, -below))
         .pushPoints([(x, 0) for x in lead_xs]).circle(lead_d / 2).extrude(below + standoff + 0.5))
result = block.union(leads)

regions = {
    "leads": result.faces("<Z"),
    "top": result.faces(">Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
