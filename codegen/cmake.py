from __future__ import annotations

import subprocess
from pathlib import Path


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
