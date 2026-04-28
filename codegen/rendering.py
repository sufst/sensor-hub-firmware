from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from codegen.models import SensorConfig

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def render_outputs(
    config: SensorConfig,
    analog_groups: list[dict],
    digital_groups: list[dict],
    i2c_groups: list[dict],
) -> tuple[str, str, str]:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    ctx = {
        "ecu_name":       config.ecu_name,
        "analog_groups":  analog_groups,
        "digital_groups": digital_groups,
        "i2c_groups":     i2c_groups,
        "all_messages":   analog_groups + digital_groups + i2c_groups,
    }
    header = env.get_template("sensor_hub.h.j2").render(**ctx)
    source = env.get_template("sensor_hub.c.j2").render(**ctx)
    dbc = env.get_template("sensor_hub_append.dbc.j2").render(**ctx)
    return header, source, dbc
