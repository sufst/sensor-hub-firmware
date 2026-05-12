from dataclasses import dataclass
from typing import Sequence


@dataclass
class AnalogRead:
    name: str
    adc_channel: str
    board_id: str
    stm32_pin: str

    @property
    def is_analog(self) -> bool:
        return True


@dataclass
class DigitalRead:
    name: str
    gpio_port: str
    gpio_pin: str
    board_id: str
    stm32_pin: str

    @property
    def is_analog(self) -> bool:
        return False


ChannelRead = AnalogRead | DigitalRead


@dataclass
class DbcSignalView:
    signal_name: str
    start_bit: int
    length: int
    scale: str
    offset: str
    min: str
    max: str
    unit: str
    value_type: str = "@1+"


@dataclass
class MessageView:
    name: str
    can_id: int
    can_id_hex: str
    id_macro: str  # {msg_name}_ID
    dlc: int
    dlc_macro: str  # {msg_name}_DLC
    pack_lines: list[str]
    c_signals: Sequence[ChannelRead]
    dbc_signals: Sequence[DbcSignalView]


@dataclass
class HardwareView:
    prescaler: int
    period: int
    led_port: str
    led_pin: str
