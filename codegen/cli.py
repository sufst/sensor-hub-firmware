from __future__ import annotations

from pathlib import Path

import click

from codegen.cmake import cmake_build
from codegen.messages import build_i2c_groups, build_message_groups, validate_with_cantools
from codegen.models import parse_csv
from codegen.rendering import render_outputs


def _run_generate(input_csv: Path, output_dir: Path | None) -> Path:
    """Core generate logic shared by generate and build commands. Returns the output directory."""
    if output_dir is None:
        output_dir = Path("Generated") / input_csv.stem

    click.echo(f"Parsing {input_csv} ...")
    config = parse_csv(input_csv)
    click.echo(f"  ECU     : {config.ecu_name}")
    click.echo(f"  Analog  : {len(config.enabled_analog)} enabled channel(s)")
    click.echo(f"  Digital : {len(config.enabled_digital)} enabled channel(s)")

    analog_groups, digital_groups = build_message_groups(
        config, config.analog_base_id, config.digital_base_id
    )
    i2c_groups = build_i2c_groups(config)

    click.echo("Validating signal packing with cantools ...")
    validate_with_cantools(config, analog_groups + digital_groups + i2c_groups)
    click.echo("  OK")

    click.echo("Rendering outputs ...")
    header, source, dbc = render_outputs(
        config, analog_groups, digital_groups, i2c_groups)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sensor_hub.h").write_text(header)
    (output_dir / "sensor_hub.c").write_text(source)
    (output_dir / f"{config.ecu_name}.dbc").write_text(dbc)

    for g in analog_groups + digital_groups + i2c_groups:
        click.echo(
            f"  {g['name']:<42} ID={g['can_id_hex']}  DLC={g['dlc']}  {len(g['signals'])} signal(s)"
        )

    click.echo(f"\nWritten to {output_dir}/")
    click.echo(f"Import {output_dir}/{config.ecu_name}.dbc into your CAN database.")

    return output_dir


def _run_build(input_csv: Path, build_type: str) -> None:
    click.echo(f"\n{'='*60}")
    click.echo(f"Config: {input_csv.stem}  [{build_type}]")
    click.echo(f"{'='*60}")

    _run_generate(input_csv, None)

    source_dir = Path.cwd()
    build_dir = source_dir / "build" / f"{input_csv.stem}_{build_type.lower()}"
    click.echo(f"\nBuilding → {build_dir} ...")
    cmake_build(source_dir, build_dir, input_csv.stem, build_type)
    click.echo("  Build complete.")


@click.command()
@click.argument("input_csv", type=click.Path(exists=True, path_type=Path), default="Configs/default.csv")
@click.option("--output-dir", "-o", type=click.Path(path_type=Path), default=None,
              help="Output directory [default: Generated/<csv_stem>]")
def generate_cmd(input_csv: Path, output_dir: Path | None) -> None:
    """Generate DBC definitions and STM32 HAL C source from INPUT_CSV."""
    _run_generate(input_csv, output_dir)


@click.command()
@click.argument("input_csv", type=click.Path(exists=True, path_type=Path))
@click.option("--build-type", type=click.Choice(["Debug", "Release"]), default="Release", show_default=True)
def build_cmd(input_csv: Path, build_type: str) -> None:
    """Generate and build firmware for INPUT_CSV."""
    _run_build(input_csv, build_type)


@click.command()
@click.option("--build-type", type=click.Choice(["Debug", "Release"]), default="Release", show_default=True)
def build_all_cmd(build_type: str) -> None:
    """Generate and build firmware for every CSV in Configs/."""
    csvs = sorted(Path("Configs").glob("*.csv"))
    if not csvs:
        raise click.ClickException("No CSV files found in Configs/")
    for csv in csvs:
        _run_build(csv, build_type)
