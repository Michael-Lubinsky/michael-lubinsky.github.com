## AWS CLI

## JMESPath

**JMESPath** is a query language for JSON. AWS CLI includes it through the global `--query` option, letting you filter, select, sort, and reshape an AWS command’s response before it is printed. ([AWS Documentation][1])

Think of it as roughly:

* SQL-like querying for JSON
* `jq`-like filtering built directly into AWS CLI
* Python list/dictionary operations expressed as a compact command-line language

## Basic example

Without JMESPath:

```bash
aws ec2 describe-instances
```

This returns a large nested JSON document.

With JMESPath:

```bash
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].InstanceId'
```

Output:

```json
[
  "i-0123456789abcdef0",
  "i-0987654321abcdef0"
]
```

The expression means:

```text
Reservations[]
    take every reservation

.Instances[]
    take every instance inside each reservation

.InstanceId
    return only the InstanceId field
```

## Selecting multiple fields

You can transform each instance into a smaller object:

```bash
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].{
      InstanceId: InstanceId,
      Type: InstanceType,
      State: State.Name,
      PrivateIp: PrivateIpAddress
  }'
```

Result:

```json
[
  {
    "InstanceId": "i-0123456789abcdef0",
    "Type": "t3.medium",
    "State": "running",
    "PrivateIp": "10.0.1.25"
  }
]
```

This is called a **multiselect hash**.

## Filtering records

Return only running instances:

```bash
aws ec2 describe-instances \
  --query 'Reservations[].Instances[?State.Name==`running`].InstanceId'
```

Important syntax:

```text
[? condition ]
```

JMESPath literal values commonly use backticks:

```text
`running`
`true`
`10`
```

For example:

```bash
aws s3api list-buckets \
  --query 'Buckets[?contains(Name, `production`)].Name'
```

## Sorting

Sort EC2 instances by launch time:

```bash
aws ec2 describe-instances \
  --query 'sort_by(Reservations[].Instances[], &LaunchTime)[].{
      ID: InstanceId,
      Launched: LaunchTime
  }'
```

Reverse the result to show newest first:

```bash
aws ec2 describe-instances \
  --query 'reverse(sort_by(Reservations[].Instances[], &LaunchTime))[].{
      ID: InstanceId,
      Launched: LaunchTime
  }'
```

## Extracting tags

EC2 tags have a structure such as:

```json
"Tags": [
  {"Key": "Name", "Value": "web-server"},
  {"Key": "Environment", "Value": "production"}
]
```

Extract the `Name` tag:

```bash
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].{
      ID: InstanceId,
      Name: Tags[?Key==`Name`].Value | [0]
  }'
```

The pipe:

```text
|
```

passes one expression’s result into the next expression.

Here:

```text
Tags[?Key==`Name`].Value
```

may produce:

```json
["web-server"]
```

Then:

```text
| [0]
```

selects the first value.

## Producing table output

JMESPath controls the data; `--output` controls its final presentation:

```bash
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].[
      InstanceId,
      InstanceType,
      State.Name,
      PrivateIpAddress
  ]' \
  --output table
```

Example:

```text
-------------------------------------------------
|               DescribeInstances               |
+----------------------+-----------+-------------+
| i-0123456789abcdef0  | t3.medium | running     |
+----------------------+-----------+-------------+
```

For predictable tables, select fields in a fixed list or object rather than returning the original complex JSON.

## Common JMESPath constructs

| Expression                 | Meaning                                     |
| -------------------------- | ------------------------------------------- |
| `Field`                    | Select a field                              |
| `A.B`                      | Select nested field                         |
| `Items[]`                  | Flatten or iterate over an array            |
| `Items[0]`                 | First item                                  |
| `Items[-1]`                | Last item                                   |
| `Items[0:5]`               | First five items                            |
| `Items[*].Name`            | Select `Name` from all items                |
| `Items[?State==\`active`]` | Filter items                                |
| `{ID: Id, Name: Name}`     | Create an object                            |
| `[Id, Name]`               | Create a list                               |
| `sort_by(Items, &Name)`    | Sort by a field                             |
| `length(Items)`            | Count items                                 |
| `contains(Name, \`prod`)`  | Test whether a value contains another value |
| `A \| B`                   | Pass result of A into B                     |

JMESPath has a formally specified grammar and supports projections, filters, pipes, multiselects, slices, and functions. ([jmespath.org][2])

## Server-side versus client-side filtering

This distinction is important.

### Server-side filtering

```bash
aws ec2 describe-instances \
  --filters 'Name=instance-state-name,Values=running'
```

The AWS service filters the records before sending them to your computer.

### JMESPath client-side filtering

```bash
aws ec2 describe-instances \
  --query 'Reservations[].Instances[?State.Name==`running`]'
```

AWS returns the API response first, and then AWS CLI applies the JMESPath expression locally. Therefore, `--query` normally does not reduce network transfer or API processing. ([AWS Documentation][1])

They can be combined:

```bash
aws ec2 describe-instances \
  --filters 'Name=instance-state-name,Values=running' \
  --query 'Reservations[].Instances[].{
      ID: InstanceId,
      Type: InstanceType,
      IP: PrivateIpAddress
  }'
```

Use server-side filters to reduce the result set and `--query` to reshape the remaining data.

## JMESPath versus `jq`

AWS CLI:

```bash
aws ec2 describe-instances \
  --query 'Reservations[].Instances[].InstanceId'
```

Equivalent general idea with `jq`:

```bash
aws ec2 describe-instances |
jq '.Reservations[].Instances[].InstanceId'
```

JMESPath’s advantages are that it is built into AWS CLI and works directly with `--output json`, `text`, `table`, or `yaml`. `jq` is generally more powerful for complex transformations, arithmetic, custom object manipulation, and scripting.

## One pagination caveat

AWS documents an important difference for paginated commands:

* With `--output json`, `yaml`, or `yaml-stream`, the CLI processes the complete native result and applies the query to the combined structure.
* With `--output text`, the query can be applied separately to each response page, potentially producing unexpected repeated results. ([AWS Documentation][3])

For complicated or paginated queries, prefer:

```bash
--output json
```

and convert to text afterward when necessary.

[1]: https://docs.aws.amazon.com/cli/v1/userguide/cli-usage-filter.html?utm_source=chatgpt.com "Filtering output in the AWS CLI"
[2]: https://jmespath.org/?utm_source=chatgpt.com "JMESPath — JMESPath"
[3]: https://docs.aws.amazon.com/ko_kr/cli/latest/userguide/cli-usage-filter.html?utm_source=chatgpt.com "AWS CLI에서 출력 필터링"


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
