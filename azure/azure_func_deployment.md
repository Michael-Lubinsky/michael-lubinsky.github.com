There are several approaches to use your Azure Function in production

## Option 1: Deploy Same Code to Production Resource Group (Recommended)

Create a separate Function App in a **production resource group** with the same code:

### Steps:

**1. Create Production Resource Group:**
```bash
az group create \
    --name production-rg \
    --location eastus
```

**2. Create Production Storage Account:**
```bash
az storage account create \
    --name prodfuncappstorage \
    --resource-group production-rg \
    --location eastus \
    --sku Standard_LRS
```

**3. Create Production Function App:**
```bash
az functionapp create \
    --name my-adls-writer-prod \
    --resource-group production-rg \
    --runtime python \
    --runtime-version 3.13 \
    --functions-version 4 \
    --consumption-plan-location eastus \
    --storage-account prodfuncappstorage \
    --os-type Linux \
    --assign-identity [system]
```

**4. Deploy Your Code to Production:**
```bash
# From your local development directory
func azure functionapp publish my-adls-writer-prod
```

**5. Configure Production Environment Variables:**
```bash
az functionapp config appsettings set \
    --name my-adls-writer-prod \
    --resource-group production-rg \
    --settings \
    "ADLS_ACCOUNT_NAME=prod-storage-account" \
    "ADLS_FILE_SYSTEM=prod-container" \
    "POSTGRES_HOST=prod-db.postgres.azure.com" \
    "POSTGRES_DATABASE=production_db" \
    "POSTGRES_PASSWORD=prod-password"
```

### Architecture:
```
┌─────────────────────────────────────┐
│ TEST Resource Group                 │
├─────────────────────────────────────┤
│ • Function App: my-adls-writer-test │
│ • Storage: testfuncappstorage       │
│ • ADLS: test-data-lake             │
│ • Postgres: test-db                 │
│ • Environment: Development/Testing  │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ PRODUCTION Resource Group           │
├─────────────────────────────────────┤
│ • Function App: my-adls-writer-prod │
│ • Storage: prodfuncappstorage       │
│ • ADLS: prod-data-lake             │
│ • Postgres: prod-db                 │
│ • Environment: Production           │
└─────────────────────────────────────┘
```

**Pros:**
- ✅ Complete isolation between test and prod
- ✅ Different databases and storage accounts
- ✅ Independent scaling and configuration
- ✅ No risk of test changes affecting production

**Cons:**
- ❌ Duplicate infrastructure (more cost)
- ❌ Must deploy to both environments

---

## Option 2: Use Deployment Slots (Staging → Production)

Keep one Function App but use deployment slots:

### Steps:

**1. Create Production Slot (if not exists):**
```bash
az functionapp deployment slot create \
    --name my-adls-writer-func \
    --resource-group test \
    --slot staging
```

**2. Configure Slot-Specific Settings:**

In Azure Portal:
- Go to Function App → **Configuration**
- Set environment variables with **"Deployment slot setting" checked** for:
  - `ADLS_ACCOUNT_NAME`
  - `POSTGRES_HOST`
  - etc.

**3. Deploy to Staging Slot:**
```bash
func azure functionapp publish my-adls-writer-func --slot staging
```

**4. Test Staging:**
```bash
# Test the staging URL
curl https://my-adls-writer-func-staging.azurewebsites.net/api/your-function
```

**5. Swap Staging → Production:**
```bash
az functionapp deployment slot swap \
    --name my-adls-writer-func \
    --resource-group test \
    --slot staging
```

### Architecture:
```
┌────────────────────────────────────────────────┐
│ TEST Resource Group                            │
├────────────────────────────────────────────────┤
│ Function App: my-adls-writer-func              │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │ PRODUCTION SLOT (live traffic)           │ │
│  │ • Code: v2.0                             │ │
│  │ • DB_HOST: prod-db [Sticky]              │ │
│  │ • URL: my-adls-writer-func.azure...net  │ │
│  └──────────────────────────────────────────┘ │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │ STAGING SLOT (testing)                   │ │
│  │ • Code: v2.1 (testing)                   │ │
│  │ • DB_HOST: test-db [Sticky]              │ │
│  │ • URL: ...func-staging.azure...net      │ │
│  └──────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

**Pros:**
- ✅ Single infrastructure to manage
- ✅ Easy swap between staging/production
- ✅ Zero-downtime deployments
- ✅ Can quickly rollback

**Cons:**
- ❌ Test and prod in same resource group
- ❌ Requires careful slot configuration
- ❌ Deployment slots cost extra

---

## Option 3: Move Function App to Production Resource Group

Move the existing Function App from test to production:

```bash
# Move resource to different resource group
az resource move \
    --destination-group production-rg \
    --ids /subscriptions/<subscription-id>/resourceGroups/test/providers/Microsoft.Web/sites/my-adls-writer-func
```

**Pros:**
- ✅ Simple migration

**Cons:**
- ❌ Downtime during move
- ❌ Loses test environment
- ❌ Not recommended

---

## Option 4: Use Environment-Based Configuration (Same Function)

Keep the Function in test resource group but use environment variables to point to production resources:

```bash
# Configure to point to production resources
az functionapp config appsettings set \
    --name my-adls-writer-func \
    --resource-group test \
    --settings \
    "ENVIRONMENT=production" \
    "ADLS_ACCOUNT_NAME=prod-storage" \
    "POSTGRES_HOST=prod-db.postgres.azure.com"
```

**Pros:**
- ✅ Quick and simple

**Cons:**
- ❌ No separation between test and prod
- ❌ Risk of accidental changes to production
- ❌ Not best practice

---

## Recommended Approach: Option 1 (Separate Resource Groups)

## Summary of Recommended Approach:

### Best Practice: Separate Environments

```
TEST Environment (test resource group)
├── Function App: my-adls-writer-test
├── Storage: test-storage
├── ADLS: test-data-lake
└── PostgreSQL: test-db

PRODUCTION Environment (production-rg)
├── Function App: my-adls-writer-prod
├── Storage: prod-storage
├── ADLS: prod-data-lake
└── PostgreSQL: prod-db
```

### Quick Commands:

```bash
# 1. Create production resource group
az group create --name production-rg --location eastus

# 2. Create production function app
az functionapp create \
    --name my-adls-writer-prod \
    --resource-group production-rg \
    --runtime python \
    --os-type Linux \
    --storage-account prodfuncappstorage

# 3. Deploy your code
func azure functionapp publish my-adls-writer-prod

# 4. Configure production settings in Azure Portal
```

This approach gives you:
- ✅ Complete isolation
- ✅ Safe testing environment
- ✅ Production-grade setup
- ✅ Easy rollback options

```bash
#!/bin/bash

# Production Deployment Script for Azure Function
# This script creates a complete production environment

set -e  # Exit on error

# ===========================
# Configuration Variables
# ===========================
SUBSCRIPTION_ID="your-subscription-id"
TEST_RG="test"
PROD_RG="production-rg"
LOCATION="eastus"

# Test Environment
TEST_FUNC_APP="my-adls-writer-test"
TEST_STORAGE="testfuncappstorage"

# Production Environment
PROD_FUNC_APP="my-adls-writer-prod"
PROD_STORAGE="prodfuncappstorage"
PROD_ADLS_ACCOUNT="prodadlsstorage"
PROD_ADLS_CONTAINER="prod-data"
PROD_POSTGRES_HOST="prod-db.postgres.azure.com"
PROD_POSTGRES_DB="production_db"
PROD_POSTGRES_USER="admin_user"
PROD_POSTGRES_PASSWORD="YourSecurePassword123!"

echo "=================================="
echo "Production Environment Setup"
echo "=================================="

# ===========================
# Step 1: Create Production Resource Group
# ===========================
echo ""
echo "Step 1: Creating production resource group..."
az group create \
    --name $PROD_RG \
    --location $LOCATION \
    --subscription $SUBSCRIPTION_ID

echo "✅ Resource group created: $PROD_RG"

# ===========================
# Step 2: Create Production Function App Storage
# ===========================
echo ""
echo "Step 2: Creating production function app storage..."
az storage account create \
    --name $PROD_STORAGE \
    --resource-group $PROD_RG \
    --location $LOCATION \
    --sku Standard_LRS \
    --kind StorageV2

echo "✅ Function app storage created: $PROD_STORAGE"

# ===========================
# Step 3: Create Production Function App
# ===========================
echo ""
echo "Step 3: Creating production function app..."
az functionapp create \
    --name $PROD_FUNC_APP \
    --resource-group $PROD_RG \
    --runtime python \
    --runtime-version 3.13 \
    --functions-version 4 \
    --consumption-plan-location $LOCATION \
    --storage-account $PROD_STORAGE \
    --os-type Linux \
    --assign-identity [system]

echo "✅ Function app created: $PROD_FUNC_APP"

# ===========================
# Step 4: Get Function App Managed Identity
# ===========================
echo ""
echo "Step 4: Getting managed identity..."
PRINCIPAL_ID=$(az functionapp identity show \
    --name $PROD_FUNC_APP \
    --resource-group $PROD_RG \
    --query principalId \
    --output tsv)

echo "✅ Managed Identity Principal ID: $PRINCIPAL_ID"

# ===========================
# Step 5: Create or Configure Production ADLS Gen2
# ===========================
echo ""
echo "Step 5: Setting up production ADLS Gen2..."

# Check if ADLS account exists
if az storage account show --name $PROD_ADLS_ACCOUNT --resource-group $PROD_RG &>/dev/null; then
    echo "ADLS account already exists: $PROD_ADLS_ACCOUNT"
else
    echo "Creating ADLS Gen2 storage account..."
    az storage account create \
        --name $PROD_ADLS_ACCOUNT \
        --resource-group $PROD_RG \
        --location $LOCATION \
        --sku Standard_LRS \
        --kind StorageV2 \
        --hierarchical-namespace true
    
    echo "✅ ADLS Gen2 account created: $PROD_ADLS_ACCOUNT"
fi

# Create container if it doesn't exist
echo "Creating ADLS container..."
az storage fs create \
    --name $PROD_ADLS_CONTAINER \
    --account-name $PROD_ADLS_ACCOUNT \
    --auth-mode login || echo "Container may already exist"

echo "✅ ADLS container configured: $PROD_ADLS_CONTAINER"

# ===========================
# Step 6: Assign RBAC Permissions
# ===========================
echo ""
echo "Step 6: Assigning RBAC permissions..."

# Get ADLS storage account resource ID
ADLS_SCOPE=$(az storage account show \
    --name $PROD_ADLS_ACCOUNT \
    --resource-group $PROD_RG \
    --query id \
    --output tsv)

# Assign Storage Blob Data Contributor role
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Storage Blob Data Contributor" \
    --scope $ADLS_SCOPE

echo "✅ RBAC permissions assigned"

# ===========================
# Step 7: Configure Environment Variables
# ===========================
echo ""
echo "Step 7: Configuring environment variables..."

az functionapp config appsettings set \
    --name $PROD_FUNC_APP \
    --resource-group $PROD_RG \
    --settings \
    "ENVIRONMENT=production" \
    "ADLS_ACCOUNT_NAME=$PROD_ADLS_ACCOUNT" \
    "ADLS_FILE_SYSTEM=$PROD_ADLS_CONTAINER" \
    "POSTGRES_HOST=$PROD_POSTGRES_HOST" \
    "POSTGRES_DATABASE=$PROD_POSTGRES_DB" \
    "POSTGRES_USER=$PROD_POSTGRES_USER" \
    "POSTGRES_PASSWORD=$PROD_POSTGRES_PASSWORD" \
    "POSTGRES_PORT=5432"

echo "✅ Environment variables configured"

# ===========================
# Step 8: Deploy Function Code
# ===========================
echo ""
echo "Step 8: Deploying function code..."
echo "Run this command from your function directory:"
echo ""
echo "  func azure functionapp publish $PROD_FUNC_APP"
echo ""
echo "Or use this script to deploy:"

cat << 'EOF' > deploy-to-production.sh
#!/bin/bash
# Deploy to production
cd /path/to/your/function/code
func azure functionapp publish my-adls-writer-prod
EOF

chmod +x deploy-to-production.sh
echo "✅ Created deploy-to-production.sh script"

# ===========================
# Step 9: Summary
# ===========================
echo ""
echo "=================================="
echo "Deployment Summary"
echo "=================================="
echo "Production Resource Group: $PROD_RG"
echo "Function App Name: $PROD_FUNC_APP"
echo "Function App URL: https://${PROD_FUNC_APP}.azurewebsites.net"
echo "ADLS Account: $PROD_ADLS_ACCOUNT"
echo "ADLS Container: $PROD_ADLS_CONTAINER"
echo ""
echo "Next Steps:"
echo "1. Deploy your function code:"
echo "   func azure functionapp publish $PROD_FUNC_APP"
echo ""
echo "2. Test the production endpoint:"
echo "   curl https://${PROD_FUNC_APP}.azurewebsites.net/api/your-function"
echo ""
echo "3. Monitor logs:"
echo "   az functionapp log tail --name $PROD_FUNC_APP --resource-group $PROD_RG"
echo ""
echo "=================================="

# ===========================
# Optional: Create Deployment Pipeline
# ===========================
echo ""
echo "Would you like to create a GitHub Actions deployment pipeline? (y/n)"
read -r CREATE_PIPELINE

if [[ $CREATE_PIPELINE == "y" ]]; then
    echo "Creating GitHub Actions workflow..."
    
    mkdir -p .github/workflows
    
    cat > .github/workflows/deploy-production.yml << EOF
name: Deploy to Production

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.13'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Deploy to Azure Functions
      uses: Azure/functions-action@v1
      with:
        app-name: $PROD_FUNC_APP
        package: .
        publish-profile: \${{ secrets.AZURE_FUNCTIONAPP_PUBLISH_PROFILE }}
EOF
    
    echo "✅ Created .github/workflows/deploy-production.yml"
    echo ""
    echo "To use this workflow:"
    echo "1. Get publish profile:"
    echo "   az functionapp deployment list-publishing-profiles --name $PROD_FUNC_APP --resource-group $PROD_RG --xml"
    echo ""
    echo "2. Add it as GitHub secret: AZURE_FUNCTIONAPP_PUBLISH_PROFILE"
fi

echo ""
echo "Setup complete! 🎉"
```
