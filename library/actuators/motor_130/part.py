"""130-size DC motor

The standard small brushed DC motor, size 130 (Mabuchi FA-130 and its many
equivalents): a round can with two flats, its front face carrying the
shaft's bearing boss and two mounting holes, and a 2 mm output shaft.

Assumptions where the description is silent:
- nominal dimensions; check them against the motor in hand: the body
  20 mm across, with flats 15 mm apart, 25 mm long including the end bell;
  the bearing boss 6.2 mm across and 1.6 mm proud of the front face; the
  shaft 2.0 mm, standing 9.6 mm out of the front face;
- two M2 tapped mounting holes in the front face, 12 mm apart across the
  flats' width (along x), 3 mm deep;
- the terminals and the rear bearing's boss on the end bell are not
  modelled;
- modelled with the shaft's axis along +z, the front face on z = 0 and the
  body behind it (z = -25 to 0), the flats facing +-y.
"""
import cadquery as cq

# parameters, in mm
diameter = 20.0  # the can, across its round sides (along x)
flats = 15.0  # across the flats (along y)
length = 25.0  # the body, behind the front face
boss_diameter = 6.2
boss_height = 1.6
shaft_diameter = 2.0
shaft_length = 9.6  # out of the front face
mount_hole_spacing = 12.0  # along x
mount_hole_diameter = 1.6  # M2 tapped
mount_hole_depth = 3.0

body = (cq.Workplane("XY", origin=(0, 0, -length)).circle(diameter / 2).extrude(length)
        .intersect(cq.Workplane("XY", origin=(0, 0, -length)).rect(diameter, flats)
                   .extrude(length)))
boss = cq.Workplane("XY").circle(boss_diameter / 2).extrude(boss_height)
shaft = cq.Workplane("XY", origin=(0, 0, -1)).circle(shaft_diameter / 2).extrude(shaft_length + 1)
holes = (cq.Workplane("XY", origin=(0, 0, -mount_hole_depth))
         .pushPoints([(-mount_hole_spacing / 2, 0), (mount_hole_spacing / 2, 0)])
         .circle(mount_hole_diameter / 2).extrude(mount_hole_depth))
result = body.union(boss).union(shaft).cut(holes)

regions = {
    "front_face": result.faces(cq.selectors.NearestToPointSelector((diameter / 2 - 2, 0, 0))),
    "shaft": result.faces("%CYLINDER").faces(cq.selectors.NearestToPointSelector(
        (shaft_diameter / 2, 0, shaft_length - 1))),
    "flats": result.faces("|Y").faces(cq.selectors.BoxSelector(
        (-diameter, -flats, -length + 1), (diameter, flats, -1))),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
