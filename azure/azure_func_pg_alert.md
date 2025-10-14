Ah, excellent! You're right - using **token-based authentication with Managed Identity** is much more secure. This is actually the **Azure best practice**.

Let's set this up properly!

---

## **Step 1: Enable Managed Identity**

Remember that **Identity** setting we discussed earlier? Now we need to turn it **ON**.

1. In your Function App, go to **Settings** → **Identity**
2. Under **System assigned** tab
3. Set **Status** to **On**
4. Click **Save**
5. Click **Yes** to confirm
6. **Copy the Object (principal) ID** that appears (you'll need it)

---

## **Step 2: Configure PostgreSQL for Azure AD Authentication**

1. Go to your **PostgreSQL Flexible Server** in Azure Portal
2. Go to **Settings** → **Authentication**
3. **Authentication method**: Select **Azure Active Directory authentication only** (or **PostgreSQL and Azure Active Directory authentication**)
4. Click **Add Azure AD admin** and add yourself as admin
5. Click **Save**

---

## **Step 3: Grant Function App Access to PostgreSQL**

Now we need to create a database user for your Function App's Managed Identity.

### **Option A: Using Azure Portal (if available)**

Some PostgreSQL servers have this option:
1. In PostgreSQL server, go to **Settings** → **Authentication**  
2. Look for **"Azure AD users"** or **"Add user"**
3. Add your Function App name

### **Option B: Using SQL (More reliable)**

1. Connect to your PostgreSQL using Azure Cloud Shell or any SQL client
2. Run these commands:

```sql
-- Connect as Azure AD admin first

-- Create role for your Function App
-- Replace "dataplatform" with your Function App name
CREATE ROLE "dataplatform" WITH LOGIN;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE your_database_name TO "dataplatform";
GRANT USAGE ON SCHEMA public TO "dataplatform";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO "dataplatform";
GRANT SELECT ON your_table_name TO "dataplatform";

-- If you need to grant to future tables too
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO "dataplatform";
```

**Important:** The role name must **exactly match** your Function App name: `dataplatform`

---

## **Step 4: Update Function Code for Token Authentication**

Now update your function code to use Managed Identity instead of passwords:

```python
import azure.functions as func
import logging
import os
import sys
import subprocess

def install_if_missing(package, import_name=None):
    """Install package on first run if not available"""
    if import_name is None:
        import_name = package.replace('-', '_')
    try:
        __import__(import_name)
        return True
    except ImportError:
        logging.info(f'Installing {package}...')
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package])
            return True
        except Exception as e:
            logging.error(f'Failed to install {package}: {e}')
            return False

app = func.FunctionApp()

# Timer trigger - runs every 6 hours
@app.schedule(schedule="0 0 */6 * * *", arg_name="myTimer", run_on_startup=False)
def check_database_records(myTimer: func.TimerRequest) -> None:
    logging.info('=' * 50)
    logging.info('Starting database check with Managed Identity...')
    logging.info('=' * 50)
    
    # Install required packages
    if not install_if_missing('psycopg2-binary', 'psycopg2'):
        logging.error('Cannot proceed without psycopg2')
        return
    
    if not install_if_missing('azure-identity'):
        logging.error('Cannot proceed without azure-identity')
        return
    
    try:
        import psycopg2
        from azure.identity import DefaultAzureCredential
        
        # Get database connection info from environment variables
        db_host = os.environ.get('DB_HOST')
        db_name = os.environ.get('DB_NAME')
        db_user = os.environ.get('DB_USER')  # Your Function App name
        
        if not all([db_host, db_name, db_user]):
            logging.error('Missing database configuration!')
            logging.error('Required: DB_HOST, DB_NAME, DB_USER')
            return
        
        logging.info(f'Database: {db_host}/{db_name}')
        logging.info(f'User: {db_user}')
        
        # Get Azure AD access token using Managed Identity
        logging.info('Getting access token from Managed Identity...')
        credential = DefaultAzureCredential()
        token_response = credential.get_token(
            "https://ossrdbms-aad.database.windows.net/.default"
        )
        access_token = token_response.token
        
        logging.info('✓ Token obtained successfully')
        
        # Connect to PostgreSQL using the token as password
        logging.info('Connecting to PostgreSQL with token...')
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=access_token,
            sslmode='require'
        )
        
        logging.info('✓ Connected successfully!')
        
        cur = conn.cursor()
        
        # Get table name from environment variable
        table_name = os.environ.get('DB_TABLE', 'your_table_name')
        
        query = f"SELECT COUNT(*) FROM {table_name}"
        logging.info(f'Executing: {query}')
        
        cur.execute(query)
        record_count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        logging.info(f'✓ Query successful!')
        logging.info(f'✓ Record count: {record_count}')
        logging.info(f'✓ Threshold: 10')
        
        # Check if below threshold
        if record_count < 10:
            logging.warning('⚠️ ALERT: Record count below threshold!')
            send_email_alert(record_count)
        else:
            logging.info('✓ Status: OK (above threshold)')
        
        logging.info('=' * 50)
        logging.info('Database check completed')
        logging.info('=' * 50)
        
    except Exception as e:
        logging.error('=' * 50)
        logging.error(f'ERROR: {str(e)}')
        logging.error('=' * 50)
        import traceback
        logging.error(traceback.format_exc())


def send_email_alert(record_count):
    """Send email alert via SMTP"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime
    
    try:
        # Get SMTP settings from environment variables
        smtp_server = os.environ.get('SMTP_SERVER')
        smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        smtp_user = os.environ.get('SMTP_USER')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        recipient_email = os.environ.get('ALERT_EMAIL', 'admin@company.com')
        
        if not all([smtp_server, smtp_user, smtp_password]):
            logging.error('Email not configured! Missing SMTP settings')
            return
        
        # Create email
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = recipient_email
        msg['Subject'] = f'⚠️ Database Alert: Only {record_count} Records!'
        
        body = f"""
DATABASE ALERT
{'=' * 50}

⚠️  Record count is below threshold!

Current count: {record_count}
Threshold:     10
Status:        CRITICAL

Time:          {datetime.utcnow()} UTC

Please investigate immediately.

{'=' * 50}
This is an automated alert from Azure Functions.
Authentication: Managed Identity (no passwords)
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        logging.info(f'Sending email to {recipient_email}...')
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        logging.info('✓ Email sent successfully!')
        
    except Exception as e:
        logging.error(f'Failed to send email: {str(e)}')
        import traceback
        logging.error(traceback.format_exc())
```

---

## **Step 5: Update Environment Variables**

Go to **Settings** → **Environment variables** and add these:

### **Database Settings (NO PASSWORD!):**

```
Name: DB_HOST
Value: yourserver.postgres.database.azure.com

Name: DB_NAME  
Value: your_database_name

Name: DB_USER
Value: dataplatform
(This must match your Function App name exactly!)

Name: DB_TABLE
Value: your_table_name
```

### **Email Settings (same as before):**

```
Name: SMTP_SERVER
Value: smtp.office365.com

Name: SMTP_PORT
Value: 587

Name: SMTP_USER
Value: your-email@company.com

Name: SMTP_PASSWORD
Value: your-password

Name: ALERT_EMAIL
Value: admin@company.com
```

Click **Apply** to save.

---

## **Step 6: Test the Connection**

Create a simple test function first to verify the Managed Identity works:

```python
import azure.functions as func
import logging
import os
import sys
import subprocess

def install_if_missing(package, import_name=None):
    if import_name is None:
        import_name = package.replace('-', '_')
    try:
        __import__(import_name)
        return True
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package])
        return True

app = func.FunctionApp()

@app.schedule(schedule="0 */30 * * * *", arg_name="myTimer", run_on_startup=False)
def test_managed_identity(myTimer: func.TimerRequest) -> None:
    logging.info('Testing Managed Identity setup...')
    
    install_if_missing('azure-identity')
    
    try:
        from azure.identity import DefaultAzureCredential
        
        logging.info('✓ azure-identity imported')
        
        # Test getting token
        credential = DefaultAzureCredential()
        token_response = credential.get_token(
            "https://ossrdbms-aad.database.windows.net/.default"
        )
        
        logging.info('✓ Token obtained successfully!')
        logging.info(f'  Token length: {len(token_response.token)} chars')
        logging.info(f'  Expires in: {token_response.expires_on}')
        
        # Test database connection
        install_if_missing('psycopg2-binary', 'psycopg2')
        import psycopg2
        
        db_host = os.environ.get('DB_HOST')
        db_name = os.environ.get('DB_NAME')
        db_user = os.environ.get('DB_USER')
        
        logging.info(f'Connecting to: {db_host}')
        logging.info(f'Database: {db_name}')
        logging.info(f'User: {db_user}')
        
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=token_response.token,
            sslmode='require'
        )
        
        logging.info('✓ Database connection successful!')
        
        cur = conn.cursor()
        cur.execute('SELECT version()')
        version = cur.fetchone()[0]
        logging.info(f'✓ PostgreSQL version: {version}')
        
        cur.close()
        conn.close()
        
        logging.info('✓ All tests passed!')
        
    except Exception as e:
        logging.error(f'✗ Test failed: {str(e)}')
        import traceback
        logging.error(traceback.format_exc())
```

---

## **Troubleshooting**

### If you get "password authentication failed for user"

This means the PostgreSQL user wasn't created properly. Run this SQL as your Azure AD admin:

```sql
-- Connect as your Azure AD admin
CREATE ROLE "dataplatform" WITH LOGIN;
GRANT CONNECT ON DATABASE your_db TO "dataplatform";
GRANT USAGE ON SCHEMA public TO "dataplatform";
GRANT SELECT ON your_table TO "dataplatform";
```

### If you get "DefaultAzureCredential failed to retrieve token"

- Make sure System Assigned Identity is **ON**
- Restart the Function App
- Check that the Function App name matches the PostgreSQL role name

### If you get "no pg_hba.conf entry for host"

- In PostgreSQL → **Networking** → **Firewall rules**
- Add rule: `0.0.0.0` to `0.0.0.0` for Azure services

---

## **Summary of Changes**

**Old way (insecure):**
```
DB_CONNECTION_STRING = "host=... user=admin password=SecretPass123 ..."
```

**New way (secure with Managed Identity):**
```
DB_HOST = "server.postgres.database.azure.com"
DB_NAME = "mydb"
DB_USER = "dataplatform"  # Function App name
# NO PASSWORD! Token is fetched automatically
```

**Benefits:**
- ✅ No passwords stored anywhere
- ✅ Tokens rotate automatically
- ✅ Audit trail in Azure AD
- ✅ Compliant with security best practices
- ✅ No credential management needed

---

**Ready to set this up?** Let me know if you need help with any specific step!
