# Generic STM32 Sensor Hub Firmware (STM32F105RBT)

## First time repository setup
1. Clone the repository
```sh
git clone https://github.com/sufst/sensor-hub-firmware
```
2. [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/) if you don't have it already
```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```
3. [Install Ninja](https://github.com/ninja-build/ninja/wiki/Pre-built-Ninja-packages) and the [GCC Arm toolchain](https://learn.arm.com/install-guides/gcc/arm-gnu/) if you don't have it already
```sh
sudo apt install ninja-build gcc-arm-none-eabi binutils-arm-none-eabi
```
4. Download python dependencies
```sh
uv sync
```
5. Check the build works
```sh
uv run build-all
```
Files should be generated in `Generated/default` and `build/default_release`.

## Configuring and flashing a board
For a new board:
1. Copy `Configs/default.csv` to `Configs/<board_name>.csv`
2. Fill it in `Configs/<board_name>.csv` (e.g. use Microsoft Excel):
    - ECU Name
    - Message ID bases (analog and digital, base because if more than 1 message is required it's incremented)
    - Which ports are enabled/disabled 
        - for the half size one, it's the first 8
        - for the full size it's all 16
        - leave ports disabled that aren't connected to anything
    - Which ports to treat as analog/digital
    - Resistor configuration (capacitor is optional for reference)
3. Run the build
```sh
uv run build Configs/<board_name>.csv
```
(or alternatively `uv run build-all` to build all boards)
4. Flash to the board
Use STM32CubeProgrammer on the generated .elf in `build/<board_name>_release/sensor-hub-<board_name>.elf`
5. Update the DBC definition in [sufst/can-defs](https://github.com/sufst/can-defs) (see below)
### Using the generated DBC
6. Import `Generated/<board_name>/<ecu_name>.dbc` into the desired can definition (e.g. [sufst/can-defs](https://github.com/sufst/can-defs))
7. Profit 🤑 (maybe test it first)

## Troubleshooting
If you get CMake errors, you might need to install the toolchain, e.g. on Ubuntu:
```sh
sudo apt install gcc-arm-none-eabi binutils-arm-none-eabi
```
And to install ninja:
```sh
sudo apt install ninja-build
```
