## Creating and deploying the simplest Azure Function using Python. 


```
michael-weavix-testing $ func azure functionapp publish Michael
Functions in Michael:
    write_file_to_adls_managed_identity - [timerTrigger]
```

### 1. **Prerequisites:**
```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Install Azure CLI (if not already installed)
# curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login
```

### 2. **Create Project Structure:**
```bash
# Create project directory
mkdir my-azure-function
cd my-azure-function

# Initialize function project
func init --python

# Create the function files (copy the content from artifacts above)
```

**Create these files:**
- `function_app.py` (main function code)
- `requirements.txt` (dependencies)
- `host.json` (function app configuration)
- `local.settings.json` (local development settings)

### 3. **Test Locally:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
func start

# Test in another terminal
curl "http://localhost:7071/api/hello?name=World"
```

### 4. **Deploy to Azure:**

**Option A: Quick Deploy (Recommended for testing)**
```bash
# Create resource group
az group create --name rg-my-function --location "East US"

# Create storage account (required for Azure Functions)
az storage account create \
  --name mystorageaccount$(date +%s) \
  --resource-group rg-my-function \
  --location "East US" \
  --sku Standard_LRS

# Create function app
az functionapp create \
  --resource-group rg-my-function \
  --consumption-plan-location "East US" \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name my-function-app-$(date +%s) \
  --storage-account mystorageaccount$(date +%s) \
  --os-type Linux

# Deploy function
func azure functionapp publish my-function-app-XXXXX
```

**Option B: Using VS Code (Easiest)**
1. **Install Azure Functions extension** in VS Code
2. **Sign in to Azure** in VS Code
3. **Open your project folder**
4. **Press F1** → "Azure Functions: Deploy to Function App"
5. **Follow the prompts**

### 5. **Test Deployed Function:**
```bash
# Your function will be available at:
# https://your-function-app.azurewebsites.net/api/hello?name=World

# Test with curl
curl "https://your-function-app.azurewebsites.net/api/hello?name=Azure"
```

## Alternative: Even Simpler Version

If you want the absolute minimum:## Quick Commands Summary:

```bash
# 1. Create project
mkdir my-function && cd my-function
func init --python

# 2. Create function_app.py (copy from artifacts)

# 3. Test locally  
func start

# 4. Deploy (replace with your app name)
az group create --name rg-function --location "East US"
az functionapp create --resource-group rg-function --consumption-plan-location "East US" --runtime python --functions-version 4 --name my-unique-function-app --storage-account mystorageaccount123 --os-type Linux
func azure functionapp publish my-unique-function-app
```

#### Tips:

- **Function app names must be globally unique**
- **Storage account names must be globally unique and lowercase**
- **Use consumption plan for cost-effective testing**
- **Functions timeout after 5 minutes by default**
- **Check Azure portal for logs and monitoring**

The function will be accessible at: `https://your-function-app.azurewebsites.net/api/hello`

 ### function_app.py - Minimal version
 ```python
import azure.functions as func

app = func.FunctionApp()

@app.function_name(name="hello")
@app.route(route="hello")
def main(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("Hello from Azure Functions!", status_code=200)
```


That's because the two Function Apps are using **different hosting models**:

## Function App Hosting Models:

**"michael-weavix-testing"** (has Deployment settings) = **Consumption Plan or App Service Plan**
- Traditional Azure Functions
- Has deployment slots, continuous deployment options
- More configuration options

**"Michael"** (no Deployment settings) = **Flex Consumption Plan** (newer model)
- Simplified deployment model
- Uses different deployment methods
- More streamlined, fewer configuration options

## To Deploy to Either Function App:

### Option 1: Deploy to "michael-weavix-testing" (Traditional)

You can use the **Deployment Center** in the portal:

1. **Click on "michael-weavix-testing"**
2. **Go to "Deployment settings" (or "Deployment Center")**
3. **Choose deployment source:**
   - **Local Git** (deploy from your local machine)
   - **GitHub** (if your code is on GitHub)
   - **ZIP Deploy** (upload a ZIP file)

### Option 2: Deploy to "Michael" (Flex Consumption)

Use Azure Functions Core Tools:

```bash
# Deploy using CLI (this should work for both types)
func azure functionapp publish Michael

# Or deploy to the other one
func azure functionapp publish michael-weavix-testing
```

### Option 3: Deploy via ZIP (Works for Both)

```bash
# Create a ZIP of your function project
zip -r myfunction.zip . -x "*.git*" "*.vscode*" "__pycache__*"

# Deploy ZIP via CLI
az functionapp deployment source config-zip \
  --resource-group <RESOURCE_GROUP_NAME> \
  --name michael-weavix-testing \
  --src myfunction.zip

# Or for the other function app
az functionapp deployment source config-zip \
  --resource-group <RESOURCE_GROUP_NAME> \
  --name Michael \
  --src myfunction.zip
```

## Recommended Approach:

**Try the CLI deployment first** (it works for both types):

```bash
# Navigate to your function project directory
cd /path/to/your/function/project

# Deploy to whichever function app you prefer
func azure functionapp publish michael-weavix-testing

# Or
func azure functionapp publish Michael
```

## Check Resource Groups:

First, find out which resource groups these function apps are in:

```bash
az functionapp list --query "[].{name:name, resourceGroup:resourceGroup, kind:kind}" --output table
```

**The "kind" field will tell you the hosting model differences.**

Which function app would you like to deploy to? I'd recommend using `func azure functionapp publish` as it works for both types.

```bash
pwd
/Users/michaellubinsky/code/AZURE_FUNCTION/michael-weavix-testing
func azure functionapp publish Michael
```

result
``` 
Functions in Michael:
    write_file_to_adls_managed_identity - [timerTrigger]
```    

Based on your Azure Function logs, you're encountering authentication issues with Azure Data Lake Storage Gen2 (ADLS Gen2). The `DefaultAzureCredential` is failing to authenticate, and specifically the Managed Identity isn't working as expected.

Here's what's happening and how to fix it:

## Root Cause
The function is trying multiple authentication methods in this order, and all are failing:
1. **EnvironmentCredential** - Environment variables not configured
2. **WorkloadIdentityCredential** - Missing tenant_id, client_id, token_file_path
3. **ManagedIdentityCredential** - No response from IMDS endpoint (this is the key issue)
4. Other credentials (VS Code, Azure CLI, PowerShell) - Not available in Azure Functions environment

## Solutions

### 1. Enable System-Assigned Managed Identity
In the Azure Portal:
1. Go to your Function App
2. Navigate to **Identity** in the left menu
3. Under **System assigned**, set Status to **On**
4. Click **Save**

### 2. Grant ADLS Gen2 Permissions
After enabling the managed identity:
1. Go to your ADLS Gen2 storage account
2. Navigate to **Access Control (IAM)**
3. Click **Add role assignment**
4. Assign the **Storage Blob Data Contributor** role to your Function App's managed identity

### 3. Verify Your Python Code
Make sure your function code is using the correct authentication pattern:

```python
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

# This should work once managed identity is properly configured
credential = DefaultAzureCredential()
service_client = DataLakeServiceClient(
    account_url="https://yourstorageaccount.dfs.core.windows.net",
    credential=credential
)
```

### 4. Alternative: Use Connection String
If managed identity continues to fail, you can temporarily use a connection string stored in Application Settings:

```python
from azure.storage.filedatalake import DataLakeServiceClient
import os

# Add connection string to Function App Configuration
connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
service_client = DataLakeServiceClient.from_connection_string(connection_string)
```

### 5. Check Function App Configuration
Verify in your Function App's **Configuration** section that you don't have conflicting environment variables that might interfere with authentication.

The most likely fix is enabling the system-assigned managed identity and granting it proper permissions to your ADLS Gen2 storage account. Let me know if you need help with any of these steps!

The "Add role assignment" being greyed out means you don't have sufficient permissions to assign roles on the storage account. Here are several ways to resolve this:

## Solution Options

### 1. Check Your Current Permissions
You need one of these roles on the storage account to assign roles:
- **Owner**
- **User Access Administrator** 
- **Role Based Access Control Administrator**

### 2. Contact Your Azure Administrator
If you don't have these permissions, ask someone who has **Owner** or **User Access Administrator** rights on the storage account (or subscription) to:

1. Go to the ADLS Gen2 storage account
2. Navigate to **Access Control (IAM)**
3. Click **Add role assignment**
4. Select **Storage Blob Data Contributor** role
5. Assign it to your Function App's managed identity

### 3. Use Azure CLI (if you have appropriate permissions)
If you have permissions via Azure CLI but not the portal:

```bash
# Get your function app's managed identity principal ID
az functionapp identity show --name <your-function-app-name> --resource-group <your-resource-group>

# Assign the role (replace the placeholders)
az role assignment create \
  --assignee <managed-identity-principal-id> \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.Storage/storageAccounts/<storage-account-name>"
```

### 4. Request Elevated Permissions
Ask your Azure administrator to temporarily grant you **User Access Administrator** role on the storage account, then you can assign the role yourself.

### 5. Alternative: Use Access Keys (Less Secure)
As a temporary workaround, you can use storage account access keys:

1. Go to your storage account
2. Navigate to **Security + networking** > **Access keys**
3. Copy one of the connection strings
4. Add it to your Function App's **Configuration** > **Application settings** as `AZURE_STORAGE_CONNECTION_STRING`
5. Modify your Python code to use the connection string instead of managed identity

The most secure long-term solution is still option 2 - having an administrator assign the proper role to your Function App's managed identity.  




# For Azure Functions connecting to Azure Database for PostgreSQL with Azure AD authentication, here are the best practices:

## Recommended Approach: Use Managed Identity with Token Refresh

### 1. Enable System-Assigned Managed Identity
(You may have already done this for ADLS Gen2)
- Go to your Function App → **Identity** → Enable **System assigned**

### 2. Grant Database Permissions
Connect to your PostgreSQL database and create a user for the managed identity:

```sql
-- Connect as an admin user first
SET aad_validate_oids_in_tenant = off;

-- Create user for your Function App's managed identity
CREATE ROLE "your-function-app-name" WITH LOGIN PASSWORD NULL IN ROLE azure_ad_user;

-- Grant necessary permissions
GRANT CONNECT ON DATABASE weavix TO "your-function-app-name";
GRANT USAGE ON SCHEMA public TO "your-function-app-name";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "your-function-app-name";
```

### 3. Python Code with Token Refresh

```python
import azure.functions as func
import psycopg2
import logging
from azure.identity import DefaultAzureCredential
from datetime import datetime, timedelta
import threading
import os

# Global variables for connection pooling and token management
_token_cache = {}
_token_lock = threading.Lock()
_credential = None

def get_credential():
    """Get or create the DefaultAzureCredential instance"""
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential

def get_postgres_token():
    """Get a fresh PostgreSQL access token, with caching"""
    global _token_cache
    
    with _token_lock:
        now = datetime.now()
        
        # Check if we have a valid cached token (refresh 10 minutes before expiry)
        if ('token' in _token_cache and 
            'expires_at' in _token_cache and 
            _token_cache['expires_at'] > now + timedelta(minutes=10)):
            return _token_cache['token']
        
        # Get fresh token
        try:
            credential = get_credential()
            token_response = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
            
            # Cache the token
            _token_cache['token'] = token_response.token
            _token_cache['expires_at'] = datetime.fromtimestamp(token_response.expires_on)
            
            logging.info(f"Retrieved new PostgreSQL token, expires at: {_token_cache['expires_at']}")
            return token_response.token
            
        except Exception as e:
            logging.error(f"Failed to get PostgreSQL access token: {str(e)}")
            raise

def get_postgres_connection():
    """Get a PostgreSQL connection using managed identity"""
    
    # Get configuration from environment variables
    pg_host = os.environ.get('PG_HOST', 'weavix-dev-pg.postgres.database.azure.com')
    pg_database = os.environ.get('PG_DATABASE', 'weavix')
    pg_user = os.environ.get('PG_USER')  # Should be your Function App name
    
    if not pg_user:
        raise ValueError("PG_USER environment variable must be set to your Function App name")
    
    # Get fresh access token
    token = get_postgres_token()
    
    try:
        conn = psycopg2.connect(
            host=pg_host,
            database=pg_database,
            user=pg_user,
            password=token,
            sslmode='require'
        )
        return conn
    except Exception as e:
        logging.error(f"Failed to connect to PostgreSQL: {str(e)}")
        raise

# Example Azure Function
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    try:
        # Get database connection
        conn = get_postgres_connection()
        
        # Example database operation
        with conn.cursor() as cursor:
            cursor.execute("SELECT version()")
            result = cursor.fetchone()
            logging.info(f"PostgreSQL version: {result[0]}")
        
        conn.close()
        
        return func.HttpResponse(
            f"Successfully connected to PostgreSQL: {result[0]}",
            status_code=200
        )
        
    except Exception as e:
        logging.error(f"Error in function execution: {str(e)}")
        return func.HttpResponse(
            f"Error: {str(e)}",
            status_code=500
        )

```

### 4. Alternative: Connection Pool with Auto-Refresh

For high-throughput applications, consider using a connection pool:### 5. Environment Variables Setup

Add these to your Function App's **Configuration** → **Application settings**:

- `PG_HOST`: `weavix-dev-pg.postgres.database.azure.com`
- `PG_DATABASE`: `weavix`  
- `PG_USER`: `your-function-app-name` (the exact name of your Function App)

### 6. Requirements.txt

Make sure your `requirements.txt` includes:

```
azure-functions
azure-identity
psycopg2-binary
```

## Key Benefits of This Approach:

1. **Secure**: Uses managed identity, no secrets in code
2. **Auto-refresh**: Tokens are refreshed before expiry
3. **Resilient**: Handles token refresh failures gracefully  
4. **Efficient**: Connection pooling for better performance
5. **No manual token management**: Everything is automatic

## Alternative: Using Connection Strings (Less Recommended)

If you must use traditional connection strings, store them in **Azure Key Vault** and reference them in your Function App settings, but managed identity is the more secure and Azure-native approach.

The first approach (simple token refresh) should work well for most use cases. Use the connection pool approach if you have high-throughput requirements.
