"""DS18B20 temperature sensor, TO-92, formed for a board.

The bare DS18B20 in its TO-92 package, standing on its three legs above a
board, the outer legs bent out from the package's 1.27 mm pitch to the
board's 2.54 mm.

Assumptions where the description is silent:
- the TO-92 body is 4.6 mm across the flat, 3.6 mm deep and 4.6 mm tall,
  the back an arc of a 4.8 mm circle; the legs 0.45 mm square;
- the body stands 3.0 mm above the board; the outer legs leave it at
  1.27 mm from the middle one, jog out at 1.5 mm up, and go down through
  holes 2.54 mm apart; the legs are cut 3.0 mm below the board's top;
- seen from the flat face (-y), left to right: GND, DQ, VDD (the DS18B20's
  pinout), GND at -x;
- modelled with the board's top on z = 0, the middle leg on the z axis.
"""
import cadquery as cq

# in mm
width = 4.6  # across the flat, along x
depth = 3.6  # flat to back, along y
body_h = 4.6
back_d = 4.8
lead = 0.45  # square
package_pitch = 1.27
pitch = 2.54  # on the board
standoff = 3.0  # the body's bottom, above the board
jog_z = 1.5  # where the outer legs step out
below = 3.0
hole = 1.0

flat_y = -depth / 2
back_centre = flat_y + depth - back_d / 2
lead_y = flat_y + 1.0  # the legs' line, behind the flat
lead_xs = [-pitch, 0.0, pitch]  # GND, DQ, VDD
height = standoff + body_h

body = (
    cq.Workplane("XY", origin=(0, back_centre, standoff)).circle(back_d / 2).extrude(body_h)
    .intersect(cq.Workplane("XY", origin=(0, 0, standoff))
               .center(0, flat_y + depth / 2).rect(width, depth).extrude(body_h))
)


def bar(x0, z0, x1, z1):
    """A square leg section from (x0, z0) to (x1, z1), along x or z."""
    lx, lz = abs(x1 - x0) + lead, abs(z1 - z0) + lead
    return cq.Workplane("XY").box(lx, lead, lz).translate(((x0 + x1) / 2, lead_y, (z0 + z1) / 2))


legs = bar(0, -below + lead / 2, 0, standoff)
for s in (-1, 1):
    legs = (legs.union(bar(s * package_pitch, jog_z, s * package_pitch, standoff))
            .union(bar(s * package_pitch, jog_z, s * pitch, jog_z))
            .union(bar(s * pitch, -below + lead / 2, s * pitch, jog_z)))
result = body.union(legs)

regions = {
    "flat": result.faces("<Y").filter(lambda f: f.Center().z > standoff),
    "leads": result.faces("<Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
