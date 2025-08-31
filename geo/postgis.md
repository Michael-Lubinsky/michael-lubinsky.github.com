## PostGIS

https://habr.com/ru/companies/selectel/articles/939804/

### Metabase
How to visualize an array of (longitude, latitude) data points in Metabase, using the Map visualization 

✅ Step-by-Step: Visualize Longitude & Latitude in Metabase
🔹 1. Prepare the data
Ensure your table (or query result) has at least these two columns:

- longitude  
- latitude  

Optionally, you can add:

- label (e.g., name, location)  
- value (e.g., count, temperature)  

Example structure:

```sql
SELECT
  name,
  latitude,
  longitude
FROM your_table;
```
🔹 2. Open Metabase > Ask a Question > Native or Simple Query
Go to your dashboard or collection

Click "Ask a question" > Native query (or Simple question if the data is already in a table)

🔹 3. Choose the Map Visualization
Once your query/table displays:

Click the Visualization tab

Choose Map

🔹 4. Choose Map Type
Metabase offers:

Pin Map – for plotting individual points

Region Map – for aggregating values over countries/regions (you probably want Pin Map)

🔹 5. Configure the Pin Map
Set the Latitude column

Set the Longitude column

Optionally, set the Label and Value

🔹 6. Save the Question
Click Save

Name the question (e.g., "GPS Points Map")

Optionally, add it to a dashboard

🗺️ Example Use Case
If you have a table like:
```
name	latitude	longitude
Cafe A	37.7749	-122.4194
Cafe B	34.0522	-118.2437
```
You can use it to create a map showing pins for each cafe.

🛠 Notes
Metabase uses Mapbox behind the scenes

Ensure coordinates are numeric (not text)

At least 2 decimal digits are recommended for accuracy


✅ Example SQL for Metabase Map
Suppose your table is called gps_points with columns:

name – name of the location  
latitude – numeric  
longitude – numeric  

Here is a sample SQL query:

```sql

SELECT
  name,
  latitude,
  longitude
FROM gps_points
WHERE latitude IS NOT NULL
  AND longitude IS NOT NULL;
```

🗺 How to Use This in Metabase  
Go to Metabase > Ask a question > Native SQL

Paste the query above (adjust table/column names if needed)

Run it

Click the Visualization tab

Select Map > Pin Map

Set:

- Latitude → latitude  
- Longitude → longitude  
- (Optional) Label → name

Click Save, name your map, and optionally add to a dashboard.

📌 Tips
If you don’t have separate latitude/longitude columns but a single POINT column (PostGIS),  
you can extract them like this:

```sql
SELECT
  name,
  ST_Y(geom) AS latitude,
  ST_X(geom) AS longitude
FROM your_postgis_table
WHERE geom IS NOT NULL;
```
(Requires PostGIS extension)

