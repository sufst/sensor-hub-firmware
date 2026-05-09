from __future__ import annotations

import json
import subprocess
from pathlib import Path


def update_presets(source_dir: Path, config_name: str, build_type: str) -> None:
    presets_file = source_dir / "CMakePresets.json"
    data = json.loads(presets_file.read_text())

    preset_name = f"{config_name}-{build_type}"
    new_configure = {
        "name": preset_name,
        "inherits": "default",
        "cacheVariables": {
            "CMAKE_BUILD_TYPE": build_type,
            "SENSOR_HUB_CONFIG": config_name,
        },
    }
    new_build = {"name": preset_name, "configurePreset": preset_name}

    cfg = [p for p in data["configurePresets"] if p["name"] != preset_name]
    bld = [p for p in data.get("buildPresets", []) if p["name"] != preset_name]
    data["configurePresets"] = cfg + [new_configure]
    data["buildPresets"] = bld + [new_build]

    presets_file.write_text(json.dumps(data, indent=4) + "\n")


def cmake_build(source_dir: Path, build_dir: Path, config_name: str, build_type: str) -> None:
    subprocess.run(
        [
            "cmake", "-S", str(source_dir), "-B", str(build_dir),
            "-G", "Ninja",
            f"-DCMAKE_TOOLCHAIN_FILE={source_dir / 'cmake/gcc-arm-none-eabi.cmake'}",
            f"-DCMAKE_BUILD_TYPE={build_type}",
            f"-DSENSOR_HUB_CONFIG={config_name}",
        ],
        check=True,
    )
    subprocess.run(["cmake", "--build", str(build_dir)], check=True)
