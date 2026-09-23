# Setup

How to get from a fresh clone and an unboxed Arduino UNO Q to a running app. These steps were tested on macOS with a UNO Q running Debian 13, App Lab `arduino-app-cli` 0.13.0, and `arduino:zephyr` 1.0.0.

Everything is named `open-fp`: the board hostname, the App Lab app, and the repo. The Python package is `open_fp`, because Python names can't contain hyphens.

## 1. Dev machine (once)

You need Homebrew (https://brew.sh), Python 3.11+, and an SSH key (see step 3).

```bash
git clone <repo-url> open-fp && cd open-fp
tools/dev_setup.sh
```

`dev_setup.sh` does the following, and is safe to re-run:
- installs `git-lfs` and `arduino-cli` with Homebrew
- runs `git lfs pull` to download the STL/STEP files
- installs the UNO Q core (`arduino:zephyr`)
- creates `.venv` with the simulator and test dependencies

## 2. Board first boot (once per board)

1. Install **Arduino App Lab** (https://www.arduino.cc/en/software) on the dev machine.
2. Connect the UNO Q to the dev machine with a **data-capable** USB-C cable. Plug straight into the computer or a powered hub. Underpowered ports can make the board reboot.
3. Follow App Lab's first-time setup:
   - board name: **`open-fp`**
   - your Wi-Fi network
   - a password for the user `arduino`
   - accept all system and software updates
4. Check that it worked. `ping open-fp.local` should reply, and `arduino-cli board list` should show "Arduino UNO Q" with FQBN `arduino:zephyr:unoq` on both a `/dev/cu.usbmodem*` port and a network port.

## 3. SSH access (once per dev machine per board)

```bash
tools/board_setup.sh              # optional host argument, default open-fp.local
```

This installs `~/.ssh/id_ed25519.pub` on the board, which asks for the `arduino` password once. It then prints the OS version, the `arduino-app-cli` help, and the router service status.

- To use a different key, run `PUBKEY=~/.ssh/other.pub tools/board_setup.sh`.
- **The private key doesn't have to be on disk.** It works with the 1Password SSH agent or any other agent. The script avoids `ssh-copy-id`, which fails when the private key file is missing.
- If you have no key, create one with `ssh-keygen -t ed25519`.

Check that `ssh arduino@open-fp.local` logs in without asking for a password.

## 4. Create the App Lab app (once per board)

The deploy script restarts the app by its folder path on the board, so the app must exist there first. In App Lab, create a new app named **`open-fp`** and add the **WebUI - HTML** brick. App Lab creates it at `/home/arduino/ArduinoApps/open-fp`.

The repo already contains the generated `app/app.yaml` and `app/sketch/sketch.yaml`. The first deploy overwrites App Lab's files with the repo's. Don't hand-edit these two files. If you change bricks or libraries, make the change in App Lab and copy the files back:

```bash
ssh arduino@open-fp.local 'cd ~/ArduinoApps/open-fp && tar cf - app.yaml sketch/sketch.yaml' | tar xf - -C app/
```

## 5. Deploy and run

```bash
tools/deploy.sh                   # copy app/ to the board and restart the app
tools/logs.sh                     # follow the Python logs (Ctrl-C to stop)
```

The UI is at `http://open-fp.local:7000`.

- The deploy copies with tar over SSH because the board has no `rsync`. It replaces everything in the app folder except `data/`, which holds calibration and swings, and `.cache/`, where App Lab keeps the Python venv.
- The first start builds and flashes the MCU sketch and may pull containers, so the board needs internet access.
- To open the MCU serial monitor, run `ssh -t arduino@open-fp.local arduino-app-cli monitor`.

## 6. Start the app at boot (optional)

```bash
ssh arduino@open-fp.local arduino-app-cli properties set default /home/arduino/ArduinoApps/open-fp
# undo: ... properties set default none
```

Not tested yet: whether the "default" app starts at boot is still to be confirmed (M8). App Lab also has a GUI option for this.

## 7. Bench sketches (MCU only, no Linux side)

```bash
arduino-cli compile --fqbn arduino:zephyr:unoq bench/ads1220_single
arduino-cli upload  --fqbn arduino:zephyr:unoq -p /dev/cu.usbmodem<…> bench/ads1220_single
```

Find the port with `arduino-cli board list`.

## 8. Development without hardware

```bash
. .venv/bin/activate
python tools/sim/sim_server.py    # (M5) http://localhost:7000
pytest
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ssh-copy-id: failed to open ID file` | The private key is in an agent. Use `tools/board_setup.sh`, which doesn't need the file. |
| `rsync: command not found` on the board | Use `tools/deploy.sh`, which copies with tar. |
| `open-fp.local` doesn't resolve | The board is off Wi-Fi or on a different network. Use `arduino-cli board list` to see its IP, or `adb shell` over USB. |
| App shows "running" but port 7000 doesn't answer | `main.py` must create `WebUI()`. Check `tools/logs.sh`. |
