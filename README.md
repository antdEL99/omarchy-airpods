# AirPods Pro 3 for the Omarchy bar

A small [Omarchy](https://omarchy.org) bar widget for AirPods Pro 3 on Linux: battery of each earbud and the case, and the listening mode (noise cancellation, transparency, adaptive, off), switchable from the panel.

*Widget per la barra di Omarchy: batteria e modalità di ascolto delle AirPods Pro 3. Interfaccia in italiano e inglese.*

## How it works

- `airpodsd.py` is a user service written with the Python standard library only. It finds the connected AirPods with `bluetoothctl`, opens Apple's accessory protocol channel (L2CAP, PSM 0x1001), and writes the state to `$XDG_RUNTIME_DIR/airpods/status.json`. Mode changes arrive on a Unix socket in the same private folder.
- `Panel.qml` is the bar widget. It reads the state file and calls `airpodsd.py set <mode>`.
- No pairing keys are read or stored, nothing listens on the network, and the systemd unit allows only Unix and Bluetooth sockets with a read-only home (`systemd-analyze security`: 1.3).

## Install

Requirements: Omarchy, BlueZ, Python 3.12 or newer, AirPods already paired.

```bash
git clone https://github.com/antdEL99/omarchy-airpods.git
cd omarchy-airpods
./install
omarchy bar put antdel.airpods
```

`install` copies the plugin to `~/.config/omarchy/plugins/antdel.airpods/` and the service to `~/.config/systemd/user/antdel-airpods.service`, then enables it. Run it again after an update.

Tests: `python3 -m unittest`.

## Notes

- Tested with AirPods Pro 3 (A3063). Other AirPods that speak the same protocol may partly work.
- "Off" works only after the earbuds' "allow off" setting is enabled; the service sends that setting before switching to Off.
- Protocol values come from the [LibrePods](https://github.com/librepods-org/librepods) documentation (`docs/`). No LibrePods code is included.
- Icon: [MingCute](https://github.com/mingcute-design/mingcute-icons) `airpods-fill`, Apache-2.0 (see `LICENSE-MingCute-Apache-2.0`).

## License

GPL-3.0-or-later. AirPods is a trademark of Apple Inc.; this project is not affiliated with Apple.
