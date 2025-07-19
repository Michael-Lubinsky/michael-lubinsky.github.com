## Grafana

In Grafana 12 (released around May 7, 2025) the old “Explore” suite has been renamed and upgraded to Grafana Drilldown,   
introducing a powerful Drilldown menu entry in the main sidebar 
(e.g. Drilldown → Metrics, Logs, Traces, Profiles) 

```
Drilldown → Metrics, Logs, Traces, Profiles
```

Source: [grafana.com - Drilldown Apps Overview](https://grafana.com/blog/2025/02/20/grafana-drilldown-apps-the-improved-queryless-experience-formerly-known-as-the-explore-apps/?utm_source=chatgpt.com)

---

## 🛠️ Key Features of Drilldown

### 1. Unified, Queryless Exploration
Explore telemetry data (metrics, logs, traces, profiles) visually—no need to write PromQL, LogQL, etc.

### 2. Four Drilldown Apps
- **Metrics Drilldown**  
  - Auto-displays charts  
  - Group/filter by labels, prefixes, suffixes  
  - Pivot into logs for context  
  - Docs: https://grafana.com/docs/grafana/latest/explore/simplified-exploration/metrics/drill-down-metrics/

- **Logs Drilldown**  
  - Log volumes by service/label/text pattern  
  - Inline JSON support  
  - Filter via UI  
  - Docs: https://grafana.com/docs/grafana/latest/explore/simplified-exploration/logs/

- **Traces Drilldown**  
  - RED metrics (Rate, Errors, Duration)  
  - Span breakdowns & heatmaps  
  - Query-free filter by labels  
  - Docs: https://grafana.com/docs/grafana/latest/explore/simplified-exploration/traces/

- **Profiles Drilldown** *(new in Grafana 12)*  
  - Visualize CPU/Memory profiles  
  - Hot path & spike detection  
  - Docs: https://grafana.com/docs/grafana/latest/explore/simplified-exploration/profiles/

---

## 🔍 Drilldown App Highlights

### Metrics Drilldown
- Sidebar filtering (prefix/suffix/regex)
- Label grouping & pivoting
- OpenTelemetry label joins
- Native histogram support
- One-click switch to logs

More: https://grafana.com/blog/2025/05/29/whats-new-in-grafana-metrics-drilldown-advanced-filtering-options-ui-enhancements-and-more/

---

### Logs Drilldown
- Service-level log view
- Label/field drilldown
- JSON rendering
- Multi-filter & pagination

---

### Traces Drilldown
- View by span rate, errors, duration
- Heatmaps, breakdown tabs
- Easy filtering

---

### Profiles Drilldown
- Interactive flamegraphs
- CPU/memory usage visualizations
- Root-cause hotspot detection

---

## ✅ Benefits of Grafana Drilldown

- No query language required
- Unified interface for all telemetry types
- Deep context switching (metrics → logs → traces)
- Great for fast incident investigation

---

## 🧭 How to Use It

1. Upgrade to Grafana 12+ (or use Grafana Cloud)
2. Navigate to **Drilldown** in the sidebar
3. Pick an app: Metrics, Logs, Traces, or Profiles
4. From dashboard panels, you can also click:
   ```
   Panel menu → Metrics drilldown
   ```

Docs:
- Getting Started: https://grafana.com/docs/grafana/latest/explore/simplified-exploration/metrics/get-started/


### Snowflake

Options to connect Snowflake to Grafana:
### 1. [Grafana Snowflake Plugin by Grafana Labs (Premium/Enterprise only)]
Available in Grafana Enterprise or Grafana Cloud Pro/Advanced tiers.

Official plugin: Snowflake data source plugin

Features:
SQL query editor
Time series support
Table, bar chart, pie chart visualizations

Authentication:
Username/password
OAuth (in some setups)

Requires setting up the Snowflake connection string and credentials.

### 2. Using a middle layer (alternative for OSS users)
If you're using Grafana OSS (Open Source) and can't use the premium plugin, consider:

PostgREST + Snowflake External Table: Create external views in Snowflake that are queried via another supported source.

Apache Arrow Flight SQL or ODBC bridge: Connect Snowflake via an ODBC/Flight SQL connector that exports to a source Grafana supports (like PostgreSQL proxy).

Python API (with Flask + SQLAlchemy + JSON API): Write a backend API that queries Snowflake and use Grafana's JSON API plugin to visualize it.

| Method                               | Native? | License Required | Complexity | Notes                       |
| ------------------------------------ | ------- | ---------------- | ---------- | --------------------------- |
| Grafana Snowflake Plugin             | ✅       | Enterprise/Cloud | Low        | Easiest if you have license |
| JSON API Plugin + Custom Backend     | ❌       | Free             | Medium     | Use Python or Node.js       |
| Proxy via PostgreSQL or Presto/Trino | ❌       | Free             | High       | Not real-time; more for ETL |

