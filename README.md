# B2Fuzz

Discovering Bluetooth L2CAP and RFCOMM Vulnerabilities via Adaptive Stateful Fuzzing

## Prerequisites

### version info

python: 3.8.10, scapy: 2.4.4, ouilookup: 0.2.4, pybluez: 0.40

```
$ sudo apt-get install libbluetooth-dev
$ python3 -m pip install git+https://github.com/pybluez/pybluez.git#egg=pybluez
$ python3 -m pip install scapy==2.4.4
$ python3 -m pip install ouilookup==0.2.4
```

## Running the fuzzer

1. move to B2Fuzz folder.
2. run main.py with sudo.
3. Choose the layer.

```
$ sudo python3 run.py
1. l2cap
2. rfcomm
> 2
Performing classic bluetooth inquiry scan...
```

1. Choose target device.

```
Performing classic bluetooth inquiry scan...
nearby devices : 1

	Target Bluetooth Device List
	[No.]	[BT address]		[Device name]		[Device Class]		[OUI]
	00.	xx:xx:xx:xx:xx:xx	Pixel 7		Phone(Smartphone)
	Found 1 devices

Choose Device : 0 

```

1. Choose target service which is supported by L2CAP or RFCOMM layer

```
Start scanning services...

	List of profiles for the device
	00. [None]: None
	01. [None]: None
	02. [0x110D]: Advanced Audio Source
	03. [0x110E]: AV Remote Control Target
	04. [0x110E]: AV Remote Control
	05. [0x1108]: Headset Gateway
	06. [0x111E]: Handsfree Gateway
	07. [None]: None
	08. [0x1116]: Android Network Access Point
	09. [0x1115]: Android Network User
	10. [0x1134]: SMS/MMS
	11. [0x1130]: OBEX Phonebook Access Server
	12. [0x112D]: SIM Access
	13. [0x1105]: OBEX Object Push
	14. [None]: NearbySharing

Select a profile to fuzz : 10

	Protocol for the profile [SMS/MMS] : RFCOMM

===================Test Informatoin===================
{
	"tool_name": "b2fuzz",
	"interface": "Bluetooth",
	"toolVer": "1.0.0",
	"protocol": "RFCOMM",
	"bdaddr": "xx:xx:xx:xx:xx:xx",
	"service": "SMS/MMS",
	"port": 4
}

```

1. Fuzz testing start.

### End test

The fuzzer ends after transmitting 2,000,000 packets. If you want to quit before then, type `Ctrl+C`.

```
Ctrl+C
```

### Log file

The log file will be generated after fuzz testing in log/ folder.

# Crash Monitor

We provide crash monitor at **android** and **linux** for capture crash log.

## Prerequisites

### version info

python: 3.8.10, adb_shell: 0.4.4, pyshark: 0.6

```
$ python3 -m pip install adb_shell==0.4.4
$ python3 -m pip install pyshark==0.6
```

## Running the crash monitor

### android

**Rooting is required for Bluetooth HCI snoop log capture.**

1. Check “Enabled” in **Enable Bluetooth HCI snoop log** in Developer option
2. allow wireless debugging between target device and monitor device.
3. if don’t have adbkey, Connect and disconnect the target device once with adb for the monitor device.
4. run monitor.py with sudo in monitor device.

### linux

**Required root permission for capture bluetooth packet.**

1. run monitor.py with sudo in target device.

## Others

- Contacts: dlehgus1023@naver.com, pingjuu@korea.ac.kr, Computer & Communication Security Lab (https://ccs.korea.ac.kr)
- It will be uploaded on the IoTcube Platform in **November**
- B2FUZZ's research on the L2CAP layer is scheduled to be presented as BLOOMFUZZ at ESORICS 2024.