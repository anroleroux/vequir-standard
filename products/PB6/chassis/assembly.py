"""Chassis base with the six-cell 18650 pack.

The base with the six-cell 18650 pack from the parts library
(battery_holders/pack_3x2) on its floor: three holders side by side across
the breadth, in two rows, their length along x, its back end against the
base's back end wall (-x).
Two IP6505 USB fast-charge boards sit side by side on the floor in front of
the pack, their USB ports against the front wall, each behind one of the
wall's USB-A holes, and a CN3302 2S charger board sits beside them at +y,
its USB-C port behind the wall's USB-C hole. Eight M1.2 x 6 countersunk screws, two through each of the end
strips' four tabs, fix the pack to the base's pillars.

The base and the boards come from their own scripts through load_part and
the pack through load_library, so the assembly follows any change to them.

The summary's interference lists each pillar screw against the base: that is
the screw's 1.2 mm shank forming its thread in the pillar's 0.95 mm tap hole,
as intended.

Assumptions where the description is silent:
- the pack is centred across the breadth and stands on the floor, its back
  end (the tips of its back end strip's tabs) against the back wall;
- the cells are wired as two groups of three in parallel, in series (2S3P,
  8.4 V full), to suit the 2S charger; the wiring is not modelled.
"""
import cadquery as cq

base = load_part("base")  # floor and end walls at +-x, standing on z = 0
pack = load_library("battery_holders/pack_3x2")  # the six-cell pack, standing on z = 0
ip6505 = load_part("ip6505_charger")  # USB-A port at +x, underside on z = 0
cn3302 = load_part("cn3302_charger")  # USB-C port at +x, underside on z = 0

# move the pack's back end onto the inside of the back wall, centre it across
# the breadth and stand it on the floor
screw = load_library("fasteners/m1_2x6_countersunk")  # standing up: tip on z = 0
pack_loc = cq.Location((base.pack_dx, base.pack_dy, base.pack_dz))

result = (
    cq.Assembly(name="chassis")
    .add(base.result, name="base", color=cq.Color(0.36, 0.56, 0.78))
    .add(pack.result, name="pack_3x2", loc=pack_loc)
)

# the USB boards where the base's plug holes expect them
board_green = cq.Color(0.15, 0.45, 0.30)
for i, y in enumerate(base.ip6505_ys):
    result.add(
        ip6505.result,
        name=f"ip6505_charger_{i + 1}",
        loc=cq.Location((base.ip6505_x, y, base.ip6505_z)),
        color=board_green,
    )
result.add(
    cn3302.result,
    name="cn3302_charger",
    loc=cq.Location((base.cn3302_x, base.cn3302_y, base.cn3302_z)),
    color=board_green,
)


# the pack fixed down: an M1.2 x 6 screw through each tab hole into its
# pillar, the head flush in the tab's countersink
screw_top = base.pack_dz + pack.tab_top
for i, (x, y) in enumerate(base.pillar_holes, start=1):
    result.add(screw.result, name=f"pillar_screw_{i}",
               loc=cq.Location((x, y, screw_top - screw.length)),
               color=cq.Color(0.70, 0.70, 0.72))

regions = {}

if "show_object" in globals():  # CQ-editor (load_part runs under neobotics only)
    show_object(result, name="chassis")
