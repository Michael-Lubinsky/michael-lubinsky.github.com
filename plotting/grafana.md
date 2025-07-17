## Grafana

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

