How to get your AWS Access Key ID and Secret Access Key from the AWS Console 

## Getting Your Access Keys from AWS Console

1. **Sign in to AWS Console** and go to the **IAM (Identity and Access Management)** service
   - You can search for "IAM" in the top search bar

2. **Navigate to your user**:
   - Click on "Users" in the left sidebar
   - Click on your username

3. **Create Access Keys**:
   - Go to the "Security credentials" tab
   - Scroll down to the "Access keys" section
   - Click "Create access key"

4. **Select use case**:
   - Choose "Command Line Interface (CLI)"
   - Check the confirmation box
   - Click "Next"

5. **Download or copy your credentials**:
   - You'll see your **Access Key ID** and **Secret Access Key**
   - **Important**: This is the ONLY time you'll be able to see the Secret Access Key, so make sure to copy it or download the CSV file

6. **Use in aws configure**:
   ```bash
   aws configure
   ```
   - Paste your Access Key ID
   - Paste your Secret Access Key
   - Enter your default region (e.g., `us-east-1`)
   - Enter default output format (e.g., `json`)

## Important Security Notes

- **Never share** your Secret Access Key
- Store it securely (the key will be saved in `~/.aws/credentials` on your Mac)
- If you lose the Secret Access Key, you'll need to create a new access key
- Consider using access keys with appropriate IAM permissions (least privilege principle)

After configuration, you can test your connection with:
```bash
aws dynamodb list-tables
```

