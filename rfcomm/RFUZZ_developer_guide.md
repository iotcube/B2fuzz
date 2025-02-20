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
![image](https://github.com/user-attachments/assets/ac05a563-e36b-4d94-8920-5dc1f0869df5)

 In the `construct_sm()` function, the module conducts conformance testing for the RFCOMM test suite. The function constructs a state machine that aligns with the RFCOMM test suite scenario, referring to this state machine as the **base SM**.
 
 After creating the base SM, the module expands it by sending all possible RFCOMM frames and commands while visiting each base state. During this expansion process, **the state anomaly detection logic** is also executed. 
 
 This logic confirms whether the base state can be revisited normally after testing an RFCOMM frame, thereby detecting any abnormalities. Through this approach, it becomes possible to preemptively identify potential crashes that could result from previously transmitted frames.


---

### mutation_new.py
 This module perform stateful fuzzing. In this module, **the state anomaly detection** also executed.

---

### layer.rfcomm.types
 This module defines RFCOMM frames, commands and frame generator with AFL mutator.

--- 
