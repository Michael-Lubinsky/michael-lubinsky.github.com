https://superset.apache.org/



When you install Superset and load examples using:
```bash
superset load_examples
```
Superset creates **example datasets, charts, and dashboards** and stores them in **Superset’s metadata database** (typically SQLite, Postgres, or MySQL, depending on your configuration).

The **example datasets themselves** are stored as **table metadata in Superset** pointing to underlying SQL tables (often created in a bundled SQLite file or memory database).   
They are **not stored as CSV or raw files on disk**, but inside the database Superset uses for metadata and example data storage.


## Where is the source code for dashboards and charts located?

- **Dashboards and charts are not stored as static files in the Superset installation folder.**
- They are stored in Superset’s metadata database as JSON configurations describing:
  - Chart SQL queries  
  - Chart visualization types and configurations  
  - Dashboard layouts and components  
- Example charts and dashboards are initially created using Python scripts in Superset’s source under:
  ```
  superset/examples/ 
  ```
  and are executed when `superset load_examples` is run.

If you want to extract dashboard or chart definitions for version control,   
you can export them via the Superset UI   
or using the Superset CLI with   
`superset export-dashboards` and `superset export-charts`.


## What is the difference between dashboards and charts?

✅ **Charts:**
- A **chart** in Superset is a **single visualization** based on a dataset or SQL query (e.g., bar chart, line chart, pie chart).
- Charts have:
  - A visualization type.
  - A dataset or SQL query.
  - Filters and visualization configurations.

✅ **Dashboards:**
- A **dashboard** is a **collection of charts** arranged in a grid layout for interactive exploration.
- Dashboards can include:
  - Multiple charts.
  - Filters and controls that affect all charts.
  - Markdown and headers for annotations.

**Summary:**
- **Charts = single visual analysis on data.**
- **Dashboards = organized collection of charts and filters for comprehensive analysis.**


### Examples superset/examples
pwd  
/Users/mlubinsky/CODE/SUPERSET/superset-venv/lib/python3.10/site-packages/superset/examples
```
ls -1 | sort
__init__.py
__pycache__
bart_lines.py
big_data.py
birth_names.py
configs
countries.md
countries.py
country_map.py
css_templates.py
data_loading.py
deck.py
energy.py
flights.py
helpers.py
long_lat.py
misc_dashboard.py
multiformat_time_series.py
paris.py
random_time_series.py
sf_population_polygons.py
supported_charts_dashboard.py
tabbed_dashboard.py
utils.py
world_bank.py
```


##  Add your Postgres database in Superset

pip install psycopg2-binary

1. Go to **Data > Databases**.
2. Click **+ Database**.
3. Set:
   - **Display Name:** `Local Postgres` (or any name).
   - **SQLAlchemy URI:**
     ```
     postgresql://<username>:<password>@localhost:5432/<database_name>
     ```
     Example:
     ```
     postgresql://mlubinsky:yourpassword@localhost:5432/postgres
     ```
4. Click **Test Connection**.
5. If successful, click **Connect**.

---

## ✅ 3️⃣ Add your table `T` as a dataset
1. Go to **Data > Datasets**.
2. Click **+ Dataset**.
3. Select the **Database** you just created.
4. Select the **Schema** (often `public` unless changed).
5. Select the **Table** `T`.
6. Click **Add**.

---

## ✅ 4️⃣ Create your first chart
1. Go to **Charts**.
2. Click **+ Chart**.
3. Select your **dataset `T`**.
4. Choose a **chart type** (e.g., **Bar Chart** or **Time-series Line Chart**).
5. Click **Create New Chart**.
6. Configure:
   - **X-axis:** `ts` (timestamp).
   - **Y-axis:** `value` (float).
   - Optionally, add **group by** `device_name` or `device_type`.
7. Click **Run** to visualize.
8. Click **Save** and give it a name like "Device Value Over Time".


### Using a SQL-based Virtual Dataset

1. Go to **Data > Datasets**.
2. Click **+ Dataset**.
3. Select your Postgres database.
4. Choose **"Write a SQL query that defines the dataset"** instead of selecting a single table.
5. Write your SQL join, for example:
    ```sql
    SELECT a.id, a.device_name, b.status, a.ts, a.value
    FROM T a
    JOIN device_status b ON a.device_name = b.device_name
    WHERE a.ts >= '2025-01-01'
    ```
6. Click **Preview** to confirm it works.
7. Save the virtual dataset with a descriptive name (e.g., `T joined with device_status`).

Now you can create charts using this virtual dataset as if it were a physical table.


### superset_config.py
Superset only loads `superset_config.py` if it is in the Superset home directory  
or the directory set in the `SUPERSET_CONFIG_PATH` environment variable. 
Creating it in the current directory alone will not be picked up by Superset.

Alternatively, explicitly set:
```bash
export SUPERSET_CONFIG_PATH=/path/to/your/superset_config.py
```
### marshmallow version
pip show marshmallow  
Uninstall marshmallow 4.x:**  
pip uninstall marshmallow  
Install a Superset compatible marshmallow version   
pip install 'marshmallow>=3.13,<4.0'

### Reset the password for the existing `admin` user**:

superset fab reset-password --username admin


```bash
python3 -m venv superset-venv
source superset-venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install apache-superset

export FLASK_APP=superset 
superset db upgrade
# A Default SECRET_KEY was detected, please use superset_config.py to override it.
# Refusing to start due to insecure SECRET_KEY

superset fab create-admin
# User first name [admin]:
# User last name [user]:
# Email [admin@fab.org]:
# Password

superset load_examples
superset init
superset run -p 8088 --with-threads --reload --debugger
```

http://localhost:8088  admin/admin

## Superset Local Development (build from source)
- Pre-requisites: Python 3.9 or 3.10  
- Node.js (LTS recommended, e.g., 18.x)  
- npm or yarn  
- Docker (optional for DB/Redis dependencies)

```bash
# Clone the repo
git clone https://github.com/apache/superset.git
cd superset

# Set up Python virtual environment
python -m venv venv
source venv/bin/activate

# Install backend dependencies
pip install -e ".[dev]"

# Install frontend dependencies
cd superset-frontend
npm ci
npm run build
cd ..

export FLASK_APP=superset
# Initialize the database
superset db upgrade

# Create an admin user

superset fab create-admin

# Load examples (optional)
superset load_examples

# Start the app
superset run -p 8088 --with-threads --reload --debugger
```
Visit:  
http://localhost:8088  
and log in with your admin credentials.

### Production Deployment
Common Stack:
- Superset served via Gunicorn  
- Nginx as a reverse proxy  
- PostgreSQL or MySQL for metadata DB  
- Redis for caching and async task queues  
- Celery for async SQL Lab and background tasks  

Steps:
a. Database and Redis
Provision PostgreSQL/MySQL database for superset_config.py.

Provision Redis.

b. Configuration
Create a superset_config.py:
```python
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://user:password@host/dbname'
SECRET_KEY = 'your_random_secret_key'
REDIS_HOST = 'localhost'
CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_KEY_PREFIX': 'superset_',
    'CACHE_REDIS_URL': 'redis://localhost:6379/0'
}
```
Set:
```bash
export SUPERSET_CONFIG_PATH=/path/to/superset_config.py
```

c. Initialize DB
```bash
superset db upgrade
superset fab create-admin
```

d. Start Superset with Gunicorn
```bash
gunicorn \
    --workers 5 \
    --timeout 120 \
    -b 0.0.0.0:8088 \
    'superset.app:create_app()'
```

e. Configure Celery Worker
```bash
celery --app=superset.tasks.celery_app:app worker --pool=prefork -O fair -c 4
```

f. Optional: Configure Flower for Celery monitoring
```bash
celery --app=superset.tasks.celery_app:app flower
```
g. Nginx Reverse Proxy
Configure Nginx to proxy requests to Gunicorn on localhost:8088.

## Docker Deployment (Recommended for quick setup)
Apache Superset provides official Docker Compose support for quick deployment.
```bash

git clone https://github.com/apache/superset.git
cd superset

# Copy example env file
cp .env.example .env

# Start Superset
docker compose up
```
On first run:

```bash
docker compose exec superset superset db upgrade
docker compose exec superset superset fab create-admin
docker compose exec superset superset load_examples
docker compose exec superset superset init
```
Access:

http://localhost:8088

## Deployment on Cloud
You can deploy Superset on: AWS ECS, EKS, or EC2, Azure AKS, App Service, or VM

GCP GKE or Compute Engine

Heroku (less recommended for production due to file system limitations)

Recommended:
✅ Use containerized deployments with CI/CD.
✅ Store metadata in RDS/Aurora (AWS) or Cloud SQL (GCP).
✅ Use managed Redis services.
✅ Configure TLS (via Nginx/Load Balancer or Traefik).

6️⃣ Security and Hardening Checklist
Enforce HTTPS

Configure strong SECRET_KEY

Use production-grade DB and Redis

Enable authentication (OIDC, LDAP, OAuth2 if needed)

Limit admin privileges

Enable database and dashboard-level access control

Regularly upgrade Superset to patch vulnerabilities

🚀 Summary
For development: clone, install, run superset run.

For production: use Gunicorn + Nginx + PostgreSQL + Redis + Celery.

For simplicity and cloud readiness: use Docker Compose or Kubernetes deployments.

Ensure proper configuration, scaling, and security for a stable production environment.


