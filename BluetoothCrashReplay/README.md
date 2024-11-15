---

# Bluetooth Crash Packet Replayer

This repository is Bluetooth Crash Packet Replayer, designed to replay Bluetooth packets from log files, specifically targeting RFCOMM and L2CAP layers. It was developed using Python 3 and `pybluez`. This tool can be used to load and replay Bluetooth packet log files, which is helpful in testing and debugging Bluetooth implementations.

## Features

- Supports replaying Bluetooth packet logs targeting RFCOMM and L2CAP layers.
- Provides a command-line interface to load a log file and initiate the replay sequence.
- Compatible with Python 3.

## Prerequisites

- **Python 3**
- **pybluez**: To install, run:
  ```bash
  pip install pybluez
  ```
- **scapy**: To install, run:
  ```bash
  pip install scapy
  ```

## Usage

To use the Bluetooth Crash Packet Replayer, run the `main.py` script with the following command-line options:

```bash
python3 main.py --path <logfile_path>
```

### Command-Line Options

- `-h, --help`: Displays the help message and exits.
- `--path PATH`: Specifies the path to the Bluetooth packet log file for replay.

### Example

```bash
python3 main.py --path /path/to/your/logfile.log
```

This command replays the Bluetooth packets recorded in `logfile.log`.

### Others
- Contacts: Computer & Communication Security Lab (https://ccs.korea.ac.kr)
