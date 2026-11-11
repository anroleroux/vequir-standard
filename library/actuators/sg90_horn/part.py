"""SG90 single-arm horn

The single-arm horn supplied with the SG90 micro servo: a round hub with a
socket that pushes onto the servo's splined shaft, and one tapering arm with
a hole near its end for a linkage.

Assumptions where the description is silent:
- the hub is 7.0 mm across and 4.0 mm tall, its socket the shaft's 4.8 mm
  (the spline not modelled), 3.0 mm deep, open on the servo's side;
- the arm is 1.5 mm thick, flush with the hub's far face, 5.0 mm wide at
  the hub tapering to a 4.0 mm round end 14 mm from the axis;
- the hole is drilled out to 2.0 mm at 14 mm from the axis, for a 2 mm
  pin (the horn comes with 1 mm holes at several radii);
- modelled with its axis on x = 0, y = 0, the face towards the servo on
  z = 0, the arm along +x.
"""
import cadquery as cq

servo = load_part("../sg90")  # the shaft it pushes onto

# parameters, in mm
hub_diameter = 7.0
hub_height = 4.0
socket_depth = servo.shaft_height
arm_thickness = 1.5
arm_root_width = 5.0  # at the hub
tip_diameter = 4.0  # the arm's round end
arm_length = 14.0  # the axis to the hole
hole_diameter = 2.0  # drilled out for a 2 mm pin

arm_z = hub_height - arm_thickness  # the arm's face towards the servo

hub = cq.Workplane("XY").circle(hub_diameter / 2).extrude(hub_height)
arm = (
    cq.Workplane("XY", origin=(0, 0, arm_z))
    .polyline([(0, -arm_root_width / 2), (arm_length, -tip_diameter / 2),
               (arm_length, tip_diameter / 2), (0, arm_root_width / 2)])
    .close()
    .extrude(arm_thickness)
    .union(cq.Workplane("XY", origin=(0, 0, arm_z)).center(arm_length, 0)
           .circle(tip_diameter / 2).extrude(arm_thickness))
)
socket = cq.Workplane("XY").circle(servo.shaft_diameter / 2).extrude(socket_depth)
hole = (cq.Workplane("XY", origin=(0, 0, arm_z - 1)).center(arm_length, 0)
        .circle(hole_diameter / 2).extrude(arm_thickness + 2))
result = hub.union(arm).cut(socket).cut(hole)

regions = {
    "socket": result.faces("%CYLINDER").faces(cq.selectors.NearestToPointSelector(
        (servo.shaft_diameter / 2, 0, socket_depth / 2))),
    "hole": result.faces("%CYLINDER").faces(cq.selectors.NearestToPointSelector(
        (arm_length + hole_diameter / 2, 0, arm_z + arm_thickness / 2))),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
