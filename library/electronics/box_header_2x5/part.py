"""2 x 5 box header, right-angle.

A shrouded 10-pin IDC header at 0.1 in (2.54 mm) pitch, right-angle: the
shroud lies on the board, its opening facing along the board, and the two
rows of five pins bend down through it.

Assumptions where the description is silent (typical catalogue sizes; check
them against the supplier's drawing):
- the shroud is 20.3 mm long (along the rows), 8.9 mm high off the board
  and 9.0 mm deep (from its opening to its back); its cavity is 15.4 x
  6.2 mm and 6.0 mm deep, centred in its face, with a 4.5 mm key notch
  through the top wall from the face back to the cavity's bottom;
- the pins are 0.64 mm square; the row nearer the opening (row A) runs out
  of the cavity 3.18 mm above the board, the other (row B, 2.54 mm further
  back) 5.72 mm above it, so the two are centred in the shroud's height;
  their tips stand 0.5 mm back from the face; they reach 3.0 mm below the
  board's top (through a 1.6 mm board and 1.4 mm out);
- modelled with the board's top on z = 0: the rows along x, centred, row A
  at y = 0 and row B at y = +2.54, the opening facing -y, its face
  front_off = 5.16 mm in front of row A.
"""
import cadquery as cq

# in mm
pitch = 2.54
n = 5  # pins per row
length = 20.3  # shroud, along x
height = 8.9  # off the board, along z
depth = 9.0  # opening to back, along y
cavity = (15.4, 6.2)  # along x and z
cavity_depth = 6.0
key_w = 4.5  # the notch in the top wall
pin = 0.64  # square
row_z = (3.18, 5.72)  # rows A and B, above the board
row_y = (0.0, pitch)  # rows A and B, from row A
tip_back = 0.5  # the pins' tips, back from the face
below = 3.0  # the pins' cut ends, under the board's top
back_past_b = 1.3  # the shroud's back, behind row B

back_y = row_y[1] + back_past_b
front_off = depth - back_y  # the face, in front of row A
face_y = -front_off
pin_xs = [(i - (n - 1) / 2) * pitch for i in range(n)]

shroud = cq.Workplane("XY", origin=(0, face_y, 0)).box(length, depth, height, centered=(True, False, False))
pocket = (cq.Workplane("XY", origin=(0, face_y, height / 2 - cavity[1] / 2))
          .box(cavity[0], cavity_depth, cavity[1], centered=(True, False, False)))
key = (cq.Workplane("XY", origin=(0, face_y, height / 2))
       .box(key_w, cavity_depth, height / 2, centered=(True, False, False)))
result = shroud.cut(pocket).cut(key)
for y, z in zip(row_y, row_z):
    for x in pin_xs:
        down = cq.Workplane("XY", origin=(x, y, -below)).rect(pin, pin).extrude(below + z + pin / 2)
        out = (cq.Workplane("XZ", origin=(x, y + pin / 2, z)).rect(pin, pin)
               .extrude(y + pin / 2 - (face_y + tip_back)))  # "XZ" extrudes toward -y
        result = result.union(down).union(out)

regions = {
    "face": result.faces("<Y"),  # the opening's face, where the cable's socket goes in
    "bottom": result.faces("%PLANE").filter(  # on the board
        lambda f: f.normalAt().z < -0.999 and abs(f.Center().z) < 1e-6),
    "pins": result.faces("<Z"),  # the pins' cut ends, under the board
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
