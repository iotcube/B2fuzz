# RFUZZ 
---
 RFUZZ is Bluetooth RFCOMM layer fuzzer. It conduct stateful fuzzing with expanded crash monitoring.

# Developer Guide

## Source for Core logic

```
rfcomm ------+----main.py
             |
             |
             |
             +-modules--+-------construct_sm.py
             |          |
             |          +-------mutation_new.py
             |          |
             |          +-------pairing.py
             |
             |          
             +layer--rfcomm--types--+
                                    |
                                    +--data.py
                                    |
                                    +--disc.py
                                    |
                                    +--dm.py
                                    |
                                    +--sabm.py
                                    |
                                    +--ua.py
                                    |
                                    +--uih.py
                                    |
                                    +--const.py
                                    |
                                    +--mx--+--fcoff.py
                                           |
                                           +--fcon.py
                                           |
                                           +--invalid.py
                                           |
                                           +--msc.py
                                           |
                                           +--nsc.py
                                           |
                                           +--pn.py
                                           |
                                           +--rls.py
                                           |
                                           +--rpn.py
                                           |
                                           +--test.py
```
---

## Discription of modules

### main.py
 This module is fuzzer's main logic.

---

### construct_sm.py
 This module constructs base state machine and adaptive state machine

---

### mutation_new.py
 This module perform stateful fuzzing.

---

### layer.rfcomm.types
 This module defines RFCOMM frames, commands and frame generator with AFL mutator.

--- 