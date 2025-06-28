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

# Initialize the database
superset db upgrade

# Create an admin user
export FLASK_APP=superset
superset fab create-admin

# Load examples (optional)
superset load_examples

# Start the app
superset run -p 8088 --with-threads --reload --debugger
```
Visit:  
http://localhost:8088  
and log in with your admin credentials.

