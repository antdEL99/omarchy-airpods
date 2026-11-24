# AirPods Pro 3 per la barra di Omarchy — progetto

Riscrittura da zero del 24 novembre 2026. Obiettivo: il più semplice e solido possibile.

- `airpodsd.py`: servizio utente, solo libreria standard di Python. Trova le AirPods collegate con
  `bluetoothctl`, apre il canale AAP (L2CAP, PSM 0x1001), legge batteria e modalità di ascolto, scrive
  `$XDG_RUNTIME_DIR/airpods/status.json` e riceve i cambi di modalità su un socket Unix nella stessa cartella (0700).
  Nessuna chiave letta o salvata, nessuna porta di rete, nessun privilegio.
- `protocol.py`: funzioni pure del protocollo AAP (pacchetti), con test.
- `Panel.qml` + `manifest.json` + `i18n/`: widget della barra; legge lo stato dal file, invia i comandi con
  `airpodsd.py set <modalità>`.
- `airpods.service`: unità systemd utente con restrizioni.
- `install`: collega plugin e servizio nella home.

Protocollo: documentazione di LibrePods (`docs/AAP Definitions.md`, GPL-3.0), letta il 24 novembre 2026.
Sono usati solo i valori dei pacchetti, non il codice.
