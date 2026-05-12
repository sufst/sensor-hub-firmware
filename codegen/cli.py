from pathlib import Path
import subprocess

import click

from codegen.cmake import cmake_build, update_presets
from codegen.loader import load_config
from codegen.packing import build_messages
from codegen.rendering import render_outputs


def _run_generate(input_yaml: Path, output_dir: Path | None) -> Path:
    if output_dir is None:
        output_dir = Path("Generated") / input_yaml.stem

    click.echo(f"Parsing {input_yaml} ...")
    config = load_config(input_yaml)
    click.echo(f"  ECU     : {config.ecu_name}")
    click.echo(f"  Analog  : {len(config.enabled_analog)} enabled channel(s)")
    click.echo(f"  Digital : {len(config.enabled_digital)} enabled channel(s)")

    messages = build_messages(config)
    header, source, dbc = render_outputs(config, messages)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sensor_hub.h").write_text(header)
    (output_dir / "sensor_hub.c").write_text(source)
    (output_dir / f"{config.ecu_name}.dbc").write_text(dbc)

    for m in messages:
        click.echo(f"  {m.name:<42} ID={m.can_id_hex}  DLC={m.dlc}")

    click.echo(f"\nWritten to {output_dir}/")
    click.echo(f"Import {output_dir}/{config.ecu_name}.dbc into your CAN database.")
    return output_dir


def _run_build(input_yaml: Path, build_type: str) -> None:
    click.echo(f"\n{'=' * 60}")
    click.echo(f"Config: {input_yaml.stem}  [{build_type}]")
    click.echo(f"{'=' * 60}")

    _run_generate(input_yaml, None)

    source_dir = Path.cwd()
    update_presets(source_dir, input_yaml.stem, build_type)
    build_dir = source_dir / "build" / f"{input_yaml.stem}_{build_type.lower()}"
    click.echo(f"\nBuilding → {build_dir} ...")
    cmake_build(source_dir, build_dir, input_yaml.stem, build_type)
    click.echo("  Build complete.")


@click.command()
@click.argument("input_yaml", type=click.Path(exists=True, path_type=Path), default="Configs/default.yaml")
@click.option("--output-dir", "-o", type=click.Path(path_type=Path), default=None,
              help="Output directory [default: Generated/<yaml_stem>]")
def generate_cmd(input_yaml: Path, output_dir: Path | None) -> None:
    """Generate DBC definitions and STM32 HAL C source from INPUT_YAML."""
    _run_generate(input_yaml, output_dir)


@click.command()
@click.argument("input_yaml", type=click.Path(exists=True, path_type=Path))
@click.option("--build-type", type=click.Choice(["Debug", "Release"]), default="Release", show_default=True)
def build_cmd(input_yaml: Path, build_type: str) -> None:
    """Generate and build firmware for INPUT_YAML."""
    _run_build(input_yaml, build_type)


@click.command()
@click.option("--build-type", type=click.Choice(["Debug", "Release"]), default="Release", show_default=True)
def build_all_cmd(build_type: str) -> None:
    """Generate and build firmware for every YAML in Configs/."""
    yamls = sorted(Path("Configs").glob("*.yaml"))
    if not yamls:
        raise click.ClickException("No YAML files found in Configs/")
    for yaml_path in yamls:
        _run_build(yaml_path, build_type)


@click.command()
@click.argument("input_yaml", type=click.Path(exists=True, path_type=Path))
@click.option("--build-type", type=click.Choice(["Debug", "Release"]), default="Release", show_default=True)
@click.option("--interface", default="stlink", show_default=True, help="OpenOCD interface config name (no .cfg)")
def flash_cmd(input_yaml: Path, build_type: str, interface: str) -> None:
    """Flash firmware for INPUT_YAML to a connected target via OpenOCD."""
    elf = Path("build") / f"{input_yaml.stem}_{build_type.lower()}" / f"sensor-hub-{input_yaml.stem}.elf"
    if not elf.exists():
        raise click.ClickException(f"ELF not found at {elf} — run 'build' first")
    cmd = [
        "openocd",
        "-f", f"interface/{interface}.cfg",
        "-f", "target/stm32f1x.cfg",
        "-c", f"program {elf} verify reset exit",
    ]
    click.echo(f"Flashing {elf} ...")
    if subprocess.run(cmd).returncode != 0:
        raise click.ClickException("OpenOCD exited with errors")
    click.echo("Flash complete.")
