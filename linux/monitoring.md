## Monitoring
<https://habr.com/ru/articles/922310/> DevOps в локальных облаках: как строить высоконагруженные системы с CI/CD, Kubernetes и Grafana

<https://signoz.io/blog/what-is-opentelemetry/> What is opentelemetry

### Grafana Dashboards

https://medium.com/data-engineer-things/the-data-engineers-toolkit-12-free-monitoring-dashboards-you-didn-t-know-existed-c0e2fee806f4

### Monitiring Postgres with Grafana

Configure PostgreSQL
Modify the authentication method in the pg_hba.conf file to use scram-sha-256   
instead of peer for local connections. 
This will allow you to use password-based authentication to the server.
```
Local all all scram-sha-256
```
Restart the server:

```sudo systemctl restart postgresql```

Create a database user for monitoring and set a password for this user:

```CREATE USER monitoring_user WITH PASSWORD test@1234 SUPERUSER;```

Install the postgres_exporter <https://github.com/prometheus-community/postgres_exporter>
Download the latest release of the postgres_exporter binary:

```wget https://github.com/prometheus-community/postgres_exporter/releases/download/v0.14.0/postgres_exporter-0.14.0.linux-amd64.tar.gz```
Unzip the binary:

tar xzf postgres_exporter-0.14.0.linux-amd64.tar.gz

Move postgres_exporter binary to /usr/local/bin:

```sudo cp postgres_exporter /usr/local/bin```

#### Configure the postgres_exporter
Create a new directory under /opt to store connection information for the PostgreSQL server:
```
mkdir /opt/postgres_exporter
echo DATA_SOURCE_NAME="postgresql://monitoring_user:test@1234@localhost:5432/?sslmode=disable" > /opt/postgres_exporter/postgres_exporter.env
```
Create a service file for the postgres_exporter:
```ini
echo '[Unit]
Description=Postgres exporter for Prometheus
Wants=network-online.target
After=network-online.target
[Service]
User=postgres
Group=postgres
WorkingDirectory=/opt/postgres_exporter
EnvironmentFile=/opt/postgres_exporter/postgres_exporter.env
ExecStart=/usr/local/bin/postgres_exporter --web.listen-address=localhost:9100 --web.telemetry-path=/metrics
Restart=always
[Install]|
WantedBy=multi-user.target' >> /etc/systemd/system/postgres_exporter.service
```
Since we created a new service file, it is better to reload the demon once so it recognizes the new file:

```sudo systemctl daemon-reload```

Start and enable the postgres_exporter service:

```sudo systemctl start postgres_exporter sudo systemctl enable postgres_exporter```

Check the service status:
```
sudo systemctl status postgres_exporter
  postgres_exporter.service - Prometheus exporter for Postgresql
     Loaded: loaded (/etc/systemd/system/postgres_exporter.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2024-03-05 13:52:56 UTC; 2h 15min ago
   Main PID: 9438 (postgres_export)
      Tasks: 6 (limit: 9498)
```
Verify the postgres_exporter setup from the browser: 
```localhost:9100/metrics```


#### Set up the Prometheus and Grafana server
Install Prometheus
Create a system group named Prometheus:

sudo groupadd --system prometheus

Create a system user named Prometheus in a Prometheus group without an interactive login:

sudo useradd -s /sbin/nologin --system -g prometheus prometheus

Creating the required directory structure:

sudo mkdir /etc/prometheus sudo mkdir /var/lib/prometheus

Download the Prometheus source:

wget https://github.com/prometheus/prometheus/releases/download/v2.43.0/prometheus-2.43.0.linux-amd64.tar.gz

Decompress the source code:

tar vxf prometheus*.tar.gz

Set up proper permissions for the installation files:
```bash
cd prometheus*/
sudo mv prometheus /usr/local/bin
sudo mv promtool /usr/local/bin
sudo chown prometheus:prometheus /usr/local/bin/prometheus
sudo chown prometheus:prometheus /usr/local/bin/promtool
sudo mv consoles /etc/prometheus
sudo mv console_libraries /etc/prometheus
sudo mv prometheus.yml /etc/prometheus
sudo chown prometheus:prometheus /etc/prometheus
sudo chown -R prometheus:prometheus /etc/prometheus/consoles
sudo chown -R prometheus:prometheus /etc/prometheus/console_libraries
sudo chown -R prometheus:prometheus /var/lib/prometheus
```
#### Configure Prometheus
Add the PostgreSQL Exporter configurations inside the prometheus.yml file at the following location:
```
 /etc/prometheus/prometheus.yml
scrape_configs:
  - job_name: "Postgres exporter"
    scrape_interval: 5s
    static_configs:
      - targets: [localhost:9100]
```
Create a new service file for Prometheus at the following location:

/etc/systemd/system/prometheus.service
```ini
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target
[Service]
User=prometheus
Group=prometheus
Type=simple
```

```
ExecStart=/usr/local/bin/prometheus \
    --config.file /etc/prometheus/prometheus.yml \
    --storage.tsdb.path /var/lib/prometheus/ \
    --web.console.templates=/etc/prometheus/consoles \
    --web.console.libraries=/etc/prometheus/console_libraries
```

```ini
[Install]
WantedBy=multi-user.target
```

Reload systemd manager:

sudo systemctl daemon-reload

Start the Prometheus service:

sudo systemctl enable prometheus sudo systemctl start prometheus

Verify the Prometheus service:
```
sudo systemctl status prometheus
  prometheus.service - Prometheus
     Loaded: loaded (/etc/systemd/system/prometheus.service; enabled; vendor preset: enabled)
```

```
     Active: active (running) since Tue 2024-03-05 13:53:51 UTC; 2h 27min ago
   Main PID: 9470 (prometheus)
      Tasks: 8 (limit: 9498)
```

Verify the Prometheus setup from the browser: localhost:9090/graph

#### Install Grafana
Install the pre-required packages:

sudo apt install -y apt-transport-https software-properties-common

Add the Grafana GPG key:
```
sudo mkdir -p /etc/apt/keyrings/
wget -q -O - https://apt.grafana.com/gpg.key | gpg --dearmor | sudo tee /etc/apt/keyrings/grafana.gpg > /dev/null
```
Add Grafana’s APT repository:
```
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" | sudo tee -a /etc/apt/sources.list.d/grafana.list
sudo apt update
```
Install the Grafana package:

sudo apt install grafana

Start the Grafana service:

sudo systemctl start grafana-server sudo systemctl enable grafana-server

Verify the Grafana service:
```
sudo systemctl status grafana-server
● grafana-server.service - Grafana instance
    Loaded: loaded (/lib/systemd/system/grafana-server.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2024-03-12 05:45:23 UTC; 1h 29min ago
       Docs: http://docs.grafana.org
   Main PID: 719 (grafana)
```
Verify your Grafana setup from the browser: localhost:3000


#### Integrate Prometheus server with Grafana
Add new data source for Prometheus: localhost:3000/connections/datasources

Create a new dashboard
Find a PostgreSQL Grafana dashboard online and copy the URL of the dashboard that suits your preferences. 
<localhost:3000/dashboard/import>
Paste the URL and select Load.

<https://medium.com/timescale/how-to-monitor-postgresql-like-a-pro-5-techniques-every-developer-should-know-68581c49a4a4>

### Grafana Automation
<https://github.com/grafana/grafanactl>  
<https://grafana.github.io/grafana-foundation-sdk/>

#### Grafonnet
<https://grafana.github.io/grafonnet/>  
<https://www.youtube.com/watch?v=u6git2AjoEo>  
<https://jsonnet.movatech.today/blog/fully-reproducible-grafana-dashboards-with-grafonnet/>  

#### Alloy
<https://github.com/grafana/alloy>  <https://grafana.com/docs/alloy/latest/>

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




## How to Scrape Linux CPU and Memory Metrics into Prometheus and Visualize in Grafana


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

## 4.  Add Prometheus Data Source to Grafana

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
  - **VictoriaMetrics**  <https://habr.com/ru/companies/t2/articles/922168/>
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

## Prometheus and VictoriaMetrics <https://habr.com/ru/companies/t2/articles/922168/>

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

<https://www.youtube.com/@Grafana>

<https://grafana.com/events/grafanacon/2025/loki-at-dropbox-logging-at-petabyte-scale>

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

### Does MQTT Broker Have Replicas Like Kafka?

Typically, **MQTT brokers do not have built-in replication like Kafka** does. However, some advanced MQTT broker implementations **support high availability and clustering**, but not with the same level of partitioned replication and distributed durability as Kafka.

#### MQTT Broker Redundancy Options:
- **Mosquitto**: No built-in clustering or replication. Can use external load balancer or HA proxy.
- **EMQX, HiveMQ, VerneMQ**: Support clustering and failover, but replication is often eventual and not as strict as Kafka's guarantees.

---

### Main Differences Between Kafka and MQTT Broker

| Feature                     | Kafka                                      | MQTT Broker                                 |
|----------------------------|--------------------------------------------|---------------------------------------------|
| Protocol Type              | High-throughput distributed log system     | Lightweight publish-subscribe protocol      |
| Transport                  | TCP                                        | TCP (or WebSockets)                         |
| Broker Replication         | Yes, built-in replication of partitions    | Usually no; some brokers support HA         |
| Persistence                | Strong durability with disk-based storage  | Optional; many MQTT messages are transient  |
| Message Retention          | Configurable by time or size (logs)        | Short-lived unless retained flag is set     |
| Ordering Guarantees        | Per partition                              | No strict ordering                          |
| Throughput                 | High (optimized for large-scale pipelines) | Low to moderate (optimized for IoT/edge)    |
| Use Case                   | Event streaming, analytics, pipelines      | IoT telemetry, mobile messaging             |
| Client Requirements        | Generally more heavyweight                 | Very lightweight (suitable for microcontrollers) |
| QoS (Quality of Service)   | Not natively (uses ack + retries in client)| Yes (QoS 0, 1, 2)                            |

---

### Summary

- **Kafka** is a distributed, persistent, high-throughput log platform with strong replication and fault-tolerance guarantees. It’s optimized for data pipelines and analytics.
- **MQTT brokers** are optimized for lightweight, low-latency communication in IoT and mobile scenarios. While some support clustering, they lack Kafka’s log-based replication model.

Kafka is best for **back-end systems**, while MQTT is best for **edge and device communication**.


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

### When to Choose CoAP vs MQTT

Choosing between **CoAP** and **MQTT** depends on your application requirements, especially around network reliability, power constraints, message flow model, and device capabilities.

---

### CoAP is Better When:

- **You need RESTful interaction** (e.g., GET/PUT on resources like `/sensor/temp`)
- **You prefer HTTP-like semantics** in constrained environments
- **Multicast support is important** (e.g., sending command to many devices at once)
- **You want UDP-based communication** (lower overhead, no connection setup)
- **Power usage is extremely critical** (sleepy nodes, battery-powered sensors)
- **Your devices are addressable by IP** (sensors with IP addresses and routes)

#### Example Use Cases:
- Wireless sensor networks
- Smart street lighting
- Smart meters
- Actuator control (e.g., turning on/off a device directly)

---

### MQTT is Better When:

- **You need reliable delivery and message ordering**
- **You want pub/sub pattern** (decoupled producers and consumers)
- **You need persistent session and QoS** (Quality of Service 0, 1, 2)
- **Devices are not always online**, but must receive messages later (via retained messages)
- **Network is lossy or intermittent**, but TCP overhead is acceptable
- **Backend systems need easy integration**

#### Example Use Cases:
- Telemetry from mobile or embedded devices
- Remote health monitoring
- Fleet tracking
- Smart home automation (e.g., Home Assistant)

---

### Summary Table

| Feature                  | CoAP                                | MQTT                                 |
|--------------------------|--------------------------------------|---------------------------------------|
| Model                    | Client-Server (REST)                 | Publish-Subscribe (event-driven)      |
| Transport                | UDP                                  | TCP                                   |
| Reliability              | Optional (confirmable messages)      | Built-in QoS levels (0, 1, 2)         |
| Message Pattern          | Request/Response                     | Publish/Subscribe                     |
| Multicast Support        | Yes                                  | No                                    |
| Power Efficiency         | Very high                            | High                                  |
| Built-in Persistence     | No (stateless)                       | Yes (retain, persistent sessions)     |
| Ideal Use                | Device control, direct access        | Asynchronous messaging, telemetry     |

### MQTT and CoAP Message Formats

Both **MQTT** and **CoAP** are designed for IoT, but they use very different message formats optimized for different goals.

---

### MQTT Message Format

MQTT messages are **binary encoded** and have a simple fixed header with optional variable headers and payload.

#### General Structure:
+------------+--------------------+------------------+  
| Fixed Header | Variable Header | Payload |  
+------------+--------------------+------------------+  

 

#### 1. Fixed Header (2+ bytes)
- Message type (e.g., CONNECT, PUBLISH, SUBSCRIBE)
- Flags (DUP, QoS, RETAIN)
- Remaining length (length of variable header + payload)

#### 2. Variable Header (varies by message type)
- Topic name (for PUBLISH)
- Packet Identifier (for QoS > 0)
- Additional fields (Client ID, Will, etc.)

#### 3. Payload
- Message body (optional, e.g., JSON, string, binary)

#### Example: PUBLISH packet (QoS 1)
Fixed Header: PUBLISH, QoS 1, DUP=0, RETAIN=0
Variable Header: Topic="sensor/temp", Packet ID=0x1234
Payload: "22.4"

 

 

### CoAP Message Format

CoAP messages are also **binary encoded**, and follow a compact header-payload model over **UDP**.

#### General Structure:
+------------------------+----------------+-------------------+  
| Header (4 bytes)       | Options (0-N) | Payload (optional)|  
+------------------------+----------------+-------------------+  

 

#### 1. Fixed Header (4 bytes)
- Version (2 bits)
- Type (2 bits): CON, NON, ACK, RST
- Token length (4 bits)
- Code (8 bits): Method (GET/POST/PUT/DELETE) or response code (e.g., 2.05 OK)
- Message ID (16 bits)

#### 2. Token (0–8 bytes)
- Matches response to request

#### 3. Options (compressed TLV format)
- URI path, content format, accept type, etc.

#### 4. Payload (optional)
- Starts with a special marker `0xFF` (if present)
- Contains the actual content (e.g., JSON)

#### Example: GET /sensor/temp
Header: CON, Code=GET, MID=0x1234, Token=0xAA
Options: Uri-Path = "sensor", "temp"
Payload: (none for GET)

 

---

### Summary Comparison

| Field                  | MQTT                                   | CoAP                                 |
|------------------------|-----------------------------------------|--------------------------------------|
| Transport              | TCP                                     | UDP                                  |
| Encoding               | Binary                                  | Binary                               |
| Header Size            | 2+ bytes                                | 4 bytes fixed + variable options     |
| Method Representation  | Message Type field                      | Code field (GET, POST, etc.)         |
| Payload Format         | Application-defined (e.g., JSON)        | Application-defined (e.g., JSON)     |
| Optional Fields        | Topic, Packet ID, QoS flags             | Options (Uri-Path, Content-Format)   |
| Message ID             | Optional (QoS > 0)                      | Mandatory                            |
| Token-based Matching   | No                                      | Yes (Token field)                    |


### Final Guidance:

- Choose **CoAP** when you want **low-power, REST-style access** to constrained devices over **UDP**.
- Choose **MQTT** when you want **reliable, asynchronous messaging** with **decoupled producers/consumers** over **TCP**.

Let me know if you want example scenarios or combined use of both protocols in a hybrid architecture.


### Summary

- CoAP is like a mini-HTTP for IoT, optimized for low-resource devices.
- It uses UDP, supports RESTful interactions, and enables efficient communication over lossy or constrained networks.
- Common in smart homes, industrial IoT, and wireless sensor networks.




https://sre.google/sre-book/monitoring-distributed-systems/

https://habr.com/ru/articles/917658/

https://signoz.io/blog/cicd-observability-with-opentelemetry/

https://news.ycombinator.com/item?id=44247020


https://pypi.org/project/otlp-json/
