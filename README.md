# Generic STM32 Sensor Hub Firmware ([STM32F105RBT](https://www.youtube.com/watch?v=dQw4w9WgXcQ))

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

## Debugging on Linux/WSL with gdb
If you don't want to use STM32CubeIDE, you can use `gdb` directly which can be very useful e.g.
```bash
# 1. build with debug symbols
uv run build-all --build-type Debug

# 2. run this in a seperate terminal window and leave it running
# you may need to `sudo apt install openocd`
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg

# 3. debug
# you may need to `sudo apt install gdb-multiarch`
gdb-multiarch -tui build/pedalbox_debug/sensor-hub-pedalbox.elf # target the desired .elf
(gdb) target remote :3333 # connect to openocd session
(gdb) load # flash latest elf to chip
(gdb) monitor reset halt # reset the chip
(gdb) break main # set a breakpoint to line 1 of main()
(gdb) continue # run until a breakpoint hits
(gdb) break main.c:125 # set a breakpoint to line 125 of main.c
(gdb) info break # list breakpoints
(gdb) del 2 # or `d` - delete breakpoint 2 from list
(gdb) continue # or `c`
(gdb) step # or `s` - step into function
(gdb) next # or `n` - run until next line hits at current scope
(gdb) finish # step up
(gdb) set s_tick = 1 # set value
(gdb) print s_tick # read value (`p/x` for hex)
(gdb) display s_tick # print value every time breakpoint hits
```

If you're on WSL, you can use [usbipd](https://github.com/dorssel/usbipd-win) to bind the ST-Link to Linux, e.g. on windows you might run:
```powershell
usbipd list
usbipd bind --busid 2-6 # value from list
usbipd attach --wsl --busid 2-6
```

Then in linux you can use `openocd` as described above:
```sh
openocd -f interface/stlink.cfg -f target/stm32f1x.cfg
```

If you have `openocd` installed, you can also use the flash script, e.g.:
```bash
uv run flash Configs/pedalbox.csv # release build
uv run flash Configs/pedalbox.csv --build-type Debug # debug build (not sure why you'd want this, probably use gdb `load` directly after building instead)
```
