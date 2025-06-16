
### Publish-Subscribe vs Client-Server

| Feature                 | Publish-Subscribe Model                        | Client-Server Model                            |
|------------------------|------------------------------------------------|------------------------------------------------|
| Communication Flow     | Indirect: via a broker                         | Direct: between client and server              |
| Roles                  | Publishers, Subscribers, Broker                | Client and Server                              |
| Connection Pattern     | Many-to-many                                   | One-to-one                                     |
| Message Routing        | Broker receives and routes messages based on topic | Client sends request; server replies directly |
| Decoupling             | High (publisher and subscriber don't know each other) | Low (client must know server address)      |
| Examples               | MQTT, Kafka, Redis Pub/Sub                     | HTTP, FTP, gRPC, CoAP                          |
| Typical Use Cases      | Event streaming, IoT telemetry, notifications  | Web browsing, REST APIs, remote procedure calls|

---



#### Client-Server:
- Client sends a request.
- Server processes and sends back a response.
- Communication is synchronous or request-driven.

Example:
Client → [GET /status] → Server  
Server → [200 OK] → Client

---

#### Publish-Subscribe:
- Publisher sends a message to a topic.
- Broker delivers it to all subscribers of that topic.
- Communication is event-driven and asynchronous.

Example:
Publisher → Broker (topic: temperature, msg: 22.5°C)  
Broker → Sends to all subscribers of "temperature"

---

### Summary

- Client-Server: tightly coupled, request/response model.
- Publish-Subscribe: loosely coupled, event-driven messaging with a broker in the middle.




# How to Scrape Linux CPU and Memory Metrics into Prometheus and Visualize in Grafana

---

## 1. 🧰 Install Node Exporter (Linux Metrics Exporter)

Node Exporter is a Prometheus exporter for hardware and OS metrics exposed by *nix kernels.

### 📦 Installation (Linux)

```bash
wget https://github.com/prometheus/node_exporter/releases/download/v1.8.0/node_exporter-1.8.0.linux-amd64.tar.gz
tar xvfz node_exporter-1.8.0.linux-amd64.tar.gz
cd node_exporter-1.8.0.linux-amd64
./node_exporter
```

This starts the exporter on default port `9100`.

---

## 2. 📥 Configure Prometheus to Scrape Node Exporter

### 🛠 Edit `prometheus.yml`

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
```

> Make sure Prometheus is installed: [https://prometheus.io/download/](https://prometheus.io/download/)

### 🚀 Start Prometheus

```bash
./prometheus --config.file=prometheus.yml
```

Prometheus now scrapes metrics from Node Exporter every 15 seconds.

---

## 3. 📊 Install and Connect Grafana

### 🔧 Install Grafana (on Linux)

```bash
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt-get update
sudo apt-get install grafana
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

### 🔗 Access Grafana UI

- Open: `http://localhost:3000`
- Default credentials: `admin` / `admin`

---

## 4. ➕ Add Prometheus Data Source to Grafana

1. Go to **Grafana UI** → ⚙️ **Settings** → **Data Sources**
2. Click **"Add data source"**
3. Choose **Prometheus**
4. URL: `http://localhost:9090`
5. Click **Save & Test**

---

## 5. 📈 Import Dashboard for CPU and Memory

Grafana has community dashboards for Node Exporter.

1. Go to ➕ → **Import**
2. Use Dashboard ID: **1860** (Node Exporter Full)
3. Select Prometheus as the data source
4. Click **Import**

This gives you detailed panels for:
- CPU usage
- Memory usage
- Disk I/O
- Network usage
- And more...

---

## ✅ Summary

| Component      | Role                                       |
|----------------|--------------------------------------------|
| `node_exporter`| Exposes Linux metrics (CPU, memory, etc.) |
| `prometheus`   | Scrapes metrics from `node_exporter`       |
| `grafana`      | Visualizes metrics via dashboards          |

---

### 📚 Useful Ports

| Service         | Port  |
|------------------|--------|
| Node Exporter    | 9100   |
| Prometheus       | 9090   |
| Grafana          | 3000   |


By default, Prometheus **stores time-series data for 15 days**.



### ⚙️ How to Configure Retention

You can change the retention period using command-line flags when starting Prometheus:

```bash
./prometheus \
  --config.file=prometheus.yml \
  --storage.tsdb.retention.time=30d
```

### 🛠 Other Related Flags

| Flag                                  | Description                                      | Default   |
|---------------------------------------|--------------------------------------------------|-----------|
| `--storage.tsdb.retention.time`       | How long to retain data                         | `15d`     |
| `--storage.tsdb.retention.size`       | Max storage size before old data is deleted     | `0` (disabled) |
| `--storage.tsdb.path`                 | Directory for TSDB storage                      | `data/`   |
| `--storage.tsdb.wal-compression`      | Enable write-ahead log compression              | `false`   |

> Note: Prometheus deletes **whole blocks of data**, not individual series, so retention may appear slightly off by ±1-2h.

---

### 🧹 Manual Cleanup

To manually remove old data (not recommended unless necessary), you can:
1. Stop Prometheus
2. Delete older TSDB blocks from the `data/` directory
3. Restart Prometheus

---

### 🗃 Long-Term Retention Solution

If you need metrics for **months or years**, Prometheus alone isn't ideal.

**Solution**:
- Use **remote storage backends** like:
  - **VictoriaMetrics**
  - **Thanos**
  - **Cortex**
  - **InfluxDB**

These systems support **horizontal scaling** and **long-term data retention**.

---

### ✅ Summary

| Setting                  | Default | Description                        |
|--------------------------|---------|------------------------------------|
| Retention time           | 15d     | How long metrics are stored        |
| Changeable via flag      | ✅       | `--storage.tsdb.retention.time`    |
| Long-term storage option | ✅       | Use Thanos, VictoriaMetrics, etc.  |

## Prometheus and VictoriaMetrics

- **VictoriaMetrics is designed to be a drop-in replacement or long-term storage backend for Prometheus.**
- **They can be used together**: Prometheus scrapes metrics and pushes them to VictoriaMetrics (via remote write).
- **VictoriaMetrics supports the Prometheus query language (PromQL)** and many of its APIs.

---

### Prometheus and VictoriaMetrics Key Differences and Features

| Feature                     | Prometheus                          | VictoriaMetrics                          |
|-----------------------------|-------------------------------------|-------------------------------------------|
| **Primary Role**           | Time-series database + scraper      | Time-series database only                 |
| **Data Ingestion**         | Pull-based (scrapes targets)        | Push-based (via Prometheus remote write) |
| **Storage Duration**       | Short-term (days to weeks)          | Long-term (months to years)              |
| **Scalability**            | Limited (single-node)               | Highly scalable (single-node or cluster) |
| **Performance**            | Optimized for simplicity            | Optimized for ingestion & query speed     |
| **Use Case Together**      | Prometheus scrapes, Victoria stores | VictoriaMetrics stores & queries metrics |

---

## 🧩 Typical Setup Using Prometheus and VictoriaMetrics

1. Prometheus scrapes targets and stores recent metrics locally.
2. Prometheus uses **`remote_write`** to push metrics to **VictoriaMetrics** for long-term retention.
3. Grafana queries VictoriaMetrics using PromQL for dashboards.

---

## ✅ VictoriaMetrics Advantages Over Prometheus (for storage)

- More efficient storage and lower disk usage.
- Better performance at scale (high cardinality/time range).
- Built-in compaction and downsampling.
- Supports clustering for high availability.

---

**In summary**:  
VictoriaMetrics is **not a fork** of Prometheus but rather a **complementary time-series database** that can integrate with Prometheus to provide **better scalability, performance, and long-term storage**.




### OpenTelemetry [OTel] 


- **OpenTelemetry** (OTel) is a **vendor-neutral** framework for collecting **telemetry data**: 
  - **Metrics**
  - **Logs**
  - **Traces**

- It is a unified standard backed by the CNCF (Cloud Native Computing Foundation)   
  to **instrument applications** and **export observability data**.

---

### 🔄 OTel Integration with Prometheus and Grafana

### 📊 Metrics → Prometheus

- **OpenTelemetry SDKs and Collector** can **export metrics in Prometheus format**.
- Prometheus can **scrape metrics** exposed by OpenTelemetry-instrumented applications.
- Alternatively, **OpenTelemetry Collector** can expose a **Prometheus scrape endpoint**.

### 📈 Visualization → Grafana

- **Grafana** is a **visualization layer**.
- Grafana can:
  - Read **Prometheus metrics** (scraped from OpenTelemetry).
  - Query **traces** from backends like **Jaeger** or **Tempo** (also exported by OpenTelemetry).
  - Display **logs** if exported to systems like **Loki**.

---

### 🧩 Typical Pipeline

```
Application (instrumented with OpenTelemetry SDK)
         ↓
OpenTelemetry Collector
         ↓
Exporters:
  - Prometheus metrics → scraped by Prometheus → visualized in Grafana
  - Traces → Jaeger / Tempo → visualized in Grafana
  - Logs → Loki → visualized in Grafana
```

---

### ✅ Summary

| Component        | Role                                          |
|------------------|-----------------------------------------------|
| **OpenTelemetry** | Collects telemetry data (metrics, logs, traces) |
| **Prometheus**    | Scrapes metrics from OpenTelemetry or apps     |
| **Grafana**       | Visualizes data from Prometheus, Jaeger, Loki, etc. |

---

**In essence**:  
OpenTelemetry **generates and exports** observability data.  
Prometheus **stores metrics**, and Grafana **visualizes them all** (metrics, logs, traces).



### What is MQTT Protocol?

MQTT (Message Queuing Telemetry Transport) is a lightweight, publish-subscribe messaging protocol designed for low-bandwidth, high-latency, or unreliable networks. It's especially useful for Internet of Things (IoT) applications.

#### Key Characteristics:
- Publish/Subscribe model: Devices (clients) can publish messages to topics, and other clients can subscribe to those topics.
- Broker-based: A central broker (like Mosquitto, HiveMQ) manages message distribution.
- Lightweight: Very small overhead, making it suitable for devices with limited resources.
- QoS Levels: Supports three Quality of Service levels:
  - 0: At most once (fire and forget)
  - 1: At least once
  - 2: Exactly once
- Persistent sessions and Last Will messages support device availability monitoring.

---

### Is MQTT Used in the Automotive Industry?

Yes, extensively.

#### Automotive Use Cases:
1. Connected Cars / Telematics:
   - Real-time vehicle status reporting (e.g., tire pressure, fuel level, GPS location).
   - Remote diagnostics and over-the-air (OTA) updates.
   - MQTT helps reduce cellular data usage due to its efficiency.

2. In-Vehicle Communication (in modern ECUs or gateways):
   - MQTT is sometimes used to transmit non-safety-critical telemetry data from ECUs to cloud services.

3. Fleet Management:
   - Vehicle tracking and maintenance status reporting.

4. V2X (Vehicle-to-Everything):
   - Though not the primary protocol (DSRC and C-V2X are more common), MQTT can be used for V2Cloud or V2Infrastructure communications.

5. Smart Charging / Electric Vehicles:
   - EV charging stations may use MQTT to communicate charging status or integrate with energy grids.

---

### Summary

| Feature             | MQTT |
|---------------------|------|
| Protocol Type       | Publish-Subscribe |
| Optimized For       | Low-power, unreliable networks |
| Used In Automotive? | Yes — for telemetry, diagnostics, remote monitoring, and IoT integration |

---

### Is MQTT a combination of protocol + server?

Yes — MQTT is a messaging protocol, and to use it in practice, you also need an MQTT broker (server) that implements this protocol.

#### The MQTT stack typically includes:
1. Clients: Devices, applications, or services that publish/subscribe to topics.
2. Broker (server): A centralized component that:
   - Receives published messages
   - Delivers them to subscribed clients
   - Maintains client sessions, QoS, and retained messages

Popular MQTT brokers:
- Eclipse Mosquitto (open-source, lightweight)
- HiveMQ (commercial, scalable)
- EMQX (high-performance)
- AWS IoT Core, Azure IoT Hub, GCP IoT Core (cloud-native brokers)

---

### Can Kafka act as an MQTT broker?

Not directly. Kafka is not an MQTT broker because:
- Kafka uses a different protocol and messaging model (pull-based, partitioned logs, persistent).
- MQTT is optimized for constrained devices and networks, while Kafka is optimized for throughput and scalability in backend systems.

#### However:
You can bridge MQTT and Kafka by using:
- MQTT-Kafka connectors (e.g., using EMQX Kafka Bridge, HiveMQ Kafka Extension)
- Custom middleware that subscribes to MQTT and republishes into Kafka.

This allows you to:
- Use MQTT for edge/IoT telemetry
- Use Kafka for backend processing, analytics, and stream storage

---

### Analogy

| Layer        | MQTT                        | Kafka                      |
|--------------|-----------------------------|----------------------------|
| Protocol     | Lightweight IoT protocol    | High-throughput log system |
| Broker/Server| MQTT broker (e.g., Mosquitto)| Kafka broker               |
| Use Case     | IoT, telemetry, mobile data | Data pipeline, analytics   |

---

### Summary:
- MQTT is a protocol, and it needs an MQTT broker.
- Kafka is not an MQTT broker, but the two can be integrated for hybrid use cases (e.g., MQTT at the edge, Kafka in the backend).



### What is CoAP Protocol?

CoAP (Constrained Application Protocol) is a lightweight, web-based protocol designed for resource-constrained devices in IoT environments. It is standardized by the IETF as RFC 7252.

---

### Key Features:

| Feature                | Description                                                                 |
|------------------------|-----------------------------------------------------------------------------|
| Protocol Type          | Client-server (like HTTP)                                                   |
| Runs Over              | UDP (instead of TCP, for efficiency)                                        |
| Designed For           | Low-power devices with limited CPU, memory, and bandwidth                   |
| Message Types          | Confirmable (CON), Non-confirmable (NON), Acknowledgement (ACK), Reset (RST)|
| RESTful Semantics      | Supports GET, POST, PUT, DELETE like HTTP                                   |
| Supports Multicast     | Yes — useful for broadcasting to multiple devices                           |
| Compact Binary Format  | Smaller message size compared to HTTP                                       |
| Security               | Typically DTLS (Datagram Transport Layer Security)                          |

---

### CoAP vs MQTT:

| Feature             | CoAP                            | MQTT                            |
|---------------------|----------------------------------|----------------------------------|
| Protocol Model      | Request/Response (like HTTP)     | Publish/Subscribe                |
| Transport           | UDP                              | TCP                              |
| Message Reliability | Optional (confirmable messages)  | Built-in QoS                     |
| Use Case            | Direct device access (e.g., REST APIs on sensors) | Event streaming, telemetry     |
| Security            | DTLS                             | TLS                              |
| Multicast Support   | Yes                              | No                               |

---

### Use Cases:
- Smart home: Accessing sensors or actuators (e.g., smart bulbs, thermostats).
- Industrial IoT: Communicating with edge devices on unreliable or lossy networks.
- Remote monitoring: Sending commands or reading sensor values.

---

### Example CoAP Interaction:
Client: GET coap://sensor.local/temperature  
Server: 2.05 Content "22.4°C"

---

### Summary

- CoAP is like a mini-HTTP for IoT, optimized for low-resource devices.
- It uses UDP, supports RESTful interactions, and enables efficient communication over lossy or constrained networks.
- Common in smart homes, industrial IoT, and wireless sensor networks.




https://sre.google/sre-book/monitoring-distributed-systems/

https://habr.com/ru/articles/917658/

https://signoz.io/blog/cicd-observability-with-opentelemetry/

https://news.ycombinator.com/item?id=44247020

