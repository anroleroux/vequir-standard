"""18650 holder, 1 cell, wire leads.

An open single-cell 18650 tray (Micro Robotics 18650-1S-WIRE): a floor,
two low side walls and two taller end walls, a flat contact plate inside
the positive (+x) end and a coil spring inside the negative (-x) end. The
cell is not part of it: an assembly lays power/cell_18650 in it, its axis
axis_height above the bottom, its negative end at cell_x0.

Assumptions where the description is silent (the supplier gives only the
21 mm height; the rest are a typical holder's sizes, to be checked against
the real one):
- 77.0 mm long and 21.0 mm wide outside, 21.0 mm tall at the end walls;
  the floor and side walls 1.2 mm thick, the side walls 14.0 mm tall; the
  end walls 2.0 mm thick;
- the contact plate is 1.0 mm thick, 10 mm wide and 12 mm tall; the spring
  is a 7 mm long coil, 8 mm across, of 0.8 mm wire, modelled as a plain
  tube (the turns not modelled), from the negative end wall to the cell;
- the wires are not modelled;
- modelled standing on z = 0, centred on x and y, its length along x,
  the positive end at +x.
"""
import cadquery as cq

# in mm
length = 77.0  # along x
width = 21.0  # along y
height = 21.0  # at the end walls
floor_t = 1.2
side_t = 1.2
side_h = 14.0
end_t = 2.0
plate_t = 1.0
plate = (10.0, 12.0)  # across, tall
spring_d = 8.0
spring_wire = 0.8
cell_diameter = 18.4  # the cell it takes (power/cell_18650)

inner_length = length - 2 * end_t
axis_height = floor_t + cell_diameter / 2  # the cell's axis, resting on the floor
cell_x1 = length / 2 - end_t - plate_t  # the cell's positive end, against the plate
spring_length = inner_length - plate_t - 65.0  # to a 65 mm cell
cell_x0 = -length / 2 + end_t + spring_length  # its negative end, on the spring

tray = cq.Workplane("XY").box(length, width, side_h, centered=(True, True, False))
tray = tray.cut(cq.Workplane("XY", origin=(0, 0, floor_t))
                .box(inner_length, width - 2 * side_t, side_h, centered=(True, True, False)))
ends = (cq.Workplane("XY").pushPoints([(s * (length / 2 - end_t / 2), 0) for s in (-1, 1)])
        .rect(end_t, width).extrude(height))
contact = (cq.Workplane("XY", origin=(length / 2 - end_t - plate_t / 2, 0, axis_height - plate[1] / 2))
           .rect(plate_t, plate[0]).extrude(plate[1]))
spring = (cq.Workplane("YZ", origin=(-length / 2 + end_t, 0, axis_height))
          .circle(spring_d / 2).circle(spring_d / 2 - spring_wire).extrude(spring_length))
result = tray.union(ends).union(contact).union(spring)

regions = {
    "bottom": result.faces("<Z"),
    "floor": result.faces("%PLANE").filter(  # where the cell rests
        lambda f: f.normalAt().z > 0.999 and abs(f.Center().z - floor_t) < 1e-6),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
