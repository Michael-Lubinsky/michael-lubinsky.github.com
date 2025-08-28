# Azure Data Lake Storage

az storage fs

You can see the contents of an ADLS Gen2 folder using the Azure CLI with a specific set of commands from the `az storage fs` group. 

This command group is designed to work with the hierarchical namespace of ADLS Gen2.

-----

### Listing Folder Contents

The primary command to list the contents of a directory (or "file system" in ADLS terminology) is `az storage fs ls`.

To see the contents of a specific folder, use this syntax:

```bash
az storage fs ls --account-name <account-name> --file-system <file-system-name> --path <folder-path>
```

Let's break down the parameters:

  * **`--account-name`**: The name of your Azure Data Lake Storage Gen2 account (e.g., `weavixcheckpointsdevsa` from your script).
  * **`--file-system`**: The name of the container or file system. This is the top-level directory (e.g., `adls`).
  * **`--path`**: The path to the folder you want to inspect, relative to the file system root.

For example, based on the `folderPath` in your Node.js script, you could use the following command to list the files in a specific hour's folder:

```bash
az storage fs ls --account-name weavixcheckpointsdevsa --file-system adls --path "adls/weavix_dev_db/telemetry/2025/08/27/12"
```

-----

### Viewing File Content

If you want to view the content of a specific file, you can use the `az storage fs cat` command.

For example, to view the contents of a JSONL file:

```bash
az storage fs cat --account-name <account-name> --file-system <file-system-name> --path <file-path>
```

You would replace `<file-path>` with the full path to the file you want to see. This is useful for quickly verifying that the data was written correctly to the file system.

### Finding your storage account name and key 

You can find both values directly in the Azure portal. Here are the steps:

### 1. Navigate to your Storage Account
Log in to the **Azure portal**. In the search bar at the top, type "Storage accounts" and select the service. From the list, click on the **name of your specific storage account**.

---

### 2. Access the Keys
On the left-hand menu for your storage account, under the **"Security + networking"** section, click on **"Access keys"**.

You will see two keys, `key1` and `key2`, along with their respective connection strings. Your **`AZURE_STORAGE_ACCOUNT_NAME`** is the name of the storage account itself. You can find your **`AZURE_STORAGE_ACCOUNT_KEY`** by clicking the **"Show keys"** button and then copying the **`Key`** value for either `key1` or `key2`. 

You can absolutely find the storage account name and access keys using the Azure CLI. 

Here are the commands you would use:

**1. Get the Storage Account Name**
You can list all storage accounts in a resource group to find the one you need.

```bash
az storage account list --resource-group <your-resource-group-name>
```

This command will return a JSON array of all storage accounts in that resource group.

**2. Get the Access Keys**
Once you have the storage account name, you can retrieve its access keys.

```bash
az storage account keys list --resource-group <your-resource-group-name> --account-name <your-storage-account-name>
```

The output will be a JSON object containing two keys (`key1` and `key2`). You can then extract the `value` field from either of these to use as your `AZURE_STORAGE_ACCOUNT_KEY`.

Using the CLI is a great way to manage these credentials without needing to go through the Azure Portal.

It is a recommended security best practice for production environments. 
Instead of a single connection string, you can provide a list of name-value attributes, typically as environment variables.

The Azure SDK for JavaScript uses a library called **`@azure/identity`** to handle authentication. 
This library can automatically find credentials from your environment variables, so you don't have to manage a hard-coded connection string.

You would typically set the following environment variables:

  * **`AZURE_STORAGE_ACCOUNT_NAME`**: The name of your Azure storage account.
  * **`AZURE_STORAGE_ACCOUNT_KEY`**: The access key for your storage account.

With these variables set, you can modify your code to use a credential object instead of the connection string. Here is how your code would look:

```javascript
const { DataLakeServiceClient } = require("@azure/storage-file-datalake");
const { DefaultAzureCredential } = require("@azure/identity");

// Instead of a connection string, use DefaultAzureCredential
const credential = new DefaultAzureCredential();

const accountName = process.env.AZURE_STORAGE_ACCOUNT_NAME;

this.dataLakeServiceClient = new DataLakeServiceClient(
  `https://${accountName}.dfs.core.windows.net`,
  credential
);

this.fileSystemClient = this.dataLakeServiceClient.getFileSystemClient(fileSystemName);
```

The `AZURE_STORAGE_ACCOUNT_KEY` is required in a scenario where your code needs to **directly interact with Azure Storage services** (like Blob, Table, Queue, or File storage) outside of the security context provided by Managed Identities or Service Principals.

For example, you would need to use `AZURE_STORAGE_ACCOUNT_KEY` if you are:

* Using an older Azure SDK that does not support token-based authentication.
* Running a non-Azure application that needs to authenticate with an Azure Storage account.
* Accessing a storage account from a local development environment and you have not configured other authentication methods.
* Performing an operation that is specifically a "data plane" operation and requires a key, as opposed to a "management plane" operation.
* 
### 1. Azure Blob Storage

 The hierarchical view you see in the Azure WebUI is a **logical hierarchy**, not a **physical** one.    
 It's designed to make your data easier to manage and navigate, even in a storage account that doesn't have a hierarchical namespace enabled.

 

### The Flat Namespace

By default, Azure Blob Storage uses a **flat namespace**. This means that all blobs exist at the same level within a container, like files in a single, massive folder. The "folders" you see are just part of the blob's name.

For example, a blob named `photos/2024/vacation.jpg` is treated by the storage system as a single object with that exact name. The forward slash (`/`) is just a character in the name, not a directory delimiter.



### The Simulated Hierarchy

The Azure portal, Azure Storage Explorer, and many SDKs simulate a folder structure by interpreting the `/` character. When they list the blobs, they group them visually based on these separators, creating the illusion of a file system hierarchy.

This visual simulation is a convenience for you as a user, making it simple to organize and find your data. It doesn't change the underlying flat structure, but it provides a familiar and intuitive way to interact with your blobs.



### True Hierarchical Namespace

A true **hierarchical namespace** is a feature of Azure Data Lake Storage Gen2, which is built on top of Azure Blob Storage.  
When this feature is enabled, "folders" are treated as first-class objects. 
This allows for fast, atomic operations on entire directories, such as renaming or deleting.

Without this feature, a logical folder rename or move operation would require a separate copy and delete command for every single blob within that folder,   
which can be a slow and resource-intensive process for a large number of blobs.

Azure Data Lake Storage Gen2 (ADLS Gen2) 

<https://learn.microsoft.com/en-us/azure/data-factory/connector-azure-data-lake-storage?tabs=data-factory>

<https://azure.github.io/Storage/docs/analytics/hitchhikers-guide-to-the-datalake/>
```js
/**
 * This is a complete, runnable TypeScript example for uploading data
 * to Azure Blob Storage. It demonstrates how to authenticate and
 * upload a string, and how to upload a file from a local path.
 *
 * Prerequisites:
 * 1. An Azure Storage Account with a blob container.
 * 2. An environment variable named 'AZURE_STORAGE_CONNECTION_STRING'
 * set to your storage account's connection string.
 * 3. Run 'npm install @azure/storage-blob' to install the SDK.
 */

// Import the necessary classes from the SDK.
import {
  BlobServiceClient,
  BlockBlobClient,
  StorageSharedKeyCredential
} from "@azure/storage-blob";
import * as path from 'path';
import * as fs from 'fs';

// Load connection string from environment variables for security.
const connectionString = process.env.AZURE_STORAGE_CONNECTION_STRING;
if (!connectionString) {
  throw new Error("AZURE_STORAGE_CONNECTION_STRING environment variable is not set.");
}

// Set your container name here.
const containerName = "your-container-name";

// --- Main Function to Orchestrate Uploads ---
async function main() {
  console.log("Starting Azure Blob Storage upload demo...");

  // Create a BlobServiceClient from the connection string.
  // This client is used to interact with the Azure Blob service at the account level.
  const blobServiceClient = BlobServiceClient.fromConnectionString(connectionString);

  // Get a reference to a container client.
  // This client is used to interact with a specific container.
  const containerClient = blobServiceClient.getContainerClient(containerName);

  // Check if the container exists. If not, create it.
  try {
    await containerClient.createIfNotExists();
    console.log(`Container "${containerName}" exists or was created successfully.`);
  } catch (error) {
    console.error("Failed to create container:", error);
    return;
  }

  // Example 1: Upload a simple string as a blob.
  const stringContent = "Hello, Azure Blob Storage! This is a test string.";
  const stringBlobName = "hello-world.txt";
  await uploadStringAsBlob(containerClient, stringBlobName, stringContent);

  // Example 2: Upload a file from a local path.
  // For this to work, you need a local file to upload.
  const localFilePath = "data.json";
  const fileBlobName = "uploaded-data.json";
  
  // Create a dummy file for the example if it doesn't exist.
  if (!fs.existsSync(localFilePath)) {
    fs.writeFileSync(localFilePath, JSON.stringify({ message: "This is a test file!" }));
    console.log(`Created a dummy file at "${localFilePath}" for the demo.`);
  }

  await uploadFileAsBlob(containerClient, localFilePath, fileBlobName);

  console.log("Azure Blob Storage upload demo completed.");
}

/**
 * Uploads a string of data to a block blob.
 * @param containerClient The ContainerClient object.
 * @param blobName The name of the blob to create.
 * @param content The string content to upload.
 */
async function uploadStringAsBlob(containerClient: any, blobName: string, content: string) {
  try {
    // Get a reference to a block blob client.
    // This client is used to interact with a specific blob.
    const blockBlobClient = containerClient.getBlockBlobClient(blobName);
    
    // Upload the string content.
    const uploadBlobResponse = await blockBlobClient.upload(content, content.length);
    
    console.log(`\nSuccessfully uploaded string to blob: ${blobName}`);
    console.log(`Request ID: ${uploadBlobResponse.requestId}`);
  } catch (error) {
    console.error(`Error uploading string to blob ${blobName}:`, error);
  }
}

/**
 * Uploads a file from a local path to a block blob.
 * This method is specifically for Node.js environments.
 * @param containerClient The ContainerClient object.
 * @param localFilePath The full path to the local file.
 * @param blobName The name of the blob to create.
 */
async function uploadFileAsBlob(containerClient: any, localFilePath: string, blobName: string) {
  try {
    // Get a reference to a block blob client.
    const blockBlobClient = containerClient.getBlockBlobClient(blobName);
    
    // Use the uploadFile method for Node.js to efficiently upload the file.
    const uploadResponse = await blockBlobClient.uploadFile(localFilePath);
    
    console.log(`\nSuccessfully uploaded file "${localFilePath}" to blob: ${blobName}`);
    console.log(`Request ID: ${uploadResponse.requestId}`);
  } catch (error) {
    console.error(`Error uploading file to blob ${blobName}:`, error);
  }
}

// Run the main function.
main().catch((error) => console.error("Main function failed:", error));
```



###  difference between `upload()` and `uploadData()` in the Azure Blob Storage SDK.

The main difference is the type of data they are optimized to handle and the environments they are designed for.

* **`upload()`:** This is a versatile, general-purpose method that can accept various data types,  
  including a `string`, `Buffer`, or a `ReadableStream`. It is often used for non-parallel, single-shot uploads.  
* This is the method used s for a simple string upload because it's the most direct way to handle that specific data type.

* **`uploadData()`:** This method is specifically designed for uploading binary data from a `Buffer`, `ArrayBuffer`, or `ArrayBufferView`.  
  A key feature is that it can handle large uploads by automatically splitting the data into chunks and uploading them in parallel for better performance.  

In short, `upload()` is great for simpler cases and various data inputs,   
while `uploadData()` is your go-to for efficient, high-performance uploads of binary data, especially for larger files.   
For uploading a local file,   the SDK also provides the more specific and often more performant `uploadFile()` method, 
which is optimized for Node.js.


### How to run TypeScript code above:

To run your TypeScript code from the console, you'll need to have Node.js and npm installed. You'll also need the TypeScript compiler, `tsc`, and a package like `ts-node` to run TypeScript files directly without compiling them first.

Here's a step-by-step guide:

### 1\. Initialize Your Project

First, navigate to your project directory in the console and initialize a new Node.js project. This creates a `package.json` file.

```bash
npm init -y
```

### 2\. Install Dependencies

Next, install the required packages: `typescript`, `ts-node`, and `@azure/storage-blob`. `ts-node` is a great tool that lets you execute TypeScript files directly, which is useful for development.

```bash
npm install typescript ts-node @azure/storage-blob
```

### 3\. Configure TypeScript

Create a `tsconfig.json` file in your project's root directory. This file tells the TypeScript compiler how to compile your code. You can generate a basic one with the following command:

```bash
npx tsc --init
```

For the Azure Blob SDK example, you'll want to ensure `ES2017` or higher is the `target` to support `async/await` and that `esModuleInterop` and `skipLibCheck` are set to `true` to avoid common import errors.

### 4\. Set the Environment Variable

Before running the code, you must set the `AZURE_STORAGE_CONNECTION_STRING` environment variable as specified in the comments of the Canvas.

**On Windows (Command Prompt):**

```bash
set AZURE_STORAGE_CONNECTION_STRING="your_connection_string_here"
```

**On macOS/Linux (Terminal):**

```bash
export AZURE_STORAGE_CONNECTION_STRING="your_connection_string_here"
```

### 5\. Run the Code

Finally, you can run the TypeScript file directly from your console using `ts-node`.

```bash
npx ts-node your_file_name.ts
```

This command will execute the code, perform the uploads, and print the results to your console.


### Npx
"Npx" is a tool that comes with **Node.js** and **npm** (Node Package Manager). It stands for **Node Package eXecuter**. 

Its main purpose is to let you run an executable file from a package without having to install that package globally or in your project's `node_modules` directory first.

In the context of the Canvas, when we use `npx tsc --init`,   
we're running the TypeScript compiler (`tsc`) executable directly from the npm registry without needing to install it globally. 

This is useful for one-off commands or when you want to ensure you're using a specific version of a tool without cluttering your global environment.





##  Is StorageV2 the same as ADLS Gen2?
```
Not automatically.

ADLS Gen2 (Azure Data Lake Storage Gen2) is not a separate account kind.

It is a set of hierarchical namespace (HNS) features you enable on top of a StorageV2 account.

In other words:

All ADLS Gen2 accounts are StorageV2.
But not all StorageV2 accounts are ADLS Gen2.
You only get true ADLS Gen2 capabilities (like Hadoop-compatible file system, directories, ACLs) if the Hierarchical Namespace setting is enabled.

3. How to check if your StorageV2 account is ADLS Gen2?
- Go to your storage account in the portal.
- Under Data storage → Containers, try to create a file system.
- Or, in Configuration, check if Hierarchical namespace = Enabled.

If enabled, then it’s ADLS Gen2. If not, then it’s just a regular blob storage account.

✅ Summary:

“Kind = StorageV2” means it’s the right account type to support ADLS Gen2.
To confirm it’s really ADLS Gen2, check if Hierarchical Namespace is enabled in the account configuration.
```

## How to create   **ADLS Gen2 storage account**  in **Azure Portal (Web UI)** by creating a **Storage Account** with *Hierarchical namespace* enabled. 

Here’s a step-by-step:


### 1. Sign in

* Go to [https://portal.azure.com](https://portal.azure.com) and log in.

### 2. Start Storage Account creation

* In the top search bar, type **Storage accounts**.
* Click **+ Create**.


### 3. Basics tab

Fill in the required fields:

* **Subscription** → pick your Azure subscription.
* **Resource group** → select an existing one or click **Create new**.
* **Storage account name** → must be globally unique, lowercase letters and numbers only.
* **Region** → where you want it deployed.
* **Performance** → *Standard* (HDD, cheaper) or *Premium* (SSD, faster).
* **Redundancy** → choose replication option (LRS, ZRS, GRS, RA-GRS).


### 4. Advanced tab (important for ADLS Gen2)

* Scroll to **Data Lake Storage Gen2**.
* **Enable hierarchical namespace** → check this box. ✅
  (This is what makes it ADLS Gen2 instead of just Blob storage.)


### 5. Networking / Data Protection / Tags

* Configure if needed (most defaults are fine for a test).


### 6. Review + Create

* Review settings → click **Create**.
* Deployment takes \~1–2 minutes.


### 7. Verify ADLS Gen2

* After deployment, open the storage account.
* In the left menu, under **Data storage**, you’ll see **Containers** and **Data Lake Gen2 features** (like “File systems”).
* If you see **File systems**, then Hierarchical namespace was enabled and it’s ADLS Gen2.

 

## How to create  ADLS Gen2 storage account  using `az CLI` command**  
(i.e., a Storage Account with **Hierarchical Namespace enabled**):

```bash
# Variables (adjust as needed)
RESOURCE_GROUP=myResourceGroup
LOCATION=eastus
STORAGE_ACCOUNT_NAME=mystorageacct123   # must be globally unique and lowercase

# Create resource group (if not already exists)
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# Create ADLS Gen2 storage account
az storage account create \
  --name $STORAGE_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --hierarchical-namespace true
```

### Explanation of flags:

* `--kind StorageV2` → ensures it’s the modern type that supports ADLS Gen2.
* `--hierarchical-namespace true` → this enables **Data Lake Gen2** features.
* `--sku Standard_LRS` → local redundant storage (you can change to `Standard_ZRS`, `Standard_GRS`, etc. depending on durability needs).

---

✅ After running this, you’ll have an ADLS Gen2 storage account ready.
You can then create **containers (file systems)** inside it with:

```bash
az storage container create \
  --account-name $STORAGE_ACCOUNT_NAME \
  --name mycontainer \
  --auth-mode login
```

 

## ADLS Gen2 on  **Azure Portal (Web UI) 

1. **Search for Storage Accounts** in the top search bar.
2. Click **+ Create**.
3. **Basics tab** → choose subscription, resource group, name, region, redundancy.
4. **Advanced tab** → enable **Hierarchical namespace** ✅ (this makes it ADLS Gen2).
5. **Review + Create** → then click **Create**.
6. After deployment, open the storage account and check for **File systems** under *Data storage* → this confirms ADLS Gen2 is active.

---

## ADLS Gen2 on **Azure CLI**

Here’s the full setup in CLI:

```bash
# Variables
RESOURCE_GROUP=myResourceGroup
LOCATION=eastus
STORAGE_ACCOUNT_NAME=mystorageacct123   # must be globally unique and lowercase

# 1. Create resource group (if not already exists)
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION

# 2. Create ADLS Gen2 storage account
az storage account create \
  --name $STORAGE_ACCOUNT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --hierarchical-namespace true

# 3. (Optional) Create a container (file system) inside
az storage container create \
  --account-name $STORAGE_ACCOUNT_NAME \
  --name mycontainer \
  --auth-mode login
```


✅ At this point, whether you used Portal or CLI, you have a working **ADLS Gen2 storage account** with at least one container ready.

You can confirm **Hierarchical Namespace (ADLS Gen2)** is enabled on a storage account using the `az storage account show` command.

Here’s how:

```bash
az storage account show \
  --name mystorageacct123 \
  --resource-group myResourceGroup \
  --query "isHnsEnabled"
```

* If it returns `true` → **Hierarchical namespace is enabled** (this is ADLS Gen2).
* If it returns `false` → it’s just a regular Blob Storage account.

---

For a full property list (so you can see all settings, including replication, SKU, location, etc.):

```bash
az storage account show \
  --name mystorageacct123 \
  --resource-group myResourceGroup \
  --output table
```

You’ll see a column **IsHnsEnabled** → should be `True`. ✅


Once you’ve confirmed **Hierarchical Namespace** is enabled, you can list all containers   
(in ADLS Gen2 they’re called **file systems**) with the CLI:


### **List all containers (file systems)**

```bash
az storage container list \
  --account-name mystorageacct123 \
  --auth-mode login \
  --output table
```

* `--auth-mode login` → uses your Azure login (make sure you did `az login`).
* `--output table` → formats it neatly, showing name, lease status, public access, etc.

Example output:

```
Name        Lease Status    Public Access
----------  --------------  --------------
mycontainer available       None
rawdata     available       None
```

---

### **Alternative (JSON output)**

If you want details (creation time, metadata, etag, etc.):

```bash
az storage container list \
  --account-name mystorageacct123 \
  --auth-mode login \
  --output json
```

---

### **Confirming ADLS Gen2 Structure**

When `isHnsEnabled` is `true` **and** you can see containers via `az storage container list`, that confirms your storage account is an **ADLS Gen2 account**. ✅

---

##  How to **verify and list file systems (containers) in Azure Portal Web UI** for an **ADLS Gen2 storage account**:



### **Steps in Azure Portal**

1. **Go to your Storage Account**

   * In [https://portal.azure.com](https://portal.azure.com), search for **Storage accounts**.
   * Click the name of your ADLS Gen2 storage account (the one you created with hierarchical namespace enabled).

2. **Navigate to Data Storage section**

   * In the left-hand menu, under **Data storage**, click **Containers**.
   * In ADLS Gen2, *containers = file systems*.

3. **View all file systems**

   * You’ll see a list of containers (file systems) that exist in your storage account.
   * Example:

     ```
     Name         Last modified
     -----------  -------------------
     mycontainer  2025-08-24, 10:15 AM
     rawdata      2025-08-24, 10:22 AM
     ```
   * You can click into any of them to browse folders/files (hierarchical because ADLS Gen2 is enabled).

4. **Confirm ADLS Gen2 (Hierarchical Namespace)**

   * Still in the storage account blade, go to **Configuration** (left menu).
   * Look for **Hierarchical namespace** → it should say **Enabled** ✅.

---

So to summarize:

* **Containers** in Portal = **File Systems** in ADLS Gen2.
* **Configuration tab** → check **Hierarchical namespace** is enabled to confirm it’s really Gen2.

---
Here’s how you can **create a new file system (container)** in the **Azure Portal Web UI** for your ADLS Gen2 account:

---

### **Steps in Azure Portal**

1. **Open your Storage Account**

   * Go to [https://portal.azure.com](https://portal.azure.com).
   * Search for **Storage accounts** and click your ADLS Gen2 storage account.

2. **Go to Containers (File Systems)**

   * In the left-hand menu, under **Data storage**, click **Containers**.
   * This shows the list of all existing containers (file systems).

3. **Create a new Container**

   * At the top of the Containers page, click **+ Container**.
   * Fill in details:

     * **Name** → must be lowercase letters, numbers, and hyphens only (e.g., `rawdata`, `bronze-layer`, `2025logs`).
     * **Public access level** → choose:

       * *Private (no anonymous access)* → default, recommended for ADLS Gen2.
       * *Blob* or *Container* if you want anonymous access (rare in ADLS use cases).
     * **Advanced settings** → usually leave defaults.

4. **Click Create**

   * The new container (file system) will now appear in the list.
   * You can click into it to create folders, upload files, etc.

---

### **Verify**

* The new container will be visible immediately in the **Containers** list.
* Since hierarchical namespace is enabled, inside that container you can create a directory tree (folders/subfolders) — unlike classic blob storage where it’s flat.

---

✅ So now you can both **list** all containers and **create new ones** in the same **Containers** page of the storage account in Azure Portal.

---

Would you like me to also show you the **CLI equivalent** (`az storage container create`) alongside the Portal steps, so you have both UI + script methods in one place?

-----
Azure Blog Storage: A scalable object storage service for storing unstructured data like images, videos, CSV files, Parquet files, backups, and logs.

🔹 Key Points:
Ideal for data lakes, backup, and archive.

Stores files in containers.

Supports hot, cool, and archive tiers for cost control.

Used by Azure Synapse, Data Factory, and others as a data source or sink.

🔧 Example use cases:

Storing raw data for analytics

Hosting files for machine learning

Serving images/documents to web apps



Perfect 👍 — here’s a **side-by-side guide** to creating a new **file system (container)** in **Azure Data Lake Storage Gen2**, showing both **Azure Portal UI** and **Azure CLI**:

---

## **Option 1 – Azure Portal (Web UI)**

1. **Open your Storage Account**

   * Log in to [https://portal.azure.com](https://portal.azure.com).
   * Search **Storage accounts** → click your ADLS Gen2 storage account.

2. **Go to Containers**

   * In the left menu, under **Data storage**, click **Containers**.
   * You’ll see the list of existing containers (file systems).

3. **Create New Container**

   * Click **+ Container** (top menu).
   * Enter:

     * **Name** → e.g., `bronze-data` (must be lowercase, no spaces).
     * **Public access level** → choose *Private (default)*.
   * Click **Create**.

✅ Your new container will appear in the list. You can now upload files or create directories inside it.

---

## **Option 2 – Azure CLI**

Equivalent command to create a container (file system):

```bash
# Variables
RESOURCE_GROUP=myResourceGroup
STORAGE_ACCOUNT_NAME=mystorageacct123
CONTAINER_NAME=bronze-data   # must be lowercase

# Create the container
az storage container create \
  --account-name $STORAGE_ACCOUNT_NAME \
  --name $CONTAINER_NAME \
  --auth-mode login
```

* `--auth-mode login` uses your Azure AD login (after `az login`).
* If you want to allow public blob access (not common in ADLS Gen2):

  ```bash
  az storage container create \
    --account-name $STORAGE_ACCOUNT_NAME \
    --name $CONTAINER_NAME \
    --public-access blob \
    --auth-mode login
  ```

---

### **Summary**

* **Portal** → Storage account → **Containers** → **+ Container** → Name → Create.
* **CLI** → `az storage container create ...`.

Both give you a new **ADLS Gen2 file system** that will show up under **Containers** in Portal and via `az storage container list`.




