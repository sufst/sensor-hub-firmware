from pathlib import Path

import yaml

from codegen.models.config import SensorConfig


def load_config(path: Path) -> SensorConfig:
    return SensorConfig.model_validate(yaml.safe_load(path.read_text()))
