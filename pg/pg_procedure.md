## Stored procedure example
```sql
CREATE OR REPLACE PROCEDURE public.process_date_range(
    p_start DATE,
    p_end DATE
)
LANGUAGE plpgsql
AS $$
DECLARE
    current_date DATE := p_start;
BEGIN
    IF p_start > p_end THEN
        RAISE EXCEPTION 'Start date (%) is after end date (%)', p_start, p_end;
    END IF;

    WHILE current_date <= p_end LOOP
        CALL public.process_single_date(current_date);
        current_date := current_date + INTERVAL '1 day';
    END LOOP;
END;
$$;
```
### Pass procedure name as parameter
```sql
CREATE OR REPLACE PROCEDURE public.process_date_range(
    p_start DATE,
    p_end DATE,
    p_proc_name TEXT  -- schema-qualified procedure name as string
)
LANGUAGE plpgsql
AS $$
DECLARE
    current_date DATE := p_start;
BEGIN
    IF p_start > p_end THEN
        RAISE EXCEPTION 'Start date (%) is after end date (%)', p_start, p_end;
    END IF;

    WHILE current_date <= p_end LOOP
        EXECUTE format(
            'CALL %I(%L)',
            p_proc_name,
            current_date
        );
        current_date := current_date + INTERVAL '1 day';
    END LOOP;
END;
$$;

CREATE OR REPLACE PROCEDURE public.process_single_date(p_date DATE)
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE NOTICE 'Processing %', p_date;
END;
$$;

CALL public.process_date_range('2025-08-01', '2025-08-03', 'public.process_single_date');
```

## Run Stored Procedure In The Loop
```sql
DO $$
DECLARE
  d date;
BEGIN
  FOR d IN
    SELECT generate_series(date '2025-01-01', date '2025-08-20', interval '1 day')::date
  LOOP
    BEGIN
      CALL schema_name.proc_name(d);
    EXCEPTION WHEN OTHERS THEN
      RAISE NOTICE 'Failed for %: [%] %', d, SQLSTATE, SQLERRM;
    END;
  END LOOP;
END$$;


--- ANOTHER WAY: shows elapsed time

DO $$
DECLARE
    date_to_process DATE;
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    elapsed_interval INTERVAL;
BEGIN
    FOR date_to_process IN 
        SELECT generate_series('2024-01-01'::date, '2024-01-31'::date, '1 day'::interval)::date
    LOOP
        start_time := clock_timestamp();
        RAISE NOTICE '[%] Starting processing date: %', start_time, date_to_process;
        
        CALL gold.ptt_sent_by_channel_type_daily(date_to_process);
        
        end_time := clock_timestamp();
        elapsed_interval := end_time - start_time;
        RAISE NOTICE '[%] Completed processing: % (Duration: %)', end_time, date_to_process, elapsed_interval;
    END LOOP;
    
    RAISE NOTICE '[%] All dates processed successfully', clock_timestamp();
END $$;
```

### Generate  code from code using FORMAT
```sql
SELECT format('SELECT gold.backfill_day(''%s''::timestamptz);', day_start)
FROM generate_series(
  '2025-09-11 14:45:00.000 -0700'::timestamptz,
  '2025-10-22 14:45:00.000 -0700'::timestamptz,
  '1 day'::interval
) as day_start
ORDER BY day_start;
```
code above generates:
```
SELECT gold.backfill_day('2025-09-11 14:45:00.000-07'::timestamptz);
SELECT gold.backfill_day('2025-09-12 14:45:00.000-07'::timestamptz);
```


## There is postgres pg_cron job which runs in UTC timezone.
This job calls stored procedure which accepts  the date argument.
 If I run this stored procedure interactively, my session time zone is not UTC.
Will result of this stored procedure depend on calling it interactively or  via pg_cron?

Yes, the results **CAN BE DIFFERENT** depending on how the date is determined and used. Here's why:

## The Critical Factor: How the Date is Generated

### Scenario 1: **Using CURRENT_DATE or NOW()** - DIFFERENT RESULTS
```sql
-- pg_cron job (UTC timezone)
CALL my_procedure(CURRENT_DATE);  -- Uses UTC date

-- Interactive session (e.g., America/New_York)
CALL my_procedure(CURRENT_DATE);  -- Uses New York date
```

**These can be different dates!** Example:
```sql
-- At 9 PM New York time on Oct 18:
-- UTC:      Oct 19 (1 AM next day)  
-- New York: Oct 18 (9 PM same day)

-- pg_cron would pass '2025-10-19'
-- Interactive would pass '2025-10-18'
```

### Scenario 2: **Using Literal Dates** - SAME RESULTS
```sql
-- Both calls pass the same date
CALL my_procedure('2025-10-18'::date);  -- Always Oct 18, regardless of timezone
```

## Real-World Example:

```sql
-- Stored procedure
CREATE OR REPLACE PROCEDURE process_daily_data(target_date DATE)
AS $$
BEGIN
    -- This will process data for the specific date passed
    DELETE FROM temp_data WHERE data_date < target_date;
    
    INSERT INTO daily_summary 
    SELECT ... FROM transactions 
    WHERE transaction_date = target_date;
END;
$$ LANGUAGE plpgsql;

-- pg_cron job at 1 AM UTC
SELECT cron.schedule('daily_job', '0 1 * * *', 
    'CALL process_daily_data(CURRENT_DATE - INTERVAL ''1 day'');');

-- Problem scenario:
-- At 11 PM Pacific (7 AM UTC next day):
-- pg_cron thinks it's Oct 19, so processes Oct 18
-- Interactive session thinks it's Oct 18, so would also try to process Oct 18
-- But at 9 PM Pacific (5 AM UTC next day):
-- pg_cron thinks it's Oct 19, processes Oct 18  
-- Interactive thinks it's Oct 18, processes Oct 17
-- DIFFERENT DATES!
```

## How to Ensure Consistency:

### Option 1: **Always Use Explicit UTC**
```sql
-- In the procedure call, explicitly convert to UTC
CALL my_procedure((NOW() AT TIME ZONE 'UTC')::date);

-- Or in pg_cron
'CALL my_procedure((NOW() AT TIME ZONE ''UTC'')::date);'
```

### Option 2: **Use Timestamp Parameters Instead of Date**
```sql
CREATE OR REPLACE PROCEDURE process_daily_data(
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ
)
AS $$
BEGIN
    -- Timestamps preserve timezone context
    INSERT INTO daily_summary 
    SELECT ... FROM transactions 
    WHERE created_at >= start_time AND created_at < end_time;
END;
$$ LANGUAGE plpgsql;

-- Call with explicit times
CALL process_daily_data(
    '2025-10-18 00:00:00 UTC'::timestamptz,
    '2025-10-19 00:00:00 UTC'::timestamptz
);
```

### Option 3: **Set Session Timezone in Procedure**
```sql
CREATE OR REPLACE PROCEDURE process_daily_data(target_date DATE)
AS $$
BEGIN
    -- Force UTC interpretation
    SET LOCAL timezone = 'UTC';
    
    -- Now all date/time operations use UTC
    INSERT INTO daily_summary 
    SELECT ... FROM transactions 
    WHERE transaction_date = target_date;
END;
$$ LANGUAGE plpgsql;
```

## Testing for Differences:

```sql
-- Check what date would be used in different scenarios
SELECT 
    CURRENT_DATE AS session_date,
    (NOW() AT TIME ZONE 'UTC')::date AS utc_date,
    current_setting('timezone') AS session_timezone,
    NOW() AS current_timestamp_with_tz;

-- Set different timezone and compare
SET timezone = 'America/Los_Angeles';
SELECT CURRENT_DATE AS la_date;

SET timezone = 'UTC';  
SELECT CURRENT_DATE AS utc_date;

-- See the difference
SELECT 
    '2025-10-18 23:00:00 America/Los_Angeles'::timestamptz AT TIME ZONE 'UTC' AS utc_time,
    ('2025-10-18 23:00:00 America/Los_Angeles'::timestamptz AT TIME ZONE 'UTC')::date AS utc_date;
-- Results: '2025-10-19 06:00:00' and '2025-10-19'
```

## Best Practices:

1. **Be Explicit About Timezones**
```sql
-- Bad: Ambiguous
CALL process_daily_data(CURRENT_DATE - 1);

-- Good: Explicit
CALL process_daily_data((NOW() AT TIME ZONE 'UTC' - INTERVAL '1 day')::date);
```

2. **Document Timezone Assumptions**
```sql
CREATE OR REPLACE PROCEDURE process_daily_data(
    target_date DATE  -- Expected to be in UTC
)
AS $$
BEGIN
    -- Procedure assumes dates are in UTC context
    ...
END;
$$ LANGUAGE plpgsql;
```

3. **Use Same Timezone Logic Everywhere**
```sql
-- If pg_cron uses:
'CALL my_procedure(date_trunc(''day'', NOW() AT TIME ZONE ''UTC'')::date);'

-- Interactive should use:
CALL my_procedure(date_trunc('day', NOW() AT TIME ZONE 'UTC')::date);
```

**Bottom Line**: Yes, results can differ if you're using timezone-dependent date generation like `CURRENT_DATE`. To avoid issues, always be explicit about timezones when passing dates between different contexts.
