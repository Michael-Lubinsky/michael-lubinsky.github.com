
##  Relation Between Prometheus and VictoriaMetrics

- **VictoriaMetrics is designed to be a drop-in replacement or long-term storage backend for Prometheus.**
- **They can be used together**: Prometheus scrapes metrics and pushes them to VictoriaMetrics (via remote write).
- **VictoriaMetrics supports the Prometheus query language (PromQL)** and many of its APIs.

---

## 🔍 Key Differences and Features

| Feature                     | Prometheus                          | VictoriaMetrics                          |
|-----------------------------|-------------------------------------|-------------------------------------------|
| **Primary Role**           | Time-series database + scraper      | Time-series database only                 |
| **Data Ingestion**         | Pull-based (scrapes targets)        | Push-based (via Prometheus remote write) |
| **Storage Duration**       | Short-term (days to weeks)          | Long-term (months to years)              |
| **Scalability**            | Limited (single-node)               | Highly scalable (single-node or cluster) |
| **Performance**            | Optimized for simplicity            | Optimized for ingestion & query speed     |
| **Use Case Together**      | Prometheus scrapes, Victoria stores | VictoriaMetrics stores & queries metrics |

---

## 🧩 Typical Setup Using Both

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

OTel is an open-source observability framework that enables collecting traces, metrics, and logs in a standard, vendor-agnostic way.


https://sre.google/sre-book/monitoring-distributed-systems/

https://habr.com/ru/articles/917658/

https://signoz.io/blog/cicd-observability-with-opentelemetry/

https://news.ycombinator.com/item?id=44247020

