"""TowerPro SG90 micro servo

The SG90 9 g micro servo: a 22.8 x 12.2 mm case 22.7 mm tall, two mounting
tabs at its ends with a screw hole each, the round gear housing on top at
one end and the splined output shaft standing up from it.

Assumptions where the description is silent:
- nominal dimensions from the maker's drawing; check them against the
  servo in hand: the case 22.8 x 12.2 x 22.7 mm; the tabs 2.5 mm thick,
  32.2 mm overall, as wide as the case, their underside 15.9 mm up; the
  screw holes 2.0 mm, 27.7 mm apart, centred on the case;
- the gear housing is a 11.8 mm cylinder, 4.0 mm tall, tangent to one end
  of the case; the output shaft is on its axis: a 4.8 mm splined shaft
  (the spline not modelled), 3.0 mm tall;
- the second, smaller boss on top, the label and the cable (leaving at the
  case's end, low down) are not modelled;
- modelled standing up, the case's bottom on z = 0, the output shaft's axis
  on x = 0, y = 0, the case reaching back along -x.
"""
import cadquery as cq

# parameters, in mm
length = 22.8  # the case, along x
width = 12.2  # the case, along y
case_height = 22.7  # the case's top, along z
tab_span = 32.2  # the tabs, overall along x
tab_thickness = 2.5
tab_bottom = 15.9  # the tabs' underside, up from the case's bottom
hole_spacing = 27.7  # the screw holes, centre to centre along x
hole_diameter = 2.0
housing_diameter = 11.8  # the gear housing on top, about the shaft
housing_height = 4.0
shaft_diameter = 4.8  # the splined output shaft
shaft_height = 3.0

shaft_offset = housing_diameter / 2  # the shaft's axis, in from the case's end
case_x = shaft_offset - length / 2  # the case's centre, along x (behind the shaft)
housing_top = case_height + housing_height  # where the horn's hub sits
shaft_top = housing_top + shaft_height

case = cq.Workplane("XY").center(case_x, 0).rect(length, width).extrude(case_height)
tabs = (cq.Workplane("XY", origin=(0, 0, tab_bottom)).center(case_x, 0)
        .rect(tab_span, width).extrude(tab_thickness))
holes = (cq.Workplane("XY", origin=(0, 0, tab_bottom - 1))
         .pushPoints([(case_x - hole_spacing / 2, 0), (case_x + hole_spacing / 2, 0)])
         .circle(hole_diameter / 2).extrude(tab_thickness + 2))
housing = (cq.Workplane("XY", origin=(0, 0, case_height)).circle(housing_diameter / 2)
           .extrude(housing_height))
shaft = (cq.Workplane("XY", origin=(0, 0, housing_top)).circle(shaft_diameter / 2)
         .extrude(shaft_height))
result = case.union(tabs).cut(holes).union(housing).union(shaft)

regions = {
    "case_top": result.faces(cq.selectors.NearestToPointSelector(
        (case_x - length / 2 + 1, 0, case_height))),
    "shaft": result.faces("%CYLINDER").faces(cq.selectors.NearestToPointSelector(
        (shaft_diameter / 2, 0, housing_top + shaft_height / 2))),
    "mounting_holes": result.faces("%CYLINDER").faces(cq.selectors.BoxSelector(
        (case_x - tab_span / 2 - 1, -width, tab_bottom - 1),
        (case_x - length / 2, width, tab_bottom + tab_thickness + 1))).add(
        result.faces("%CYLINDER").faces(cq.selectors.BoxSelector(
            (case_x + length / 2, -width, tab_bottom - 1),
            (case_x + tab_span / 2 + 1, width, tab_bottom + tab_thickness + 1)))),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
