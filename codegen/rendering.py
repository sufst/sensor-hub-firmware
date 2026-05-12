from pathlib import Path

import cantools
from jinja2 import Environment, FileSystemLoader

from codegen.models.config import SensorConfig
from codegen.models.view import HardwareView, MessageView

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def render_outputs(
    config: SensorConfig,
    messages: list[MessageView],
) -> tuple[str, str, str]:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    hardware = HardwareView(
        prescaler=config.hardware.prescaler,
        period=config.hardware.period,
        led_port=config.hardware.error_led.port,
        led_pin=config.hardware.error_led.pin_macro,
    )
    status_id = config.can_base_ids.status
    # I2C frames are transmitted from SUFST/Src/sensors.c, not SensorHub_Transmit
    c_messages = [m for m in messages if m.c_signals]

    header = env.get_template("sensor_hub.h.j2").render(
        messages=messages,
        hardware=hardware,
        status_id_hex=f"0x{status_id:X}",
    )
    source = env.get_template("sensor_hub.c.j2").render(
        messages=c_messages,
        hardware=hardware,
    )
    dbc = env.get_template("ecu.dbc.j2").render(
        ecu_name=config.ecu_name,
        all_messages=messages,
        status_id=status_id,
        status_id_hex=f"0x{status_id:X}",
    )

    try:
        cantools.database.load_string(dbc)
    except cantools.database.UnsupportedDatabaseFormatError as exc:
        raise RuntimeError(f"Generated DBC failed cantools round-trip: {exc}") from exc

    return header, source, dbc
