# AVRO -> Snowflake

I configured Azure EventHub Capture with serialization in Avro format on ADLS Gen2.
How to configure automate triggering Snowpipe from ADLS Gen2 on regular bases every 15 minutes?

## Claude
Snowpipe doesn't support direct triggering from ADLS Gen2 on a time-based schedule. 
Snowpipe is designed for event-driven loading when new files arrive, not scheduled batch processing. 
Here are the viable approaches:

## Option 1: Event-Driven Snowpipe (Recommended)
Set up automatic loading when new files arrive:

1. **Create Azure Event Grid subscription** on your storage account
2. **Configure blob creation events** to trigger when Avro files are written
3. **Use Azure Function or Logic App** to call Snowpipe REST API
4. **Files load automatically** as they're captured

```sql
-- Create pipe
CREATE PIPE eventhub_pipe 
AUTO_INGEST = FALSE 
AS COPY INTO events_table 
FROM @eventhub_stage 
FILE_FORMAT = (TYPE = 'AVRO');
```

## Option 2: Scheduled Tasks (Better for 15-minute intervals)
Since you want regular 15-minute intervals, use Snowflake Tasks:

```sql
-- Create task that runs every 15 minutes
CREATE TASK load_eventhub_data
WAREHOUSE = 'COMPUTE_WH'
SCHEDULE = 'USING CRON 0,15,30,45 * * * *'
AS
COPY INTO events_table 
FROM @eventhub_stage 
FILE_FORMAT = (TYPE = 'AVRO')
FILES = (SELECT file_name FROM directory(@eventhub_stage) 
         WHERE last_modified > current_timestamp - INTERVAL '16 minutes');

-- Start the task
ALTER TASK load_eventhub_data RESUME;
```

## Option 3: External Orchestration
Use Azure Data Factory or Logic Apps:

1. **Create Logic App** with 15-minute recurrence
2. **Call Snowflake REST API** to execute COPY commands
3. **Handle file tracking** to avoid duplicates

## Recommended Architecture

For your 15-minute requirement, **Option 2 (Snowflake Tasks)** is most appropriate because:
- Native Snowflake scheduling
- Efficient incremental loading
- Built-in error handling and monitoring
- No external dependencies

Event-driven Snowpipe is better for near real-time loading but adds complexity for your scheduled use case.

## ChatGPT
