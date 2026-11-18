"""TP4056 1 A charger module with protection, USB-C.

The common single-cell lithium charger board: a USB-C receptacle at one
end with the IN+ and IN- pads beside it, the TP4056 charger, the DW01
protection IC and the 8205A MOSFETs, two charge LEDs, and the B+, B-,
OUT+ and OUT- pads at the other end.

Assumptions where the description is silent (typical of the boards sold,
not measured):
- the board is 28 x 17 mm and 1.2 mm thick;
- the USB-C receptacle is a top-mount one as on the CN3302 (8.94 x 3.26 mm
  shell, 7.35 mm deep), its mouth 0.6 mm proud of the board's +x end, centred
  across it, so the module is 4.46 mm high overall;
- the IN+ and IN- pads (2.0 x 3.0 mm) sit in the corners beside the
  receptacle, IN+ at +y; at the far end OUT+ and OUT- in the corners (OUT+
  at +y) and B+ and B- between them (B+ at +y), each 2.0 x 2.5 mm, 0.1 mm
  thick, 0.5 mm in from the end;
- the TP4056 (SOP-8, 5 x 4 x 1.5 mm), the DW01 (SOT-23-6) and the 8205A
  (TSSOP-8 body) are blocks; the LEDs 1.6 x 0.8 x 0.6 mm; the resistors and
  capacitors are not modelled;
- on these boards IN- and OUT- are joined; B- reaches them through the
  8205A, so the protected side is OUT+ and OUT- (and IN-);
- x along the board, USB-C at +x, y across it, z up; centred on x and y,
  underside on z = 0.
"""
import cadquery as cq

# the board, in mm
length = 28.0  # along x
width = 17.0  # along y
pcb_t = 1.2  # board thickness

# the USB-C receptacle, at +x
usb_w = 8.94
usb_h = 3.26
usb_d = 7.35
usb_proud = 0.6  # past the board's end
mouth_w = 8.34
mouth_h = 2.66
mouth_d = 6.5
tongue_w = 6.7
tongue_t = 0.7
tongue_d = 5.0

# the pads
in_pad = (2.0, 3.0)  # along x, across
end_pad = (2.0, 2.5)
pad_t = 0.1
pad_inset = 0.5  # from the board's end
out_y = 6.0  # OUT+ / OUT- and IN+ / IN- centres, off the centre line
b_y = 2.2  # B+ / B- centres

# the chips: (along x, across, height) at (x, y)
chips = [((5.0, 4.0, 1.5), (0.0, 0.0)),  # TP4056, SOP-8
         ((2.9, 1.6, 1.1), (-7.0, -4.5)),  # DW01, SOT-23-6
         ((4.4, 3.0, 1.0), (-7.0, 4.0)),  # 8205A, TSSOP-8
         ((1.6, 0.8, 0.6), (4.5, -5.5)),  # charging LED
         ((1.6, 0.8, 0.6), (4.5, 5.5))]  # done LED

usb_x1 = length / 2 + usb_proud
usb_axis_z = pcb_t + usb_h / 2
height = pcb_t + usb_h

board = cq.Workplane("XY").box(length, width, pcb_t, centered=(True, True, False))
shell = cq.Workplane("YZ", origin=(usb_x1 - usb_d, 0, usb_axis_z)).slot2D(usb_w, usb_h).extrude(usb_d)
mouth = cq.Workplane("YZ", origin=(usb_x1, 0, usb_axis_z)).slot2D(mouth_w, mouth_h).extrude(-mouth_d)
tongue = (cq.Workplane("YZ", origin=(usb_x1 - mouth_d, 0, usb_axis_z))
          .rect(tongue_w, tongue_t).extrude(tongue_d))
result = board.union(shell.cut(mouth).union(tongue))

in_x = length / 2 - pad_inset - in_pad[0] / 2
end_x = -length / 2 + pad_inset + end_pad[0] / 2
pads = {
    "in_plus": (in_x, out_y, in_pad), "in_minus": (in_x, -out_y, in_pad),
    "b_plus": (end_x, b_y, end_pad), "b_minus": (end_x, -b_y, end_pad),
    "out_plus": (end_x, out_y, end_pad), "out_minus": (end_x, -out_y, end_pad),
}
for x, y, (px, py) in pads.values():
    result = result.union(cq.Workplane("XY", origin=(x, y, pcb_t)).rect(px, py).extrude(pad_t))
for size, (x, y) in chips:
    result = result.union(cq.Workplane("XY", origin=(x, y, pcb_t)).box(*size, centered=(True, True, False)))


def _pad(name):
    x, y, _ = pads[name]
    return result.faces("+Z").filter(
        lambda f: abs(f.Center().z - (pcb_t + pad_t)) < 1e-6
        and abs(f.Center().x - x) < 1e-3 and abs(f.Center().y - y) < 1e-3)


regions = {name: _pad(name) for name in pads}
regions["usb_end"] = result.faces("+X").filter(lambda f: abs(f.Center().x - usb_x1) < 1e-6)
regions["bottom"] = result.faces("<Z")

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
