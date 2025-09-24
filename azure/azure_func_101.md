## Creating and deploying the simplest Azure Function using Python. 

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
