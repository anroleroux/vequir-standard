"""5 mm phototransistor.

A 5 mm NPN phototransistor in the clear T-1 3/4 LED package (Micro
Robotics BP0334): the same body, dome, flange and leads as a 5 mm LED, so
the model is electronics/led_ir_5mm's.

Assumptions where the description is silent:
- the package's sizes are a 5 mm LED's (see electronics/led_ir_5mm); the
  collector lead at +x, beside the flange's flat, the emitter at -x;
- modelled standing up: the flange's underside on z = 0, the lens toward
  +z, the leads below.
"""
import cadquery as cq

led = load_library("electronics/led_ir_5mm")  # the same package

body_d, height, flange_d, flange_t, lead = led.body_d, led.height, led.flange_d, led.flange_t, led.lead
result = led.result

regions = {
    "flange_top": result.faces("%PLANE").filter(
        lambda f: f.normalAt().z > 0.999 and abs(f.Center().z - flange_t) < 1e-6),
    "leads": result.faces("<Z"),
}

if "show_object" in globals():  # CQ-editor
    show_object(result, name="part")
