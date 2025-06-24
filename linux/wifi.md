<https://habr.com/ru/companies/yadro/articles/921236/>

## 📡 Wireless KPI Metrics and Events

Wireless networks (e.g., cellular, Wi-Fi) are monitored using **Key Performance Indicators (KPIs)** and **event logs** to assess and optimize performance. These metrics span **radio access**, **core network**, and **user experience** layers.

---

## 📊 Common Wireless KPI Metrics

### 📶 Radio Access Network (RAN)
| KPI                     | Description |
|-------------------------|-------------|
| **RSRP**                | Reference Signal Received Power (signal strength) |
| **RSRQ**                | Reference Signal Received Quality |
| **SINR**                | Signal-to-Interference-plus-Noise Ratio |
| **CQI**                 | Channel Quality Indicator |
| **RSSI**                | Received Signal Strength Indicator |

### 📡 Connectivity & Mobility
| KPI                     | Description |
|-------------------------|-------------|
| **Call Setup Success Rate (CSSR)** | % of successful call setup attempts |
| **Handover Success Rate**          | % of successful handovers between cells |
| **Drop Call Rate (DCR)**           | % of calls dropped after being connected |
| **TA (Timing Advance)**            | Indicates UE distance from base station |

### 🌐 Data Throughput
| KPI                     | Description |
|-------------------------|-------------|
| **DL/UL Throughput**    | Download/Upload speed per user or cell |
| **PRB Utilization**     | % of Physical Resource Blocks used |
| **Latency (RTT)**       | Round-trip time between user and core |

### 📱 User Experience
| KPI                     | Description |
|-------------------------|-------------|
| **Packet Loss Rate**    | % of lost packets during transmission |
| **Jitter**              | Variability in packet arrival time |
| **Streaming QoE score** | Derived from buffering, resolution, interruptions |

---

## ⚙️ Common Wireless Events

| Event Type              | Examples |
|-------------------------|----------|
| **Connection Events**   | Call Setup, Call Drop, Attach, Detach, Authentication |
| **Mobility Events**     | Handover, Cell Reselection, Location Update |
| **Radio Link Events**   | RLF (Radio Link Failure), RRC Connection Setup/Release |
| **QoS Events**          | QoS Bearer Establishment, Degradation |
| **Paging Events**       | UE page request and response |
| **Measurement Reports** | UE reports RSRP, SINR, etc. to the network |
| **Interference Events** | Detected co-channel or adjacent interference |

---

## 🛠 Sources of Metrics and Events

- **Base stations / eNodeB / gNodeB** logs
- **User Equipment (UE) logs** (via test phones or network probes)
- **Drive tests**
- **Core network nodes (MME, AMF, SMF, etc.)**
- **OSS systems (e.g., Ericsson OSS, Huawei U2020)**

---

## 📈 Usage of Wireless KPIs

- **Network optimization**
- **Coverage planning**
- **Root cause analysis of issues**
- **Quality of Experience (QoE) scoring**
- **Automated anomaly detection using ML**

## 📶 Breakdown of Wireless KPIs: 4G (LTE) vs 5G (NR)

Wireless networks evolve from **4G LTE** to **5G NR (New Radio)**, and while many KPI concepts are shared, 5G introduces new layers, interfaces, and service types (e.g., URLLC, mMTC, eMBB).

---

## 📊 1. Radio Quality & Signal Metrics

| KPI          | 4G LTE                            | 5G NR                             |
|--------------|-----------------------------------|-----------------------------------|
| **RSRP**     | Yes (primary signal strength)     | Yes (per SS/PBCH beam)            |
| **RSRQ**     | Yes                               | Yes                               |
| **SINR**     | Yes                               | Yes                               |
| **CQI**      | Yes (0–15 range)                  | Yes (higher resolution)           |
| **RSSI**     | Yes                               | Less commonly used in 5G          |
| **SS-RSRP**  | No                                | Yes (Sync Signal Block RSRP)      |
| **SS-RSRQ**  | No                                | Yes                               |
| **SS-SINR**  | No                                | Yes                               |

---

## 🚦 2. Connectivity & Mobility

| KPI / Event               | 4G LTE                               | 5G NR                                |
|---------------------------|--------------------------------------|--------------------------------------|
| **Call Setup Success Rate** | VoLTE, CSFB setup                   | Voice over NR (VoNR), IMS setup      |
| **Handover Success Rate**   | X2 handover, intra-eNodeB          | Xn interface, intra/inter-gNodeB     |
| **RRC Connection Setup**    | RRC setup over S1                   | RRC setup via NG-RAN                 |
| **Radio Link Failure (RLF)**| Tracked per eNodeB                  | Includes Beam Failure Recovery       |
| **TA (Timing Advance)**     | Based on signal timing              | Optional, less used in dense 5G      |

---

## 🌐 3. Throughput & Resource Utilization

| KPI                    | 4G LTE                            | 5G NR                               |
|------------------------|-----------------------------------|-------------------------------------|
| **DL/UL Throughput**   | Per UE, per cell                  | Per UE, per beam, per slice         |
| **PRB Utilization**    | Physical Resource Blocks          | RB usage per BWP (Bandwidth Part)   |
| **MCS Index**          | Indicates modulation efficiency   | Same, with higher-order MCS values  |
| **Latency**            | ~30–50 ms for VoLTE               | <10 ms for eMBB, <1 ms for URLLC    |

---

## 🎯 4. User Experience & QoS

| KPI / Event                | 4G LTE                                  | 5G NR                                      |
|----------------------------|-----------------------------------------|-------------------------------------------|
| **QoS Bearer Setup**       | EPS Bearer via QCI                      | QoS Flow via 5QI (QoS Identifier)         |
| **Packet Loss / Jitt**

