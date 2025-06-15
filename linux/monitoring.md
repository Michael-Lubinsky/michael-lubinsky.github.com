
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

## 📚 Useful Ports

| Service         | Port  |
|------------------|--------|
| Node Exporter    | 9100   |
| Prometheus       | 9090   |
| Grafana          | 3000   |




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



https://sre.google/sre-book/monitoring-distributed-systems/

https://habr.com/ru/articles/917658/

https://signoz.io/blog/cicd-observability-with-opentelemetry/

https://news.ycombinator.com/item?id=44247020

