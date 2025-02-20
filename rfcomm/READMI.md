# RFUZZ 
---
 RFUZZ is Bluetooth RFCOMM layer fuzzer. It conduct stateful fuzzing with expanded crash monitoring.

# Developer Guid

```
rfcomm ------+----main.py
             |
             |
             |
             +-modules--+-------construct_sm.py
             |          |
             |          +-------mutation_new.py
             |          |
             |          |
             |          +-------pairing.py
             +layer-rfcomm
             

```