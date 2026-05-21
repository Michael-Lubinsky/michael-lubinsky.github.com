## Databricks dashboards 

support **filters** that apply to the SQL queries powering the visualizations.

There are two types:

## 1. Dashboard-level filter (affects all widgets)

In the dashboard editor, click **"Add filter"** in the toolbar. You pick a column that exists across your dataset   
Databricks then renders a dropdown/multi-select/date picker UI. 

When the user selects a value it is injected as a WHERE condition into **all queries** that have a column with the same name.

Best for: filtering by `date`, `user_id`, `intervention_type` — columns shared across multiple tiles.

---

## 2. Query parameter (per-widget filter)

In the SQL query backing a widget, use the `{{ parameter_name }}` Jinja syntax:

```sql
SELECT
    user_id,
    q1_environmental_importance,
    q2_cost_saving_importance,
    q3_charging_goals,
    recorded_at
FROM hcai_databricks_dev.chargeminder2.intervention_surveys
WHERE date >= {{ start_date }}
  AND date <= {{ end_date }}
  AND q1_environmental_importance >= {{ min_env_score }}
```

Databricks renders each `{{ }}` placeholder as an input widget (text box, dropdown, date picker) automatically. You configure the widget type and default value in the query editor sidebar.


## 3. Lakeview dashboards (newer UI) vs legacy

The experience depends on which dashboard type you have:

**Lakeview (AI/BI dashboards)** — the current default in Databricks. Filters are first-class — click the filter icon in the canvas toolbar, choose a field, and it cross-filters all tiles that use that field. Much more polished.

**Legacy dashboards** — use the `{{ parameter }}` syntax per query, then in the dashboard you can link parameters across widgets to make them act as a shared filter.

---

## Practical recommendation for your surveys/notifications data

```sql
-- Example: filter notifications by intervention_type and date range
SELECT
    intervention_type,
    COUNT(*) AS notification_count,
    DATE_TRUNC('day', sent_at) AS day
FROM hcai_databricks_dev.chargeminder2.notifications
WHERE intervention_type = '{{ intervention_type }}'
  AND date BETWEEN '{{ start_date }}' AND '{{ end_date }}'
GROUP BY 1, 3
ORDER BY 3
```

If you're on Lakeview, you don't need the `{{ }}` syntax at all — just add a filter tile pointing at the `intervention_type` column and it wires up automatically to all queries using that table.

Which dashboard type do you have — Lakeview or legacy?
