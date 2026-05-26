## Databricks dashboards 

### **Dashboard parameters**.

Change SQL to:

```sql
SELECT x
FROM T
WHERE date > :start_date
  AND date < :end_date
  AND user_id = :user_id
```
As soon as Databricks sees :start_date, :end_date, and :user_id, it automatically recognizes them as parameters.

Then:
```
Save the query.
Open the visualization/dashboard.
Databricks will usually show parameter controls automatically.
If not:
click Add → Filter
bind the filter to the parameter.
```
Then in the Databricks dashboard:

1. Open the dashboard in **Edit** mode.
2. Open the dataset/query behind the plot.
3. Add parameters:

   * `start_date` → type **Date**
   * `end_date` → type **Date**
   * `user_id` → type **Number** or **Text**
4. Add dashboard **Filter widgets**.
5. Connect each filter widget to the corresponding parameter.
6. Publish the dashboard.

Databricks AI/BI dashboards support named SQL parameters using `:parameter_name`, and viewers can change values through filter widgets at runtime. ([Databricks Documentation][1])

For a date range, you can also use one date-range parameter:

```sql
SELECT x
FROM T
WHERE date BETWEEN :date_range.min AND :date_range.max
  AND user_id = :user_id
```

Databricks supports parameter filters such as single value, multiple values, date picker, and date range. ([docs.azure.cn][2])

[1]: https://docs.databricks.com/aws/en/dashboards/manage/filters/parameters?utm_source=chatgpt.com "Work with dashboard parameters | Databricks on AWS"
[2]: https://docs.azure.cn/en-us/databricks/dashboards/filters?utm_source=chatgpt.com "Use dashboard filters - Azure Databricks"

In Databricks AI/BI dashboards (and also in SQL Editor), parameters are created directly inside the SQL text.

Example — replace constants with parameter names:

```sql
SELECT x
FROM T
WHERE date > :start_date
  AND date < :end_date
  AND user_id = :user_id
```

As soon as Databricks sees `:start_date`, `:end_date`, and `:user_id`, it automatically recognizes them as parameters.

Then:

1. Save the query.
2. Open the visualization/dashboard.
3. Databricks will usually show parameter controls automatically.
4. If not:

   * click **Add → Filter**
   * bind the filter to the parameter.

---


## Method 1 — directly from dashboard

### 1. Edit dashboard

Open dashboard → click **Edit**.

---

### 2. Open dataset/query

Click the chart/plot.

Choose:

* **Edit visualization**
  or
* **Edit query**

(depending on dashboard type/UI version)

---

### 3. Replace hardcoded values

Before:

```sql
SELECT x
FROM T
WHERE date < '2025-12-01'
  AND date > '2025-01-01'
  AND user_id = 5
```

After:

```sql
SELECT x
FROM T
WHERE date < :end_date
  AND date > :start_date
  AND user_id = :user_id
```

---

### 4. Run query

Click **Run**.

Databricks detects parameters automatically.

You should see parameter controls appear near the top.

---

### 5. Configure parameter type

For each parameter:

* Date
* Number
* Text
* Dropdown
* Multi-select

You can optionally:

* set default values
* allow multiple values
* map dropdown values from query results

---

### Optional: dropdown populated from table

Example:

```sql
SELECT DISTINCT user_id
FROM T
ORDER BY user_id
```

Use this query as source for dropdown values.

---

### Multiple selection example

```sql
SELECT x
FROM T
WHERE user_id IN (:user_ids)
```

Then configure parameter as:

* multi-select

---

### Dynamic date shortcuts

Databricks date filters also support:

* Last 7 days
* Last month
* This year
* etc.

through dashboard filter widgets.

---

### Important syntax

Use:

```sql
:param_name
```

NOT:

* `${param}`
* `{{param}}`

Those belong to other BI tools.

---

### Legacy dashboards vs AI/BI dashboards

Databricks currently has:

* classic SQL dashboards
* AI/BI dashboards

Both support parameters, but UI differs slightly.

The SQL syntax with `:param` is the important part.


### Claude 
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
