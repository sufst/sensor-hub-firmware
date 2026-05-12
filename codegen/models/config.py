from typing import Self
from pydantic import BaseModel, ConfigDict, Field, model_validator

from codegen.validation import DbcIdentifier, Can11BitId, PinField, check_can_id_collisions, check_duplicate_names, check_duplicate_pins, check_hardware_capabilities


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True)


class ChannelConfig(StrictModel):
    id: str
    pin: PinField
    vref: float = 3.3
    enabled: bool
    name: DbcIdentifier
    analog: bool
    series: str = "NC"  # documentation only
    pullup: str = "NC"  # documentation only
    pulldown: str = "NC"  # documentation only
    cap: str = "NC"  # documentation only


class BaseIDs(StrictModel):
    analog: Can11BitId
    digital: Can11BitId
    i2c: Can11BitId
    status: Can11BitId


class HardwareConfig(StrictModel):
    error_led: PinField
    clock_speed_hz: int = Field(gt=0)
    broadcast_period_ms: int = Field(gt=0)

    @property
    def prescaler(self) -> int:
        return int(self.clock_speed_hz / 10000) - 1

    @property
    def period(self) -> int:
        return (10 * self.broadcast_period_ms) - 1


class SensorConfig(StrictModel):
    ecu_name: DbcIdentifier
    can_base_ids: BaseIDs
    hardware: HardwareConfig
    channels: list[ChannelConfig]

    @property
    def enabled_analog(self) -> list[ChannelConfig]:
        return [c for c in self.channels if c.enabled and c.analog]

    @property
    def enabled_digital(self) -> list[ChannelConfig]:
        return [c for c in self.channels if c.enabled and not c.analog]

    @property
    def enabled(self) -> list[ChannelConfig]:
        return [c for c in self.channels if c.enabled]

    @model_validator(mode="after")
    def validate_all(self) -> Self:
        enabled = self.enabled
        check_duplicate_names(enabled)
        check_duplicate_pins(enabled)
        check_hardware_capabilities(enabled)
        check_can_id_collisions(len(self.enabled_analog), len(
            self.enabled_digital), self.can_base_ids.model_dump())
        return self
