### Rest API for Postgres
https://www.prestd.com/

https://docs.postgrest.org/

## Time Zone

Best practice - Store times in UTC, display in user's local timezone

Summary: GMT is the time at 0° longitude with no DST adjustments. It's effectively the same as UTC for practical purposes, and it's the reference point for all other timezones worldwide. When working with databases and scheduling, using GMT/UTC helps avoid timezone-related bugs.

SET timezone = 'GMT';
-- or
SET timezone = 'UTC';


### postgres_fdw  

<https://packagemain.tech/p/mastering-cross-database-operations-with-postgres-fdw>

```sql

CREATE EXTENSION postgres_fdw;

CREATE SERVER weavix_remote
  FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host 'localhost', dbname 'weavix', port '5432');


CREATE USER MAPPING FOR current_user
  SERVER weavix_remote
  OPTIONS (user 'weavix_user', password 'secret');


IMPORT FOREIGN SCHEMA public
  FROM SERVER weavix_remote
  INTO foreign_schema;

-- or

CREATE FOREIGN TABLE foreign_schema.events (
  id INT,
  name TEXT,
  created_at TIMESTAMP
)
SERVER weavix_remote
OPTIONS (schema_name 'public', table_name 'events');


SELECT * FROM foreign_schema.customers WHERE city = 'London';

SELECT cron.schedule(
    'cross_db_job',
    '0 * * * *', -- Every hour
    $$SELECT * FROM foreign_table_name WHERE condition$$
);
```

| Feature      | Description                                                              |
| ------------ | ------------------------------------------------------------------------ |
| Type         | **Foreign Data Wrapper** (SQL standard extension)                        |
| Setup        | Create foreign server + user mapping + foreign tables                    |
| Usage        | You can `SELECT`, `INSERT`, `UPDATE`, `DELETE` foreign tables like local |
| Integration  | Native with PostgreSQL query planner                                     |
| Performance  | Supports **pushdown** of filters, joins, aggregates to the remote server |
| Use in joins | ✅ Yes, join foreign + local tables in one query                          |
| Syntax       | Normal SQL: `SELECT * FROM foreign_table`                                |
| Extension    | `CREATE EXTENSION postgres_fdw;`                                         |


### db_link 

| Feature      | Description                                                  |
| ------------ | ------------------------------------------------------------ |
| Type         | Legacy PostgreSQL extension                                  |
| Setup        | Connect manually with connection strings in each query       |
| Usage        | You write queries **as strings** to be sent to the remote DB |
| Integration  | No query planner integration — pure function call            |
| Performance  | ❌ No pushdown — fetches all rows as text                     |
| Use in joins | ❌ Hard to join with local tables                             |
| Syntax       | Verbose: `SELECT * FROM dblink('conn_str', 'SELECT ...')`    |
| Extension    | `CREATE EXTENSION dblink;`                                   |


```sql
SELECT *
FROM dblink('dbname=remote_db user=remote_user password=secret',
            'SELECT id, name FROM customers WHERE city = ''London''')
  AS t(id INT, name TEXT);
```


  | Scenario                               | Use                                           |
| -------------------------------------- | --------------------------------------------- |
| Clean, seamless cross-db integration   | `postgres_fdw` ✅                              |
| Frequent cross-db joins                | `postgres_fdw` ✅                              |
| Legacy setups or quick one-off queries | `dblink`                                      |
| Need full SQL access in remote DB      | `dblink` or `postgres_fdw` with function call |






### pg_cron extension

 You cannot use pg_cron in 2 databases. 
 pg_cron runs a single background worker.  

That worker reads jobs only from the database you configure in postgresql.conf as:

```ini
shared_preload_libraries = 'pg_cron'
cron.database_name = 'weavix'
```
cron.database_name setting is not present by default in postgresql.conf.   
You need to manually add it if you want to use pg_cron with a database other than postgres

Show all scheduled cron jobs
```sql
SELECT * FROM cron.job;
```

Show only currently running jobs:
```sql
SELECT * FROM cron.job_run_details
WHERE end_time IS NULL
ORDER BY start_time DESC;
```

Show completed jobs (history:
```sql
SELECT * FROM cron.job_run_details
WHERE end_time IS NOT NULL
ORDER BY end_time DESC
LIMIT 10;
```

Show jobs and their schedule with next run:
```sql
SELECT jobid, schedule, command, nodename, nodeport, database, username, active
FROM cron.job
ORDER BY jobid;
```
pg_cron argument explained
```
0  0  *  *  *
│  │  │  │  │
│  │  │  │  └── Day of week (0-7, * = every day)
│  │  │  └───── Month (1-12, * = every month)
│  │  └──────── Day of month (1-31, * = every day)
│  └──────────── Hour (0-23, 0 = midnight/12 AM)
└─────────────── Minute (0-59, 0 = top of hour)

```

Show failed jobs:
```sql
SELECT
  j.jobid,
  j.schedule,
  j.command,
  d.start_time,
  d.end_time,
  d.status,
  d.return_code,
  d.stdout,
  d.stderr
FROM cron.job j
JOIN cron.job_run_details d ON j.jobid = d.jobid
WHERE d.status != 'succeeded'
ORDER BY d.start_time DESC
LIMIT 20;
```



Tables used by pg_cron:

| Table                  | Description                    |
| ---------------------- | ------------------------------ |
| `cron.job`             | All configured cron jobs       |
| `cron.job_run_details` | Execution history for all jobs |



you cannot run a query from one database that references another.

If you must keep pg_cron in the postgres DB but want to run queries in weavix, 
use the dblink extension.

1. Enable dblink:
In postgres database:

```sql
CREATE EXTENSION dblink;
```
2. Use it inside pg_cron jobs:
```sql
SELECT cron.schedule(
  'daily_weavix_job',
  '0 1 * * *',
  $$
  SELECT * FROM dblink('dbname=weavix',
    'INSERT INTO silver.daily_counts SELECT ... FROM bronze.events ...'
  ) AS t(dummy int);
  $$
);
```
⚠️ But this requires:

- weavix allows TCP connections from localhost  
- Authentication is correctly set up in .pgpass or via pg_hba.conf



### pg_cron.schedule_in_database()
Modern versions of pg_cron (v1.4 and above, which is highly likely for PostgreSQL 16)  
include a function specifically for this: cron.schedule_in_database().   
This function is designed to handle scheduling jobs in databases other than the one where pg_cron itself is installed.   
It simplifies the process significantly because pg_cron handles the internal connection to the target database.

```sql
SELECT cron.schedule_in_database(
    job_name TEXT,
    schedule TEXT,
    command TEXT,
    database_name TEXT,
    username TEXT DEFAULT NULL,
    active BOOLEAN DEFAULT TRUE
);
```
Example:

If pg_cron is in Database A and you want to run CALL my_procedure_in_db_b() in Database B:  
Run this from Database A (where pg_cron is installed)

```sql

SELECT cron.schedule_in_database(
    'daily_procedure_b',
    '0 3 * * *', -- Run daily at 3:00 AM
    'CALL my_procedure_in_db_b();',
    'DatabaseB', -- The name of the target database
    'your_user_for_db_b' -- User with permissions in DatabaseB
);
```
Why pg_cron.schedule_in_database() is preferred (if available):

Native Integration:   
It's the most direct and intended way to schedule jobs across databases using pg_cron.

Simplicity:   
You don't need to manually manage foreign servers or dblink connections within your cron job command. pg_cron handles the connection internally.

Security:   
pg_cron typically re-establishes a new connection for each job execution. 
You specify the username directly in schedule_in_database(), which can be more secure than hardcoding dblink connection strings everywhere.

Performance:   
While pg_cron still makes a new connection, it's optimized for this use case and avoids the overhead of FDW table scanning or potentially inefficient dblink query parsing.

**Alternatives if pg_cron.schedule_in_database() is Not Available**  

If your pg_cron version is older than 1.4 or you have a very specific scenario that isn't covered by schedule_in_database(), you could consider these options:

##### Alternative 1:  dblink (More likely for ad-hoc SQL/procedures)
   
You would create a cron.schedule() entry that uses dblink() to connect to Database B and execute the SQL or stored procedure.
 This means your pg_cron job command would look something like this:

```sql

SELECT cron.schedule(
    'my_db_b_job',
    '0 3 * * *',
    $$SELECT dblink('host=localhost user=your_user dbname=DatabaseB password=your_password',
    'CALL my_procedure_in_db_b()');$$
);


SELECT cron.schedule(
    'call_procedure',
    '0 * * * *', -- Every hour
    $$SELECT dblink_exec(
        'dbname=target_db host=localhost port=5432 user=your_user password=your_password',
        'CALL procedure_name()'
    )$$
);


SELECT cron.schedule(
    'cross_db_job',
    '0 * * * *', -- Every hour
    $$SELECT * FROM dblink(
        'dbname=target_db host=localhost port=5432 user=your_user password=your_password',
        'SELECT * FROM table_name WHERE condition'
    ) AS t(column1 datatype, column2 datatype)$$
);
```

Caveats:

Less intuitive for complex queries (results are returned as text or record sets).  
No direct table integration (cannot join with local tables easily).

Security Risk: Hardcoding passwords in the cron.schedule command is a major security risk. Ideally, you'd rely on .pgpass files or other secure credential management for the user pg_cron runs as.

Performance: dblink can be less performant for complex operations than postgres_fdw if you were trying to join tables between databases. However, for simply calling a stored procedure or executing a single SQL statement, it's often sufficient.

##### Alternative 2: postgres_fdw (Less direct for calling a procedure, but possible for table access)

You would need to set up postgres_fdw in Database A, creating a foreign server definition pointing to Database B (on localhost or 127.0.0.1), and user mappings.   
Then, you'd create foreign tables in Database A that represent the tables in Database B.

If you needed to run a stored procedure, you might have to create a wrapper function in Database A that calls a dblink_exec to run the procedure on the foreign server, or rethink the design if direct table access via FDW is sufficient.

Complexity: Setting up FDWs just to call a stored procedure in another database on the same instance is generally overkill compared to pg_cron.schedule_in_database() or even dblink().   
FDW shines when you need to query and join foreign tables directly from your local database.

### Conclusion
Always check if your pg_cron version supports cron.schedule_in_database(). If it does, that's the clearest and most robust solution.

If you are on an older pg_cron version that lacks schedule_in_database(),   
then dblink is the more straightforward choice for executing ad-hoc SQL or calling stored procedures in another database directly from a pg_cron job, with the important caveat of secure credential management.   
postgres_fdw is typically not the primary choice for simply executing code in another database, but rather for accessing data as if it were local.

# Question: in which timezone pg_cron 7:00 am ?

select schedule, command, database, jobname from cron.job ; |0 7 * * * |call gold.perform_yesterdays_aggregations(); Here '0 7 * * *' means 7:00 am daily. Question: in which timezone 7:00 am ?


Short answer: **UTC**—unless you (or your admin) have explicitly set pg\_cron’s own timezone.

* By default, `pg_cron` runs schedules in **GMT/UTC**. Recent versions let you override this with the `cron.timezone` GUC in `postgresql.conf`. ([GitHub][1], [Neon][2])

## How to check what yours is using

Run one of these in your DB:

```sql
-- Shows pg_cron-specific settings (including cron.timezone if available)
SELECT name, setting FROM pg_settings WHERE name LIKE 'cron.%';

-- Directly check the timezone setting (NULL/empty means not set; default is GMT/UTC)
SELECT current_setting('cron.timezone', true) AS cron_timezone;

-- See which pg_cron version you have (older versions were UTC-only)
SELECT extversion FROM pg_extension WHERE extname = 'pg_cron';
```

* If `cron.timezone` exists and has a value (e.g., `America/Chicago`), your `0 7 * * *` runs at **07:00 in that zone**.
* If `cron.timezone` is absent or empty, it runs at **07:00 UTC**. ([GitHub][1], [Neon][2])

## How to change it (if you have access)

Add to `postgresql.conf`, then restart PostgreSQL:

```conf
# Run all pg_cron schedules in this zone
cron.timezone = 'America/Los_Angeles'
```

Note: some managed services may not expose `cron.timezone` yet (it’s supported starting with newer pg\_cron/PostgreSQL versions). In those cases, leave it at UTC and adjust your cron expressions accordingly. ([Scaleway][3])

So your job:

```
0 7 * * *  call gold.perform_yesterdays_aggregations();
```

fires at **07:00 in `cron.timezone`**, or **07:00 UTC** if that setting isn’t configured.

[1]: https://github.com/citusdata/pg_cron?utm_source=chatgpt.com "citusdata/pg_cron: Run periodic jobs in PostgreSQL"
[2]: https://neon.com/docs/extensions/pg_cron?utm_source=chatgpt.com "The pg_cron extension - Neon Docs"
[3]: https://www.scaleway.com/en/docs/managed-databases-for-postgresql-and-mysql/api-cli/using-pgcron/?utm_source=chatgpt.com "Setting up and using the pg_cron extension"



Correct — **pg_cron can only be installed in the `postgres` database** (it uses a shared background worker tied to that DB).
This means **all scheduled jobs execute in the context of the `postgres` database**, not others — unless you explicitly connect elsewhere via `dblink`, `postgres_fdw`, or similar.

So your logic is right that you can’t move the cron job itself to `weavix`, but your proposed code still needs a small correction:

---

### ✅ Corrected version (works under pg_cron-in-postgres restriction)

```sql
-- Step 1: Drop the unused proxy procedure if it exists in 'postgres'
DROP PROCEDURE IF EXISTS proxy_seats_used_last_month();

-- Step 2: Schedule a job that runs dblink_exec directly
-- Remember: PERFORM is invalid outside PL/pgSQL, use SELECT instead
SELECT cron.schedule(
    'Run Calculate Gold Seats Used Monthly',
    '0 15 1 * *',
    $$
      SELECT dblink_exec(
        'host=localhost dbname=weavix user=cron_runner password=<the cron_runner password>',
        'CALL gold.seats_used_monthly(' ||
        'date_trunc(''month'', now() - interval ''1 month'')::date, ' ||
        'date_trunc(''month'', now())::date);'
      );
    $$
);
```

---

### 🔍 Key details

1. **`PERFORM` → `SELECT`**
   `pg_cron` executes SQL, not PL/pgSQL, so `PERFORM` will cause:

   ```
   ERROR: syntax error at or near "PERFORM"
   ```

   Use `SELECT dblink_exec(...)` instead.

2. **Ensure `dblink` is installed in the `postgres` DB**

   ```sql
   \c postgres
   CREATE EXTENSION IF NOT EXISTS dblink;
   ```

3. **Secure credentials**
   Instead of hardcoding the password, consider:

   * a `FOREIGN SERVER` + `USER MAPPING` using `postgres_fdw`, or
   * a `.pgpass` file for `cron_runner` if your hosting platform allows local loopback auth.

4. **Confirm local connectivity**
   Some managed services (like Azure Database for PostgreSQL) **don’t allow `localhost` connections**, even internally.
   In that case, replace `'host=localhost'` with the full server name:

   ```
   'host=weavix-dev-pg.postgres.database.azure.com ...'
   ```

5. **Time zone**
   The cron time `'0 15 1 * *'` is **15:00 UTC**, which executes at 8 AM Pacific / 10 AM Central, depending on DST.

---

### ✅ Final recommendation

Your corrected and safe final setup (minimal privileges):

```sql
CREATE EXTENSION IF NOT EXISTS dblink;

SELECT cron.schedule(
  'Run Calculate Gold Seats Used Monthly',
  '0 15 1 * *',
  $$
    SELECT public.dblink_exec(
      'host=weavix-dev-pg.postgres.database.azure.com dbname=weavix user=cron_runner password=<secret>',
      'CALL gold.seats_used_monthly(' ||
      'date_trunc(''month'', now() - interval ''1 month'')::date, ' ||
      'date_trunc(''month'', now())::date);'
    );
  $$
);
```

✅ This version:

* runs safely from `postgres` (the only pg_cron-compatible DB),
* uses plain SQL (no PL/pgSQL),
* directly executes your monthly stored procedure in the correct target DB.


  Since you’ve executed that `cron.schedule(...)`, here’s how to quickly verify it’s correct, test it immediately, and fix the most common issues (especially on Azure Postgres).

1. Confirm the job was created and capture the job id

```sql
SELECT jobid, schedule, command
FROM cron.job
WHERE jobname = 'Run Calculate Gold Seats Used Monthly';
```

2. Dry-run the statement once, right now (no waiting for the cron tick)

```sql
-- replace :jobid with the value from step 1
SELECT cron.run_job(:jobid);
```

3. Inspect the result/any errors

```sql
SELECT *
FROM cron.job_run_details
WHERE jobid = :jobid
ORDER BY start_time DESC
LIMIT 5;
```

If it failed, the most common culprits are below, with fixes.

---

Common fixes (Azure Postgres friendly)

A) Make sure `dblink` exists in the **postgres** database (where pg_cron runs)

```sql
\c postgres
CREATE EXTENSION IF NOT EXISTS dblink;
```

B) Use a single literal (no need for `||`) and add Azure flags (port + SSL).
Azure Flexible/Single Server typically requires `sslmode=require` and often uses the `user@servername` username format.

```sql
SELECT cron.schedule(
  'Run Calculate Gold Seats Used Monthly',
  '0 15 1 * *',
  $$
    SELECT public.dblink_exec(
      'host=weavix-dev-pg.postgres.database.azure.com port=5432 dbname=weavix user=cron_runner@weavix-dev-pg password=<secret> sslmode=require',
      'CALL gold.seats_used_monthly('''
        || 'date_trunc(''month'', now() - interval ''1 month'')::date'
        || ',' 
        || 'date_trunc(''month'', now())::date'
        || ');'
    );
  $$
);
```

Or, simpler (single literal entirely; same effect):

```sql
SELECT cron.schedule(
  'Run Calculate Gold Seats Used Monthly',
  '0 15 1 * *',
  $$
    SELECT public.dblink_exec(
      'host=weavix-dev-pg.postgres.database.azure.com port=5432 dbname=weavix user=cron_runner@weavix-dev-pg password=<secret> sslmode=require',
      'CALL gold.seats_used_monthly(''date_trunc(''''month'''', now() - interval ''''1 month'''')::date'',''date_trunc(''''month'''', now())::date'');'
    );
  $$
);
```

Notes:

* If you installed `dblink` into a schema other than `public`, call it as `that_schema.dblink_exec(...)`.
* If your server requires an SSL root cert, you may also need `sslrootcert=/path/to/BaltimoreCyberTrustRoot.crt.pem`.

C) Verify the target procedure exists in `weavix.gold` and has `(date,date)` signature

```sql
SELECT n.nspname AS schema, p.proname, pg_get_function_identity_arguments(p.oid) AS args
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE p.prokind = 'p'
  AND n.nspname = 'gold'
  AND p.proname = 'seats_used_monthly';
```

You should see a row with `args = 'date, date'`.

D) Make sure the `pg_cron` role (the user you used to create the job; often your admin role) can execute:

```sql
GRANT USAGE ON SCHEMA gold TO weavix_admin;
GRANT EXECUTE ON PROCEDURE gold.seats_used_monthly(date, date) TO weavix_admin;
```

E) Quick connectivity sanity-check (run in `postgres`)

```sql
SELECT dblink_connect(
  'wconn',
  'host=weavix-dev-pg.postgres.database.azure.com port=5432 dbname=weavix user=cron_runner@weavix-dev-pg password=<secret> sslmode=require'
);
SELECT dblink_exec('wconn', 'SELECT 1');
SELECT dblink_disconnect('wconn');
```

If `dblink_connect` fails, check the username format, password, firewall rules, and SSL settings.

---

Run it now to confirm end-to-end

```sql
-- after (re)scheduling:
SELECT jobid FROM cron.job WHERE jobname = 'Run Calculate Gold Seats Used Monthly';
SELECT cron.run_job(:jobid);
SELECT * FROM cron.job_run_details WHERE jobid = :jobid ORDER BY start_time DESC LIMIT 5;
```

If you paste any error text you see in `job_run_details.return_message`, I’ll pinpoint the exact fix (escaping, auth, SSL, or permissions).
