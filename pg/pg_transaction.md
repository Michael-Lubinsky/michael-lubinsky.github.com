https://habr.com/ru/articles/961134/

https://habr.com/ru/companies/otus/articles/968212/

https://habr.com/ru/companies/postgrespro/articles/504498/ Locks

```sql
CREATE OR REPLACE PROCEDURE gold.backfill_all()
LANGUAGE plpgsql
AS $$
DECLARE
  window_start timestamptz;
BEGIN
  FOR window_start IN
    SELECT generate_series(
      '2025-09-11 21:45:00+00'::timestamptz,
      '2025-10-20 00:30:00+00'::timestamptz,
      '15 minutes'
    )
  LOOP
    RAISE NOTICE 'Processing window_start = %', window_start;
    BEGIN
      CALL gold.qos_15min_backfill(window_start);
    EXCEPTION WHEN OTHERS THEN
      RAISE NOTICE 'Failed window_start = %, SQLSTATE=%, error=%',
        window_start, SQLSTATE, SQLERRM;
      -- subtransaction auto-rolls back this iteration
    END;
  END LOOP;

  COMMIT;  -- commits all successful iterations together
END;
$$;
```
The error in your PostgreSQL stored procedure output, `cannot commit while a subtransaction is active` (SQLSTATE 2D000), occurs because the `COMMIT` statement at the end of the `gold.backfill_all` procedure conflicts with the subtransaction created by the `BEGIN ... EXCEPTION` block inside the loop. In PostgreSQL, a `BEGIN ... EXCEPTION` block creates a subtransaction, and you cannot issue a `COMMIT` at the procedure level while subtransactions are active or partially rolled back.

### Why the Error Happens
- The `BEGIN ... EXCEPTION` block in the loop creates a subtransaction for each call to `gold.qos_15min_backfill(window_start)`.
- If an exception occurs, the subtransaction is automatically rolled back for that iteration, but the outer transaction (initiated implicitly by the procedure) remains active.
- The `COMMIT` at the end of the procedure attempts to commit the outer transaction, but PostgreSQL detects that subtransactions were used, leading to the error `cannot commit while a subtransaction is active`.
- This error suggests that the transaction state is inconsistent due to the interplay between the subtransactions and the explicit `COMMIT`.

Additionally, the timestamps in the output (e.g., `2025-09-11 16:45:00-07`) show a timezone offset of `-07`, while the procedure uses UTC (`+00`). This indicates that the session or database timezone is converting the timestamps, which may cause confusion but is not directly related to the error.

### Fix the Procedure
To resolve the issue, you need to avoid the explicit `COMMIT` in the procedure, as PostgreSQL procedures manage transactions differently. Procedures in PostgreSQL operate within a single transaction by default, and the transaction is committed automatically when the procedure completes successfully. Explicit `COMMIT` statements are generally not needed unless you’re using autonomous transactions or specific transaction control, which requires a different approach.

Here’s the corrected version of the procedure:

```sql
CREATE OR REPLACE PROCEDURE gold.backfill_all()
LANGUAGE plpgsql
AS $$
DECLARE
  window_start timestamptz;
BEGIN
  FOR window_start IN
    SELECT generate_series(
      '2025-09-11 21:45:00+00'::timestamptz,
      '2025-10-20 00:30:00+00'::timestamptz,
      '15 minutes'
    )
  LOOP
    RAISE NOTICE 'Processing window_start = %', window_start;
    BEGIN
      CALL gold.qos_15min_backfill(window_start);
    EXCEPTION WHEN OTHERS THEN
      RAISE NOTICE 'Failed window_start = %, SQLSTATE=%, error=%',
        window_start, SQLSTATE, SQLERRM;
      -- Subtransaction auto-rolls back this iteration, continue with next
    END;
  END LOOP;
  -- Remove the COMMIT statement
END;
$$;
```

### Changes Made
1. **Removed the `COMMIT` Statement**: The explicit `COMMIT` at the end of the procedure was removed. In PostgreSQL, a procedure’s transaction is committed automatically when the procedure completes without errors. The `BEGIN ... EXCEPTION` blocks handle errors for individual iterations, and the outer transaction remains intact.
2. **No Other Changes Needed**: The rest of the procedure, including the loop and exception handling, is correct for iterating over time windows and calling `gold.qos_15min_backfill`. The exception handling ensures that failures in one iteration don’t stop the entire procedure.

### Additional Considerations
- **Timezone Handling**: The output shows timestamps in `-07` (likely PDT), while the `generate_series` uses `+00` (UTC). This is due to the session’s timezone setting. To ensure consistent output, you can explicitly set the timezone in the procedure or format the output. For example:
  ```sql
  RAISE NOTICE 'Processing window_start = %', window_start AT TIME ZONE 'UTC';
  ```
  Alternatively, set the session timezone before running the procedure:
  ```sql
  SET TIME ZONE 'UTC';
  CALL gold.backfill_all();
  ```
- **Error Handling in `qos_15min_backfill`**: Ensure that the `gold.qos_15min_backfill` procedure does not issue its own `COMMIT` or `ROLLBACK`, as this could also interfere with the outer transaction. If it does, you may need to refactor it to avoid transaction control statements.
- **Performance**: The procedure processes a large number of 15-minute windows (from September 11, 2025, to October 20, 2025, which is approximately 4,608 iterations). Ensure that `gold.qos_15min_backfill` is optimized, as repeated calls could be resource-intensive.
- **Logging**: The `RAISE NOTICE` statements are useful for debugging but may generate significant output. Consider logging errors to a table for production use:
  ```sql
  INSERT INTO gold.backfill_errors (window_start, sqlstate, error_message)
  VALUES (window_start, SQLSTATE, SQLERRM);
  ```

### Expected Output
After removing the `COMMIT`, the procedure should run without the `cannot commit while a subtransaction is active` error. The output will look like:

```
Processing window_start = 2025-09-11 21:45:00+00
Processing window_start = 2025-09-11 22:00:00+00
Failed window_start = 2025-09-11 22:00:00+00, SQLSTATE=..., error=...
Processing window_start = 2025-09-11 22:15:00+00
...
```

If errors occur in `gold.qos_15min_backfill`, they will be caught and logged, and the loop will continue.

### If You Need Explicit Transaction Control
If `gold.qos_15min_backfill` requires its own transaction (e.g., to commit each window independently), you would need to use a different approach, such as calling it from a script or function that manages transactions explicitly, or modifying `qos_15min_backfill` to use autonomous transactions (if supported in your PostgreSQL version). However, this is likely unnecessary based on the current structure.

If you have further details about `gold.qos_15min_backfill` or specific requirements (e.g., independent commits per iteration), let me know, and I can tailor the solution further!


Yes, both your **original stored procedure** and the **corrected stored procedure** operate as a **single transaction** in PostgreSQL. Let me explain why and clarify the differences in transaction behavior between the two.

### Your Original Stored Procedure: Single Transaction
Your original stored procedure (`gold.backfill_all`) is written as follows:

```sql
CREATE OR REPLACE PROCEDURE gold.backfill_all()
LANGUAGE plpgsql
AS $$
DECLARE
  window_start timestamptz;
BEGIN
  FOR window_start IN
    SELECT generate_series(
      '2025-09-11 21:45:00+00'::timestamptz,
      '2025-10-20 00:30:00+00'::timestamptz,
      '15 minutes'
    )
  LOOP
    RAISE NOTICE 'Processing window_start = %', window_start;
    BEGIN
      CALL gold.qos_15min_backfill(window_start);
    EXCEPTION WHEN OTHERS THEN
      RAISE NOTICE 'Failed window_start = %, SQLSTATE=%, error=%',
        window_start, SQLSTATE, SQLERRM;
      -- subtransaction auto-rolls back this iteration
    END;
  END LOOP;
  COMMIT;  -- commits all successful iterations together
END;
$$;
```

**Transaction Behavior**:
- In PostgreSQL, a stored procedure runs within a **single transaction** by default unless explicit transaction control (e.g., `COMMIT` or `ROLLBACK`) is used to manage subtransactions or autonomous transactions.
- The `BEGIN ... EXCEPTION` blocks inside the `FOR` loop create **subtransactions** for each call to `gold.qos_15min_backfill`. If an exception occurs, the subtransaction for that iteration is rolled back, but the **outer transaction** (encompassing the entire procedure) remains active.
- The `COMMIT` statement at the end attempts to commit the entire outer transaction, which includes all successful calls to `gold.qos_15min_backfill`. However, this causes the error `cannot commit while a subtransaction is active` because the subtransactions (from `BEGIN ... EXCEPTION`) leave the transaction state in a way that conflicts with the explicit `COMMIT`.
- Despite the error, the procedure is still a **single transaction**. If the procedure completes without errors (or if the `COMMIT` were removed), all changes made by `gold.qos_15min_backfill` across all iterations would be committed together when the procedure ends, or rolled back entirely if an unhandled error occurs outside the `BEGIN ... EXCEPTION` blocks.

**Why It’s a Single Transaction**:
- PostgreSQL procedures do not implicitly commit after each iteration or subprocedure call.
- The `COMMIT` statement in your procedure is invalid due to the subtransaction state, but even without it, the procedure’s work is part of one transaction that is committed automatically when the procedure completes successfully.

### Corrected Stored Procedure: Single Transaction
The corrected version of the procedure removes the problematic `COMMIT`:

```sql
CREATE OR REPLACE PROCEDURE gold.backfill_all()
LANGUAGE plpgsql
AS $$
DECLARE
  window_start timestamptz;
BEGIN
  FOR window_start IN
    SELECT generate_series(
      '2025-09-11 21:45:00+00'::timestamptz,
      '2025-10-20 00:30:00+00'::timestamptz,
      '15 minutes'
    )
  LOOP
    RAISE NOTICE 'Processing window_start = %', window_start;
    BEGIN
      CALL gold.qos_15min_backfill(window_start);
    EXCEPTION WHEN OTHERS THEN
      RAISE NOTICE 'Failed window_start = %, SQLSTATE=%, error=%',
        window_start, SQLSTATE, SQLERRM;
      -- Subtransaction auto-rolls back this iteration
    END;
  END LOOP;
  -- COMMIT removed
END;
$$;
```

**Transaction Behavior**:
- Like the original, this procedure runs as a **single transaction**.
- The `BEGIN ... EXCEPTION` blocks still create subtransactions for each call to `gold.qos_15min_backfill`. If an error occurs in one iteration, the subtransaction for that iteration is rolled back, but the outer transaction continues.
- Without the explicit `COMMIT`, the procedure relies on PostgreSQL’s default behavior: the entire transaction (including all successful `gold.qos_15min_backfill` calls) is committed automatically when the procedure completes successfully.
- If an unhandled error occurs outside the `BEGIN ... EXCEPTION` blocks (e.g., in the `generate_series` loop itself), the entire transaction is rolled back.

**Why It’s Still a Single Transaction**:
- Removing the `COMMIT` eliminates the error but doesn’t change the fact that the procedure operates within one transaction.
- All changes made by `gold.qos_15min_backfill` across all iterations are part of the same transaction, committed together when the procedure ends or rolled back if an unhandled error occurs.

### Key Differences
- **Original Procedure**: Attempts an explicit `COMMIT`, which fails due to subtransactions, causing the error `cannot commit while a subtransaction is active`. Despite this, it’s still a single transaction, but the error may prevent successful completion.
- **Corrected Procedure**: Removes the `COMMIT`, allowing the procedure to complete without errors. It remains a single transaction, with PostgreSQL handling the commit automatically at the end.

### Implications of a Single Transaction
- **Pros**:
  - Ensures atomicity: either all successful `gold.qos_15min_backfill` calls are committed, or none are (if an unhandled error occurs).
  - Subtransactions (`BEGIN ... EXCEPTION`) allow individual iterations to fail without aborting the entire procedure.
- **Cons**:
  - A single transaction for ~4,608 iterations (from September 11, 2025, to October 20, 2025, at 15-minute intervals) can be resource-intensive, holding locks and consuming memory for the duration of the procedure.
  - If an unhandled error occurs outside the exception blocks, all work is rolled back, which could be costly for long-running processes.

### If You Want Independent Transactions
If you need each `gold.qos_15min_backfill` call to commit independently (i.e., not as a single transaction), you have a few options:
1. **Call the Procedure in a Script**: Use a client-side script (e.g., in Python with `psycopg2`) to loop over the time windows, calling `gold.qos_15min_backfill` with a separate transaction for each iteration:

   ```python
   import psycopg2
   from datetime import datetime, timedelta

   conn = psycopg2.connect("dbname=your_db")
   cursor = conn.cursor()
   start = datetime(2025, 9, 11, 21, 45, tzinfo=timezone.utc)
   end = datetime(2025, 10, 20, 0, 30, tzinfo=timezone.utc)
   step = timedelta(minutes=15)

   current = start
   while current <= end:
       try:
           cursor.execute("CALL gold.qos_15min_backfill(%s)", (current,))
           conn.commit()
       except Exception as e:
           print(f"Failed window_start = {current}, error = {e}")
           conn.rollback()
       current += step
   conn.close()
   ```
2. **Use dblink for Autonomous Transactions**: Use the `dblink` extension to call `gold.qos_15min_backfill` in a separate connection, allowing independent commits. This is complex and requires `dblink` to be installed.
3. **Modify `qos_15min_backfill`**: If possible, refactor `gold.qos_15min_backfill` to handle its own transaction management, but this depends on its implementation.

### Conclusion
- **Original Procedure**: Single transaction, but fails due to invalid `COMMIT`.
- **Corrected Procedure**: Single transaction, works correctly with automatic commit at the end.
- If you want independent transactions for each `gold.qos_15min_backfill` call, you’ll need to use a client-side script or a mechanism like `dblink`.

Let me know if you need help implementing independent transactions or further details on `gold.qos_15min_backfill`!


Short answer: that error means PostgreSQL won’t let you use `START TRANSACTION`/`COMMIT` inside a PL/pgSQL procedure block the way we tried. In PL/pgSQL, transaction control is **not supported inside the block**—you’ll see “unsupported transaction command”.

You have three workable patterns:

1. Accept one big transaction (simple, but risky for long ranges)
   – Your last version (no commits inside the inner block, one `COMMIT` at the end) avoids the error, but all progress is lost if anything fails before the final commit.

2. Per-iteration commits via a client loop (recommended + simplest)
   Run each window as its own top-level `CALL` from the client/shell so each call is its own transaction:

```bash
# bash + psql loop (UTC example)
start='2025-09-11 21:45:00+00'
end='2025-10-20 00:30:00+00'

current="$start"
while : ; do
  psql "dbname=weavix host=weavix-prod-pg.postgres.database.azure.com sslmode=require" \
       -v ON_ERROR_STOP=1 \
       -c "CALL gold.qos_15min_backfill('$current'::timestamptz);"

  if [ "$(date -u -d "$current" +%s)" -ge "$(date -u -d "$end" +%s)" ]; then
    break
  fi
  current=$(date -u -d "$current +15 minutes" +"%Y-%m-%d %H:%M:%S+00")
done
```

3. Per-iteration commits inside the server using dblink (works because each dblink_exec runs on a separate connection/transaction)
   This keeps the loop in the database but isolates each iteration on its own session so failures don’t roll back others.

```sql
-- enable the extension once per DB
CREATE EXTENSION IF NOT EXISTS dblink;

CREATE OR REPLACE PROCEDURE gold.backfill_all_dblink()
LANGUAGE plpgsql
AS $$
DECLARE
  window_start timestamptz;
  cmd text;
BEGIN
  -- Reuse a single dblink connection name
  PERFORM dblink_disconnect('local') WHERE EXISTS (
    SELECT 1 FROM pg_catalog.pg_foreign_server WHERE srvname = 'local'
  );
  PERFORM dblink_connect('local', 'host=localhost dbname=weavix');  -- adjust if DB name differs

  FOR window_start IN
    SELECT generate_series(
      '2025-09-11 21:45:00+00'::timestamptz,
      '2025-10-20 00:30:00+00'::timestamptz,
      '15 minutes'
    )
  LOOP
    RAISE NOTICE 'Processing window_start = %', window_start;

    cmd := format($f$
      CALL gold.qos_15min_backfill(%L::timestamptz)
    $f$, window_start);

    BEGIN
      -- Each exec runs as its own statement/transaction on the remote session.
      PERFORM dblink_exec('local', cmd);
    EXCEPTION WHEN OTHERS THEN
      RAISE WARNING 'Failed window_start = %, SQLSTATE=%, error=%',
        window_start, SQLSTATE, SQLERRM;
      -- continue to next window
    END;
  END LOOP;

  PERFORM dblink_disconnect('local');
END;
$$;

-- run it
CALL gold.backfill_all_dblink();
```

Notes

* dblink approach gives you per-iteration durability without client scripting. Each `dblink_exec` is its own remote transaction unless you explicitly send `BEGIN`/`COMMIT` over dblink.
* If your `gold.qos_15min_backfill()` isn’t idempotent, ensure it uses `ON CONFLICT DO NOTHING/UPDATE` to avoid duplicates when re-running windows.
* If you really want to keep everything inside a single server-side object without dblink, use **pg_cron** to enqueue one job per window (each job is its own top-level transaction).

TL;DR

* The “unsupported transaction command” is expected with PL/pgSQL.
* Use a shell/psql loop or dblink to get safe per-iteration commits; otherwise accept a single large transaction.

