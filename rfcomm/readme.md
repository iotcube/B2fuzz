# Baseline FSM Diagram

Below is the baseline FSM diagram for RFCOMM state machine coverage.
![Baseline RFCOMM FSM](fsm-diagram.png)

# RFCOMM FSM Test Matrix & Test Suite Mapping
## 1. Methodology and Rationale

This matrix and mapping are constructed by extracting valid state and event sequences for each Test Suite (TS) from the official Bluetooth RFCOMM Test Specification (RFCOMM.TS.p7).  
For each TS, valid transitions, frame directions, and roles (IUT/LT) are mapped onto the project’s canonical FSM phases:  
**Session Setup phase**, **Control Management phase**, and **Multiplexed DLC phase**.

Only test suites that are "testable" (i.e., can be triggered by the IUT/Tester or are symmetric/bi-directional) are mapped for automation.  
LT-initiated error/termination cases (e.g., LT→IUT: DISC/DM) are annotated as not testable, but are flagged as important for future error handler monitoring.

Each testable TS is mapped directly to an implementation function in `testsuite.py`.  
This mapping ensures FSM coverage, traceability, and automated test reporting.

---

## 2. FSM Test Matrix (FSM Phase Only, Latest)

| TS ID   | Purpose                  | FSM Phase(s)                                       | Function Name    | Testable | Note                    |
|---------|--------------------------|----------------------------------------------------|------------------|----------|-------------------------|
| BV-01-C | RFCOMM Init (IUT)        | Session Setup → Control Mgmt                       | tc_BV_01_C       | O        | DEVA scenario           |
| BV-02-C | RFCOMM Init (LT)         | Session Setup → Control Mgmt                       | tc_BV_02_C       | X        | LT→IUT only             |
| BV-03-C | Shutdown by LT           | Multiplexed DLC → Control Mgmt → Session Setup     | tc_BV_03_C       | X        | LT DISC; error evt      |
| BV-04-C | Shutdown by IUT          | Multiplexed DLC → Control Mgmt → Session Setup     | tc_BV_04_C       | O        | DEVA scenario           |
| BV-05-C | Open DLC (IUT)           | Control Mgmt → Multiplexed DLC                     | tc_BV_05_C       | O        | DEVA scenario           |
| BV-06-C | Open DLC (LT)            | Control Mgmt → Multiplexed DLC                     | tc_BV_06_C       | X        | LT→IUT only             |
| BV-07-C | Close DLC (IUT)          | Multiplexed DLC → Control Mgmt                     | tc_BV_07_C       | O        | DEVA scenario           |
| BV-08-C | Close DLC (LT)           | Multiplexed DLC → Control Mgmt                     | tc_BV_08_C       | X        | LT DISC; error evt      |
| BV-11-C | TEST command (bi-dir)    | Control Mgmt                                       | tc_BV_11_C       | O        | Both directions         |
| BV-13-C | RLS (bi-dir)             | Multiplexed DLC                                    | tc_BV_13_C       | O        | Both directions         |
| BV-14-C | RLS by IUT               | Multiplexed DLC                                    | tc_BV_14_C       | O        | Both directions         |
| BV-15-C | PN negotiation           | Control Mgmt                                       | tc_BV_15_C       | O        | Both directions         |
| BV-17-C | RPN negotiation          | Multiplexed DLC                                    | tc_BV_17_C       | O        | Both directions         |
| BV-19-C | RPN by IUT               | Multiplexed DLC                                    | tc_BV_19_C       | O        | Both directions         |
| BV-21-C | Credit-based flow ctrl   | Multiplexed DLC                                    | tc_BV_21_C       | O        | Credit, data UIH        |
| BV-22-C | Data transfer (credit)   | Multiplexed DLC                                    | tc_BV_22_C       | O        | Credit, UIH data        |
| BV-25-C | Unsupported cmd (bi-dir) | Control Mgmt                                       | tc_BV_25_C       | O        | Both directions         |

---
## 3. Test Suite ↔ Function Mapping (FSM State/Event Sequence)
<details>
<summary><b>BV-01-C — tc_BV_01_C</b></summary>

- **Session_Open**  
  - *(Send SABM)→*
- **Wait_UA (Setup)**  
  - *(Recv UA)→*
- **Control_Open (DLCI=0)**

</details>

<details>
<summary><b>BV-04-C — tc_BV_04_C</b></summary>

- **DLC_Open (DLCI≠0)**
  - *(Send DISC)→*
- **Wait_DISC_UA (DLC)**
  - *(Recv UA)→*
- **Control_Open (DLCI=0)**
  - *(Send DISC)→*
- **Wait_DISC_UA (Ctrl)**
  - *(Recv UA)→*
- **Session_Open**

</details>

<details>
<summary><b>BV-05-C — tc_BV_05_C</b></summary>

- **Control_Open (DLCI=0)**  
  - *(Send PN)→*
- **Wait_PN**  
  - *(Recv PN)→*
- **Control_Open (DLCI=0)**  
  - *(Send SABM)→*
- **Wait_UA (Ctrl)**  
  - *(Recv UA)→*
- **DLC_Open (DLCI≠0)**

</details>

<details>
<summary><b>BV-07-C — tc_BV_07_C</b></summary>

- **DLC_Open (DLCI≠0)**  
  - *(Send DISC)→*
- **Wait_DISC_UA (DLC)**  
  - *(Recv UA)→*
- **Control_Open (DLCI=0)**

</details>

<details>
<summary><b>BV-11-C — tc_BV_11_C</b></summary>

- **Control_Open (DLCI=0)**  
  - *(Send TEST)→*
- **Wait_Test**  
  - *(Recv TEST)→*
- **Control_Open (DLCI=0)**

</details>

<details>
<summary><b>BV-13-C — tc_BV_13_C</b></summary>

- **DLC_Open (DLCI≠0)**  
  - *(Send RLS)→*
- **Wait_RLS**  
  - *(Recv RLS)→*
- **DLC_Open (DLCI≠0)**

</details>

<details>
<summary><b>BV-14-C — tc_BV_14_C</b></summary>

- **DLC_Open (DLCI≠0)**  
  - *(Send RLS)→*
- **Wait_RLS**  
  - *(Recv RLS)→*
- **DLC_Open (DLCI≠0)**

</details>

<details>
<summary><b>BV-15-C — tc_BV_15_C</b></summary>

- **Control_Open (DLCI=0)**  
  - *(Send PN)→*
- **Wait_PN**  
  - *(Recv PN)→*
- **Control_Open (DLCI=0)**

</details>

<details>
<summary><b>BV-17-C — tc_BV_17_C</b></summary>

- **DLC_Open (DLCI≠0)**  
  - *(Send RPN)→*
- **Wait_RPN**  
  - *(Recv RPN or NSC)→*
- **DLC_Open (DLCI≠0)**

</details>

<details>
<summary><b>BV-19-C — tc_BV_19_C</b></summary>

- **DLC_Open (DLCI≠0)**  
  - *(Send RPN)→*
- **Wait_RPN**  
  - *(Recv RPN or NSC)→*
- **DLC_Open (DLCI≠0)**

</details>

<details>
<summary><b>BV-21-C — tc_BV_21_C</b></summary>

- **DLC_Open (DLCI≠0)**  
  - *(Send MSC)→*
- **Wait_MSC**  
  - *(Recv MSC)→*
- **DLC_Open (DLCI≠0)**  
  - *(Recv UIH(credits))→*
- **Credit_Rcvd**  
  - *(Send UIH(data))→*
- **DLC_Open (DLCI≠0)**

</details>

<details>
<summary><b>BV-22-C — tc_BV_22_C</b></summary>

- **DLC_Open (DLCI≠0)**  
  - *(Send MSC)→*
- **Wait_MSC**  
  - *(Recv MSC)→*
- **DLC_Open (DLCI≠0)**  
  - *(Send UIH(data))→*
- **DLC_Open (DLCI≠0)**

</details>

<details>
<summary><b>BV-25-C — tc_BV_25_C</b></summary>

- **Control_Open (DLCI=0)**  
  - *(Send Unsupported Cmd)→*
- **Wait_NSC**  
  - *(Recv NSC)→*
- **Control_Open (DLCI=0)**

</details>

---

*Phases: Session Setup, Control Mgmt, Multiplexed DLC.  
States follow your diagram’s 10-state naming (“Wait_UA (Setup)”, “Wait_DISC_UA (Ctrl)”, etc).*

