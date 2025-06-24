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

Let me know if you want a breakdown of 4G vs 5G KPIs or KPI mapping to network layers.
