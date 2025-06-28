https://superset.apache.org/


Superset only loads `superset_config.py` if it is in the Superset home directory  
or the directory set in the `SUPERSET_CONFIG_PATH` environment variable. 
Creating it in the current directory alone will not be picked up by Superset.

Alternatively, explicitly set:
```bash
export SUPERSET_CONFIG_PATH=/path/to/your/superset_config.py
```

  Uninstall marshmallow 4.x:**  
pip uninstall marshmallow

 Install a Superset compatible marshmallow version   
pip install 'marshmallow>=3.13,<4.0'




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

http://localhost:8088

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


