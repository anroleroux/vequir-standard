"""The bought-in parts: built and checked against their nominal sizes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cad.catalog import discover_all
from cad.part import build_part

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "library"


def _summary(result):
    assert result.ok, result.error
    return json.loads(result.files["summary"].read_text())


def test_the_library_holds_the_standard_parts():
    assert sorted(e.designation for e in discover_all(ROOT / "products")) == [
        "actuators/motor_130", "actuators/sg90", "actuators/sg90_horn", "electronics/box_header_2x5", "electronics/buzzer_12x9",
        "electronics/capacitor_mlcc", "electronics/diode_1n5822", "electronics/ds18b20", "electronics/led_ir_5mm", "electronics/npn_bc337", "electronics/phototransistor_5mm", "electronics/pico_2w", "electronics/resistor_025w", "electronics/resistor_025w_inline", "electronics/tsd_1166_button", "electronics/usb_c_breakout", "electronics/ws2812_stick_8",
        "hardware/m1_2x3_countersunk", "hardware/m1_2x6_countersunk",
        "power/bms_1s_3a", "power/bms_3s_20a", "power/cell_18650", "power/cn3302_charger",
        "power/holder_18650_1s", "power/ip6505_charger", "power/keystone_1107_1", "power/mt3608_boost",
        "power/tp4056_charger"]


def test_the_18650_cell_is_18_4_by_65_standing_up(tmp_path):
    cell = _summary(build_part(LIBRARY / "power/cell_18650/part.py", tmp_path / "out"))
    assert cell["bounding_box"]["size"] == pytest.approx([18.4, 18.4, 65.0])
    assert cell["bounding_box"]["min"][2] == pytest.approx(0)  # negative end on z = 0


def test_the_m1_2_screw_is_6_long_with_a_2_3_head(tmp_path):
    screw = _summary(build_part(LIBRARY / "hardware/m1_2x6_countersunk/part.py", tmp_path / "out"))
    assert screw["bounding_box"]["size"][1:] == pytest.approx([2.3, 6.0])  # head across, length


def test_the_short_m1_2_screw_is_3_long_with_the_same_head(tmp_path):
    screw = _summary(build_part(LIBRARY / "hardware/m1_2x3_countersunk/part.py", tmp_path / "out"))
    assert screw["bounding_box"]["size"][1:] == pytest.approx([2.3, 3.0])  # head across, length


def test_the_keystone_1107_1_clip_is_a_quarter_inch_wide(tmp_path):
    clip = _summary(build_part(LIBRARY / "power/keystone_1107_1/part.py", tmp_path / "out"))
    assert clip["bounding_box"]["size"][1:] == pytest.approx([6.35, 13.7])  # 0.250 in, 0.538 in


def test_the_3s_bms_is_the_listed_size_with_its_pads(tmp_path):
    """DIY Electronics' 3S protection module: 64 x 20 x 3.4 mm, a B- and a P-
    pad at the ends, and three balance taps."""
    summary = _summary(build_part(LIBRARY / "power/bms_3s_20a/part.py", tmp_path / "out"))
    assert summary["bounding_box"]["size"] == pytest.approx([64.0, 20.0, 3.4])
    assert {k: v["count"] for k, v in summary["regions"].items()} == {
        "b_minus_pad": 1, "p_minus_pad": 1, "p_plus_pad": 1, "balance_pads": 3,
        "terminal_holes": 6, "bottom": 1}


def test_the_charger_boards_are_the_listed_sizes(tmp_path):
    """The IP6505 USB-A board is 34.3 x 17 mm and 10 mm high, the CN3302 2S
    USB-C board 25 x 18 mm and 6 mm high (each port may stand proud of its end)."""
    ip6505 = _summary(build_part(LIBRARY / "power/ip6505_charger/part.py", tmp_path / "ip"))
    cn3302 = _summary(build_part(LIBRARY / "power/cn3302_charger/part.py", tmp_path / "cn"))
    assert ip6505["bounding_box"]["size"][1:] == pytest.approx([17.0, 10.0])
    assert ip6505["bounding_box"]["size"][0] >= 34.3
    assert cn3302["bounding_box"]["size"][1:] == pytest.approx([18.0, 6.0])
    assert cn3302["bounding_box"]["size"][0] >= 25.0


def test_the_pico_2_w_has_its_pins_and_mounting_holes(tmp_path):
    """51 x 21 mm on a 1 mm board, the micro-USB 1.3 mm proud of its end; 40
    pin holes, 40 castellations, 4 mounting holes and 3 debug pads."""
    summary = _summary(build_part(LIBRARY / "electronics/pico_2w/part.py", tmp_path / "out"))
    assert summary["bounding_box"]["size"] == pytest.approx([52.3, 21.0, 3.6])
    assert summary["face_types"]["CYLINDER"] == 40 + 40 + 4 + 3
    assert summary["regions"]["mounting_holes"]["count"] == 4
    assert summary["regions"]["pin_strips"]["count"] == 2
    assert summary["regions"]["debug_pads"]["count"] == 1


def test_the_sg90_servo_is_its_listed_size_with_tabs_and_shaft(tmp_path):
    """A 22.8 x 12.2 x 22.7 mm case, 32.2 mm across its tabs, the shaft's top
    29.7 mm up (case, gear housing, shaft), its axis at the origin."""
    servo = _summary(build_part(LIBRARY / "actuators/sg90/part.py", tmp_path / "servo"))
    box = servo["bounding_box"]
    assert box["size"] == pytest.approx([32.2, 12.2, 29.7])
    assert box["max"][0] == pytest.approx(10.6)  # the tab past the shaft's end
    assert servo["regions"]["mounting_holes"]["count"] == 2
    horn = _summary(build_part(LIBRARY / "actuators/sg90_horn/part.py", tmp_path / "horn"))
    assert horn["bounding_box"]["size"] == pytest.approx([19.5, 7.0, 4.0])  # hub to the arm's end
    assert horn["regions"]["hole"]["count"] == 1


def test_the_130_motor_is_20_by_15_by_25_with_its_shaft(tmp_path):
    """A 20 mm can with flats 15 mm apart, 25 mm long behind its front face,
    the 2 mm shaft 9.6 mm out of it."""
    motor = _summary(build_part(LIBRARY / "actuators/motor_130/part.py", tmp_path / "motor"))
    box = motor["bounding_box"]
    assert box["size"] == pytest.approx([20.0, 15.0, 34.6])
    assert box["min"][2] == pytest.approx(-25.0) and box["max"][2] == pytest.approx(9.6)
    assert motor["regions"]["flats"]["count"] == 2


def test_the_ls1_boards_are_their_listed_sizes(tmp_path):
    """The 1S BMS strip 30.3 x 3.7 x 2.0 mm (Mantech's L, W, T), the MT3608
    board 36 x 17 mm, the USB-C breakout 20.2 x 14 x 4.8 mm and the WS2812
    stick 51.1 x 10.2 mm with eight LEDs."""
    def size(p):
        return _summary(build_part(LIBRARY / p / "part.py", tmp_path / p))
    assert size("power/bms_1s_3a")["bounding_box"]["size"] == pytest.approx([30.3, 3.7, 2.0])
    assert size("power/mt3608_boost")["bounding_box"]["size"][:2] == pytest.approx([36.0, 17.0])
    usbc = size("electronics/usb_c_breakout")
    assert usbc["bounding_box"]["size"] == pytest.approx([14.0, 20.2, 4.8])
    assert usbc["regions"]["pin_holes"]["count"] == 8
    stick = size("electronics/ws2812_stick_8")
    assert stick["bounding_box"]["size"][:2] == pytest.approx([51.1, 10.2])
    assert stick["regions"]["led_tops"]["count"] == 8
    button = size("electronics/tsd_1166_button")
    assert button["regions"]["button"]["count"] == 1  # the 10 mm button


def test_the_buzzer_and_the_ds18b20_are_their_listed_sizes(tmp_path):
    """The buzzer 12 mm across and 9 mm tall over its 5.5 mm pins; the
    DS18B20 a TO-92, 4.6 mm across its flat."""
    buzzer = _summary(build_part(LIBRARY / "electronics/buzzer_12x9/part.py", tmp_path / "bz"))
    assert buzzer["bounding_box"]["size"] == pytest.approx([12.0, 12.0, 14.5])
    assert buzzer["regions"]["pins"]["count"] == 2
    sensor = _summary(build_part(LIBRARY / "electronics/ds18b20/part.py", tmp_path / "ds"))
    assert sensor["bounding_box"]["size"][:2] == pytest.approx([2 * 2.54 + 0.45, 3.6])  # legs at 0.1 in
    assert sensor["regions"]["leads"]["count"] == 3


def test_the_tp4056_module_and_the_1n5822_are_their_sizes(tmp_path):
    """The TP4056 board 28 x 17 mm with its six pads, the USB-C 0.6 mm proud;
    the 1N5822 a 9.5 x 5.3 mm DO-201AD body, formed for 0.6 in, its 1.3 mm
    leads cut 3 mm under the board's top."""
    tp = _summary(build_part(LIBRARY / "power/tp4056_charger/part.py", tmp_path / "tp"))
    assert tp["bounding_box"]["size"][:2] == pytest.approx([28.6, 17.0])
    assert {k for k in tp["regions"]} >= {"in_plus", "in_minus", "b_plus", "b_minus", "out_plus", "out_minus"}
    diode = _summary(build_part(LIBRARY / "electronics/diode_1n5822/part.py", tmp_path / "d"))
    assert diode["bounding_box"]["size"] == pytest.approx([15.24 + 1.3, 5.3, 5.3 + 3.0])


def test_the_formed_resistor_and_transistor_fit_the_0_1_in_grid(tmp_path):
    """The resistor's leads 0.4 in apart, the BC337's legs 0.1 in apart."""
    r = _summary(build_part(LIBRARY / "electronics/resistor_025w/part.py", tmp_path / "r"))
    assert r["bounding_box"]["size"][0] == pytest.approx(10.16 + 0.6)
    q = _summary(build_part(LIBRARY / "electronics/npn_bc337/part.py", tmp_path / "q"))
    assert q["bounding_box"]["size"][0] == pytest.approx(2 * 2.54 + 0.45)
    assert q["regions"]["legs"]["count"] == 3


def test_the_box_header_is_2_x_5_with_its_opening_forward(tmp_path):
    header = _summary(build_part(LIBRARY / "electronics/box_header_2x5/part.py", tmp_path / "out"))
    assert header["bounding_box"]["size"][:2] == pytest.approx([20.3, 9.0])  # along the rows, deep
    assert header["bounding_box"]["max"][2] == pytest.approx(8.9)  # off the board
    assert header["regions"]["pins"]["count"] == 10


def test_the_ir_led_and_phototransistor_are_5_mm_with_a_flange(tmp_path):
    for item in ("electronics/led_ir_5mm", "electronics/phototransistor_5mm"):
        part = _summary(build_part(LIBRARY / item / "part.py", tmp_path / item.split("/")[1]))
        assert part["bounding_box"]["size"][1] == pytest.approx(5.8)  # the flange, across
        assert part["bounding_box"]["max"][2] == pytest.approx(8.6)  # the dome's top
        assert part["regions"]["leads"]["count"] == 2

