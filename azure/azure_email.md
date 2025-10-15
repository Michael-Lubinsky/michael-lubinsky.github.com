You don’t need SMTP at all. Use one of these:

---

# Option A — SendGrid (fastest)

1. Add to `requirements.txt`:

```
sendgrid
```

2. In your Function App “Configuration” (App Settings), add:

* `SENDGRID_API_KEY = <your key>`
* `ALERT_TO = alice@example.com,bob@example.com`
* `ALERT_FROM = alerts@your-domain.com` (a verified sender in SendGrid)

3. Helper:

```python
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

def send_email_sendgrid(subject: str, body: str, to_csv: str = None):
    sg = SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
    msg = Mail(
        from_email=os.environ.get("ALERT_FROM", "alerts@no-reply.local"),
        to_emails=(to_csv or os.environ["ALERT_TO"]).split(","),
        subject=subject,
        plain_text_content=body,
    )
    sg.send(msg)
```

Call it:

```python
send_email_sendgrid("Postgres alert", "rows in last 6h < 10 for events.pttreceive")
```

---

# Option B — Microsoft Graph via Managed Identity (no API keys)

Good for M365 shops; no SMTP needed.

## One-time tenant setup (admin):

1. **Enable system-assigned managed identity** on the Function App.
2. In Entra ID → **Enterprise applications** → your Function’s managed identity:

   * Assign **Application permission**: `Mail.Send` (and `Mail.Send.Shared` if sending from a shared mailbox).
   * Click **Grant admin consent**.

*(With application permissions you send as a specific mailbox using `/users/{user}/sendMail`.)*

## Code

`requirements.txt`:

```
azure-identity
requests
```

Helper:

```python
import os, requests, json
from azure.identity import DefaultAzureCredential

GRAPH_SCOPE = "https://graph.microsoft.com/.default"
GRAPH_BASE  = "https://graph.microsoft.com/v1.0"

def _graph_token():
    cred = DefaultAzureCredential()
    return cred.get_token(GRAPH_SCOPE).token

def send_email_graph(subject: str, body: str, to_list: list[str], sender_upn: str):
    """
    sender_upn: the mailbox to send *as* (e.g. 'alerts@yourdomain.com' or a shared mailbox UPN)
    Requires app permission Mail.Send (and Mail.Send.Shared for shared mailboxes).
    """
    token = _graph_token()
    url = f"{GRAPH_BASE}/users/{sender_upn}/sendMail"
    payload = {
        "message": {
            "subject": subject,
            "body": { "contentType": "Text", "content": body },
            "toRecipients": [{"emailAddress": {"address": a}} for a in to_list],
        },
        "saveToSentItems": True
    }
    r = requests.post(url, headers={"Authorization": f"Bearer {token}",
                                    "Content-Type": "application/json"},
                      data=json.dumps(payload), timeout=15)
    if r.status_code not in (202, 200):
        raise RuntimeError(f"Graph sendMail failed: {r.status_code} {r.text}")
```

Call it:

```python
send_email_graph(
    subject="Postgres alert",
    body="rows in last 6h < 10 for events.pttreceive",
    to_list=os.environ["ALERT_TO"].split(","),
    sender_upn=os.environ.get("ALERT_FROM_UPN", "alerts@yourdomain.com"),
)
```

Set app settings:

* `ALERT_TO = alice@example.com,bob@example.com`
* `ALERT_FROM_UPN = alerts@yourdomain.com`  (a mailbox in your tenant)

---

# Which should you pick?

* **SendGrid**: quickest to wire up; needs an API key and a verified sender.
* **Microsoft Graph + Managed Identity**: no secrets; needs one-time admin consent for `Mail.Send`.

If you tell me which route you prefer, I’ll drop in the exact function call inside your timer function (with your env var names) so you can copy-paste.






# Options to send email from Azure Functions **without needing SMTP credentials**. Let me show you the easiest ones:

---

## **Option 1: Azure Communication Services (Recommended - Native Azure)**

This is Microsoft's official email service for Azure, and it integrates perfectly with Azure Functions.

### **Setup Steps:**

#### **Step 1: Create Azure Communication Services**

1. In Azure Portal, search for **"Communication Services"**
2. Click **Create**
3. Fill in:
   - **Resource group**: `move` (same as your Function App)
   - **Name**: `dataplatform-comms`
   - **Region**: Same as your Function App
4. Click **Review + Create** → **Create**

#### **Step 2: Add Email Communication Service**

1. Go to your Communication Services resource
2. In the left sidebar, click **Email** → **Email Services**
3. Click **Create Email Service**
4. Fill in:
   - **Name**: `dataplatform-email`
   - **Region**: Same region
5. Click **Review + Create** → **Create**

#### **Step 3: Set Up a Domain**

You have two options:

##### **Option A: Use Azure Managed Domain (Easiest - Free)**

1. Go to your Email Service → **Provision domains**
2. Click **Add domain** → **Azure Managed Domain**
3. Azure will give you a free domain like: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.azurecomm.net`
4. Click **Add**
5. Wait 2-5 minutes for provisioning

##### **Option B: Use Your Custom Domain**

If you own a domain, you can configure it (requires DNS changes).

#### **Step 4: Connect Email Service to Communication Service**

1. Go to your Communication Services resource
2. Click **Email** → **Domains**
3. Click **Connect domain**
4. Select the email domain you just created
5. Click **Connect**

#### **Step 5: Get Connection String**

1. In Communication Services resource
2. Click **Settings** → **Keys**
3. Copy the **Connection string** (Primary or Secondary)
4. It looks like: `endpoint=https://...;accesskey=...`

#### **Step 6: Add to Function App Configuration**

1. Go to your Function App
2. **Settings** → **Environment variables**
3. Add:
   ```
   Name: COMMUNICATION_SERVICES_CONNECTION_STRING
   Value: <paste the connection string>
   ```

#### **Step 7: Update Function Code**

```python
import azure.functions as func
import logging
import os
import json

app = func.FunctionApp()

@app.route(route="check-database", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
def check_database_manual(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('HTTP trigger - checking database records...')
    
    try:
        result = perform_database_check()
        return func.HttpResponse(result, status_code=200, mimetype="application/json")
    except Exception as e:
        logging.error(f'Error: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def perform_database_check():
    """Database checking logic"""
    import psycopg2
    from azure.identity import DefaultAzureCredential
    
    # Your existing database code...
    # (Get token, connect, query, etc.)
    
    # Simulate check
    record_count = 5  # Replace with actual query result
    
    # Check threshold
    status = "OK" if record_count >= 10 else "ALERT"
    
    result = {
        "status": status,
        "record_count": record_count,
        "threshold": 10,
        "timestamp": func.datetime.utcnow().isoformat()
    }
    
    # Send alert if needed
    if record_count < 10:
        logging.warning(f'Alert: {record_count} < 10')
        send_email_alert_acs(record_count)
        result["alert_sent"] = True
    else:
        result["alert_sent"] = False
    
    return json.dumps(result, indent=2)


def send_email_alert_acs(record_count):
    """Send email using Azure Communication Services"""
    from azure.communication.email import EmailClient
    
    try:
        # Get connection string from environment
        connection_string = os.environ.get('COMMUNICATION_SERVICES_CONNECTION_STRING')
        
        if not connection_string:
            raise Exception('COMMUNICATION_SERVICES_CONNECTION_STRING not configured')
        
        # Create email client
        email_client = EmailClient.from_connection_string(connection_string)
        
        # Sender address - use the Azure managed domain
        # Format: DoNotReply@xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.azurecomm.net
        sender_address = os.environ.get('SENDER_EMAIL', 'DoNotReply@<YOUR_DOMAIN>.azurecomm.net')
        
        # Recipient
        recipient_address = os.environ.get('ALERT_EMAIL', 'admin@company.com')
        
        # Compose message
        message = {
            "senderAddress": sender_address,
            "recipients": {
                "to": [{"address": recipient_address}]
            },
            "content": {
                "subject": f"⚠️ Database Alert: Only {record_count} Records",
                "plainText": f"""
Database Alert
==============

⚠️ Record count is below threshold!

Current count: {record_count}
Threshold:     10
Status:        CRITICAL

Please investigate immediately.

---
Automated alert from Azure Functions
Time: {func.datetime.utcnow()} UTC
                """
            }
        }
        
        # Send email
        logging.info(f'Sending email to {recipient_address}...')
        poller = email_client.begin_send(message)
        result = poller.result()
        
        logging.info(f'✓ Email sent! Message ID: {result["id"]}')
        
    except Exception as e:
        logging.error(f'Failed to send email: {str(e)}')
        raise
```

#### **Step 8: Update requirements.txt**

Make sure your `requirements.txt` includes:

```txt
azure-functions
psycopg2-binary
azure-identity
azure-communication-email
```

#### **Step 9: Add Sender Email to Configuration**

1. Go to your Email Service in Azure Portal
2. Note your sender domain (e.g., `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.azurecomm.net`)
3. Add to Function App environment variables:
   ```
   Name: SENDER_EMAIL
   Value: DoNotReply@xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.azurecomm.net
   
   Name: ALERT_EMAIL
   Value: your-actual-email@company.com
   ```

---

## **Option 2: SendGrid (Popular, Easy, Free Tier)**

SendGrid is a popular email service with a free tier (100 emails/day).

### **Setup Steps:**

#### **Step 1: Create SendGrid Account**

1. Go to https://sendgrid.com
2. Sign up for a free account
3. Verify your email

#### **Step 2: Create API Key**

1. In SendGrid dashboard, go to **Settings** → **API Keys**
2. Click **Create API Key**
3. Name it: `azure-function-alerts`
4. Permissions: **Full Access** (or **Mail Send** only)
5. Click **Create & View**
6. **Copy the API key** (you won't see it again!)

#### **Step 3: Verify Sender Email**

1. Go to **Settings** → **Sender Authentication**
2. Click **Verify a Single Sender**
3. Fill in your email details
4. Verify the email (check your inbox)

#### **Step 4: Add to Function App**

Add to Function App environment variables:

```
Name: SENDGRID_API_KEY
Value: SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Name: SENDER_EMAIL
Value: your-verified-email@company.com

Name: ALERT_EMAIL
Value: recipient@company.com
```

#### **Step 5: Update Function Code**

```python
def send_email_alert_sendgrid(record_count):
    """Send email using SendGrid"""
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, Content
    
    try:
        api_key = os.environ.get('SENDGRID_API_KEY')
        sender_email = os.environ.get('SENDER_EMAIL')
        recipient_email = os.environ.get('ALERT_EMAIL')
        
        if not all([api_key, sender_email, recipient_email]):
            raise Exception('SendGrid configuration missing')
        
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        
        from_email = Email(sender_email)
        to_email = To(recipient_email)
        subject = f"⚠️ Database Alert: Only {record_count} Records"
        content = Content("text/plain", f"""
Database Alert
==============

⚠️ Record count is below threshold!

Current count: {record_count}
Threshold:     10

Please investigate immediately.
        """)
        
        mail = Mail(from_email, to_email, subject, content)
        
        response = sg.client.mail.send.post(request_body=mail.get())
        
        logging.info(f'✓ Email sent via SendGrid. Status: {response.status_code}')
        
    except Exception as e:
        logging.error(f'SendGrid error: {str(e)}')
        raise
```

#### **Step 6: Update requirements.txt**

```txt
azure-functions
psycopg2-binary
azure-identity
sendgrid
```

---

## **Option 3: Microsoft Graph API (If You Have Microsoft 365)**

If your company uses Microsoft 365, you can send email through your work account.

### **Setup Steps:**

#### **Step 1: Register App in Azure AD**

1. Azure Portal → **Microsoft Entra ID** (Azure AD)
2. **App registrations** → **New registration**
3. Name: `dataplatform-email`
4. Click **Register**

#### **Step 2: Add API Permissions**

1. In your app registration, go to **API permissions**
2. Click **Add a permission** → **Microsoft Graph**
3. Select **Application permissions**
4. Search and add: `Mail.Send`
5. Click **Grant admin consent**

#### **Step 3: Create Client Secret**

1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Description: `function-email`
4. Expires: 24 months
5. Click **Add**
6. **Copy the secret value** (you won't see it again!)

#### **Step 4: Get Application ID**

1. Go to **Overview**
2. Copy the **Application (client) ID**
3. Copy the **Directory (tenant) ID**

#### **Step 5: Add to Function App**

```
Name: AZURE_CLIENT_ID
Value: <Application ID>

Name: AZURE_TENANT_ID
Value: <Tenant ID>

Name: AZURE_CLIENT_SECRET
Value: <Client secret>

Name: SENDER_EMAIL
Value: your-work-email@company.com

Name: ALERT_EMAIL
Value: recipient@company.com
```

#### **Step 6: Update Function Code**

```python
def send_email_alert_graph(record_count):
    """Send email using Microsoft Graph API"""
    import requests
    from azure.identity import ClientSecretCredential
    
    try:
        # Get credentials
        tenant_id = os.environ.get('AZURE_TENANT_ID')
        client_id = os.environ.get('AZURE_CLIENT_ID')
        client_secret = os.environ.get('AZURE_CLIENT_SECRET')
        sender_email = os.environ.get('SENDER_EMAIL')
        recipient_email = os.environ.get('ALERT_EMAIL')
        
        # Get access token
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
        token = credential.get_token('https://graph.microsoft.com/.default')
        
        # Prepare email
        email_msg = {
            "message": {
                "subject": f"⚠️ Database Alert: Only {record_count} Records",
                "body": {
                    "contentType": "Text",
                    "content": f"""
Database Alert
==============

⚠️ Record count is below threshold!

Current count: {record_count}
Threshold:     10

Please investigate immediately.
                    """
                },
                "toRecipients": [
                    {"emailAddress": {"address": recipient_email}}
                ]
            },
            "saveToSentItems": "false"
        }
        
        # Send email
        response = requests.post(
            f'https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail',
            headers={
                'Authorization': f'Bearer {token.token}',
                'Content-Type': 'application/json'
            },
            json=email_msg
        )
        
        if response.status_code == 202:
            logging.info('✓ Email sent via Microsoft Graph')
        else:
            logging.error(f'Graph API error: {response.status_code} - {response.text}')
            
    except Exception as e:
        logging.error(f'Microsoft Graph error: {str(e)}')
        raise
```

---

## **Comparison Table**

| Service | Free Tier | Setup Complexity | Best For |
|---------|-----------|-----------------|----------|
| **Azure Communication Services** | 100 emails/month | Medium | Azure-native solution |
| **SendGrid** | 100 emails/day | Easy | Quick setup, popular |
| **Microsoft Graph** | Unlimited | Hard | Microsoft 365 users |

---

## **My Recommendation: Start with SendGrid**

**SendGrid is the easiest to set up quickly:**

1. ✅ Sign up → 5 minutes
2. ✅ Get API key → 2 minutes
3. ✅ Add to Function App → 2 minutes
4. ✅ Update code → 5 minutes
5. ✅ **Total: ~15 minutes**

**Then migrate to Azure Communication Services later for a fully Azure-native solution.**

---

## **Quick Start: SendGrid (Step-by-Step)**

1. **Go to https://sendgrid.com** → Sign up
2. **Verify your email**
3. **Settings** → **API Keys** → **Create API Key** → Copy it
4. **Settings** → **Sender Authentication** → **Verify a Single Sender** → Use your email
5. **Function App** → **Environment variables** → Add:
   - `SENDGRID_API_KEY`
   - `SENDER_EMAIL`
   - `ALERT_EMAIL`
6. **Update requirements.txt** → Add `sendgrid`
7. **Update function code** → Use `send_email_alert_sendgrid()` function
8. **Restart Function App**
9. **Test!**

---

**Which option do you want to try? I recommend SendGrid for the quickest solution!** Let me know and I can provide more detailed steps for your choice.
