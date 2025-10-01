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

## If you sign in to AWS via SSO (IAM Identity Center),

- If you sign in to AWS via SSO (IAM Identity Center), you do NOT use long-term “Access Key ID / Secret Access Key”.
- You can’t “get” those keys from the console unless you have an IAM *user* with programmatic access. SSO users don’t have access keys.

#### Claude
--------------
Ah, that changes things! If you're using **AWS SSO (IAM Identity Center)**, you should **NOT** use `aws configure` with long-term access keys. Instead, you should use AWS SSO authentication, which is more secure.

## Setting Up AWS CLI with SSO

1. **Configure AWS CLI for SSO**:
   ```bash
   aws configure sso
   ```

2. **Answer the prompts**:
   - **SSO session name**: Give it a name (e.g., `my-sso`)
   - **SSO start URL**: This is your SSO portal URL (looks like `https://d-xxxxxxxxxx.awsapps.com/start` or your custom domain)
   - **SSO Region**: The region where your SSO is configured (e.g., `us-east-1`)
   - **SSO registration scopes**: Just press Enter for default (`sso:account:access`)

3. **Browser authentication**:
   - A browser window will open
   - Sign in with your SSO credentials
   - Authorize the AWS CLI

4. **Select your account and role**:
   - Choose the AWS account you want to use
   - Choose the IAM role you want to assume
   - Set default region (e.g., `us-east-1`)
   - Set default output format (e.g., `json`)

5. **Profile name**: Give your profile a name (e.g., `default` or `work`)

## Using Your SSO Profile

After configuration, use your profile with:
```bash
aws dynamodb list-tables --profile your-profile-name
```

Or if you named it `default`, you can just use:
```bash
aws dynamodb list-tables
```

## Getting Your SSO Start URL

If you don't know your SSO start URL:
- Check your browser bookmarks (you probably use it to sign in)
- Ask your AWS administrator
- Look in your email for the SSO invitation

This approach is much more secure than long-term access keys and is the recommended way when using SSO!


#### Gemini
---------------
What to do instead (CLI with SSO)
1) Ensure CLI v2:
```
   aws --version
   # should show aws-cli/2.x
```
3) Configure an SSO profile:
```
   aws configure sso
   # enter:
   # - SSO start URL (from your org’s Identity Center portal)
   # - SSO region (where Identity Center is hosted, e.g. us-west-2)
   # - Select the AWS account & role
   # - Profile name (e.g. weavix-dev)
   # - Default region (your DynamoDB region, for N. Virginia use us-east-1)
```
4) Log in to SSO:
```
   aws sso login --profile weavix-dev
```
5) Test:
```
   aws sts get-caller-identity --profile weavix-dev
   aws dynamodb list-tables --region us-east-1 --profile weavix-dev
```
Tip: set env vars so you don’t have to pass --profile/--region each time:
```
   export AWS_PROFILE=weavix-dev
   export AWS_DEFAULT_REGION=us-east-1
```
When you WOULD use access keys
- Only if your admin gives you an IAM user with programmatic access.
- Console path (if allowed): IAM > Users > Your user > Security credentials > “Create access key”.
- Many orgs disable this; SSO + roles is preferred for security.

Reminder
- “United States (N. Virginia)” = us-east-1.
- SSO tokens expire; if commands start failing later, run:
  aws sso login --profile weavix-dev
```
