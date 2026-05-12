import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Annotated
from pydantic import Field, StringConstraints, PlainValidator

from codegen.constants import PIN_TO_ADC, MAX_ANALOG_PER_MSG, MAX_DIGITAL_PER_MSG

DbcIdentifier = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$", max_length=32)
]

Can11BitId = Annotated[int, Field(ge=0x000, le=0x7FF)]

PIN_RE = re.compile(r"^P([A-H])(\d{1,2})$")


@dataclass(frozen=True)
class Stm32Pin:
    raw: str
    port: str
    pin_macro: str


def parse_pin(v: str) -> Stm32Pin:
    v_upper = v.upper()
    match = PIN_RE.match(v_upper)
    if not match:
        raise ValueError(f"Invalid pin format: '{v}'. Expected e.g. 'PA5'.")
    return Stm32Pin(
        raw=v_upper,
        port=f"GPIO{match.group(1)}",
        pin_macro=f"GPIO_PIN_{match.group(2)}"
    )


PinField = Annotated[Stm32Pin, PlainValidator(parse_pin)]


def check_duplicate_names(channels: list):
    names = [c.name for c in channels]
    if dupes := [n for n, cnt in Counter(names).items() if cnt > 1]:
        raise ValueError(f"Duplicate enabled signal names: {dupes}")


def check_duplicate_pins(channels: list):
    pins = [c.pin.raw for c in channels]
    if dupes := [p for p, cnt in Counter(pins).items() if cnt > 1]:
        raise ValueError(f"Physical pin routing collision: {dupes}")


def check_hardware_capabilities(channels: list):
    for ch in channels:
        if ch.analog and ch.pin.raw not in PIN_TO_ADC:
            raise ValueError(
                f"Signal '{ch.name}' requested analog, but pin {ch.pin.raw} "
                f"does not support ADC. Supported: {list(PIN_TO_ADC.keys())}"
            )


def check_can_id_collisions(enabled_analog: int, enabled_digital: int, base_ids: dict[str, int]):
    n_analog = math.ceil(enabled_analog / MAX_ANALOG_PER_MSG)
    n_digital = math.ceil(enabled_digital / MAX_DIGITAL_PER_MSG)

    ranges = []
    if n_analog > 0:
        ranges.append(
            ("Analog", base_ids["analog"], base_ids["analog"] + n_analog))
    if n_digital > 0:
        ranges.append(
            ("Digital", base_ids["digital"], base_ids["digital"] + n_digital))

    ranges.append(("I2C", base_ids["i2c"], base_ids["i2c"] + 3))
    ranges.append(("Status", base_ids["status"], base_ids["status"] + 1))

    for i, (name_a, start_a, end_a) in enumerate(ranges):
        for name_b, start_b, end_b in ranges[i + 1:]:
            if start_a < end_b and start_b < end_a:
                raise ValueError(
                    f"CAN ID collision: {name_a} (0x{start_a:X}-0x{end_a-1:X}) "
                    f"overlaps {name_b} (0x{start_b:X}-0x{end_b-1:X})"
                )
