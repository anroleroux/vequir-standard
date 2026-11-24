"""M1.2 x 6 countersunk screw.

A Phillips (cross recess) countersunk (flat head) machine screw, as
DIN 965 / ISO 7046, M1.2 x 0.25,
6 mm long overall: a countersunk screw's length is measured from the top of
its head. Nominal dimensions from the standard; the thread is not modelled.

Assumptions where the description is silent:
- the standards start at M1.6, so the head is DIN 963's M1.2 head:
  diameter dk 2.3 mm, height k 0.72 mm (to the theoretical sharp edge of
  the 90 degree cone; the real head's edge is a short cylinder at dk);
  check these against the supplier's drawing;
- the cross recess is two crossed slots, 1.2 mm across the head (the
  recess diameter m), 0.3 mm wide and 0.4 mm deep, square-bottomed rather
  than the real tapered cross;
- the shank is a plain cylinder at the nominal 1.2 mm, with a 0.15 mm 45
  degree chamfer at the tip;
- modelled standing up: tip on z = 0, head on top, its top face at z = length.
"""
import math

import cadquery as cq

# parameters, in mm
diameter = 1.2  # nominal, M1.2
pitch = 0.25  # coarse thread (not modelled)
length = 6.0  # overall, head included
head_diameter = 2.3  # dk
head_height = 0.72  # k
countersink_angle = 90.0  # included, degrees
recess_m = 1.2  # the cross recess, across the head
recess_width = 0.3  # each arm
recess_depth = 0.4
tip_chamfer = 0.15

half_angle = math.radians(countersink_angle / 2)
cone_height = (head_diameter - diameter) / 2 / math.tan(half_angle)  # shank to dk
edge_height = head_height - cone_height  # the short cylinder at dk, on top
shank_length = length - head_height

shank = (
    cq.Workplane("XY")
    .circle(diameter / 2)
    .extrude(shank_length)
    .faces("<Z").edges().chamfer(tip_chamfer)
)
cone = cq.Solid.makeCone(diameter / 2, head_diameter / 2, cone_height,
                         cq.Vector(0, 0, shank_length))
edge = cq.Workplane("XY", origin=(0, 0, shank_length + cone_height)).circle(
    head_diameter / 2).extrude(edge_height)
recess = (
    cq.Workplane("XY", origin=(0, 0, length - recess_depth))
    .rect(recess_m, recess_width).extrude(recess_depth)
    .union(cq.Workplane("XY", origin=(0, 0, length - recess_depth))
           .rect(recess_width, recess_m).extrude(recess_depth))
)
result = shank.union(cq.Workplane("XY").add(cone)).union(edge).cut(recess)

regions = {
    "head_top": result.faces(">Z"),  # flush with the countersunk surface
    "tip": result.faces("<Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
