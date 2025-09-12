Write the bash script pgtool.sh for backup and recovery postgres table. 
It could be a full or partial content of the table.
Output format: csv (optionally - compressed by gzip).

It should be possible to dump just part of the table based on  
date range filter applied to some column. 

Script should accept command line arguments:
- postgres instance (dev or prod or test or local)
- full table name (example: weavix.silver.mytable)
- optional: column with timestamptz datatype
- optional: date in format YYYY-MM-DD or YYYY-MM
- optional: compress it or not (default: compress)
- optional: destination folder (default folder should be in the script,
  ( it depend on postgres instance name)

The output: csv or compressed csv, depending of command line flag.
The output file name is concatenation of input parameters:
- postgres instance (dev, prod, test)
- table name
- column with timestamptz datatype
- date in format YYYY-MM-DD or YYYY-MM (one day or one month)

Example of backup of 1 month:  
pgtool.sh backup dev weavix.silver.mytable 2025-01  
Output file:  /destination_folder/dev_weavix.silver.mytable_2025-01.csv

Also this script should be able to restore data to the Postgres table.
pgtool.sh restore dev  weavix.silver.mytable_timecol_2025-01.csv

The destination table should be created automatically, based on input file name 
(without suffix .csv ot csv.gz), it should include the date, if it is part of file name.

If destination table already exists then show warning.

## chat.mistral.ai

```bash
#!/bin/bash

# pgtool.sh - PostgreSQL table backup and recovery tool
# Usage:
#   Backup: ./pgtool.sh backup <instance> <table> [<time_column>] [<date>] [--no-compress] [--dest <folder>]
#   Restore: ./pgtool.sh restore <instance> <file>

set -euo pipefail

# --- Config ---
declare -A INSTANCE_CONFIG=(
    ["dev"]="user=dev_user dbname=dev_db host=dev-host port=5432"
    ["prod"]="user=prod_user dbname=prod_db host=prod-host port=5432"
    ["test"]="user=test_user dbname=test_db host=test-host port=5432"
    ["local"]="user=postgres dbname=postgres host=localhost port=5432"
)
DEFAULT_DEST_FOLDER="/var/backups/postgres"
COMPRESS=true
# --- End Config ---

function usage() {
    cat <<EOF
Usage:
  Backup: $0 backup <instance> <table> [<time_column>] [<date>] [--no-compress] [--dest <folder>]
  Restore: $0 restore <instance> <file>

  <instance>: dev, prod, test, or local
  <table>: full table name, e.g. weavix.silver.mytable
  <time_column>: column with timestamptz datatype (for date filtering)
  <date>: YYYY-MM-DD or YYYY-MM (for date filtering)
  <file>: backup file to restore
EOF
    exit 1
}

function backup() {
    local instance="$1"
    local table="$2"
    local time_column="${3:-}"
    local date_filter="${4:-}"
    local compress="${5:-true}"
    local dest_folder="${6:-${DEFAULT_DEST_FOLDER}}"

    local conn="${INSTANCE_CONFIG[$instance]}"
    if [[ -z "$conn" ]]; then
        echo "Error: Unknown instance '$instance'"
        usage
    fi

    local schema=$(echo "$table" | cut -d. -f1,2)
    local table_name=$(echo "$table" | cut -d. -f3)
    local dest_file="$dest_folder/${instance}_${table//./_}"

    if [[ -n "$time_column" && -n "$date_filter" ]]; then
        dest_file="${dest_file}_${time_column}_${date_filter}"
        local where_clause="WHERE date_trunc('day', \"$time_column\")"
        if [[ "$date_filter" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
            where_clause+=" BETWEEN '${date_filter}-01' AND '${date_filter}-01' + INTERVAL '1 month'"
        else
            where_clause+=" = '$date_filter'"
        fi
    fi

    dest_file+=".csv"

    echo "Backing up $table to $dest_file (compress: $compress)"

    local query="COPY (SELECT * FROM $table"
    [[ -n "$time_column" && -n "$date_filter" ]] && query+=" $where_clause"
    query+=") TO STDOUT WITH CSV HEADER"

    mkdir -p "$dest_folder"
    if [[ "$compress" == "true" ]]; then
        PGPASSWORD=${PGPASSWORD:-} psql "$conn" -c "$query" | gzip > "$dest_file.gz"
        echo "Backup saved to $dest_file.gz"
    else
        PGPASSWORD=${PGPASSWORD:-} psql "$conn" -c "$query" > "$dest_file"
        echo "Backup saved to $dest_file"
    fi
}

function restore() {
    local instance="$1"
    local file="$2"
    local conn="${INSTANCE_CONFIG[$instance]}"
    if [[ -z "$conn" ]]; then
        echo "Error: Unknown instance '$instance'"
        usage
    fi

    local filename=$(basename "$file")
    local table_name="${filename%.*}"
    table_name="${table_name%.*}"
    table_name="${table_name#*_}"

    local schema=$(echo "$table_name" | cut -d_ -f1,2)
    local table=$(echo "$table_name" | cut -d_ -f3-)

    # If table_name contains date, extract the base table name
    if [[ "$table" =~ ^([^_]+_[^_]+)_[^_]+_[0-9]{4}-[0-9]{2}(-[0-9]{2})?$ ]]; then
        table="${BASH_REMATCH[1]}"
    fi

    # Check if table exists
    local exists=$(PGPASSWORD=${PGPASSWORD:-} psql "$conn" -tAc "SELECT 1 FROM information_schema.tables WHERE table_schema || '.' || table_name = '$schema.$table'")
    if [[ "$exists" == "1" ]]; then
        echo "Warning: Table $schema.$table already exists. Data will be appended."
    else
        echo "Creating table $schema.$table from backup..."
        PGPASSWORD=${PGPASSWORD:-} psql "$conn" -c "CREATE TABLE IF NOT EXISTS $schema.$table (LIKE $schema.$table INCLUDING ALL);"
    fi

    if [[ "$file" == *.gz ]]; then
        gunzip -c "$file" | PGPASSWORD=${PGPASSWORD:-} psql "$conn" -c "\COPY $schema.$table FROM STDIN WITH CSV HEADER"
    else
        PGPASSWORD=${PGPASSWORD:-} psql "$conn" -c "\COPY $schema.$table FROM '$file' WITH CSV HEADER"
    fi
    echo "Data restored to $schema.$table"
}

# --- Main ---
if [[ $# -lt 2 ]]; then
    usage
fi

case "$1" in
    backup)
        shift
        local instance="$1"
        local table="$2"
        local time_column="${3:-}"
        local date_filter="${4:-}"
        local compress=true
        local dest_folder="$DEFAULT_DEST_FOLDER"

        while [[ $# -gt 0 ]]; do
            case "$1" in
                --no-compress) compress=false ;;
                --dest) dest_folder="$2"; shift ;;
            esac
            shift
        done

        backup "$instance" "$table" "$time_column" "$date_filter" "$compress" "$dest_folder"
        ;;
    restore)
        shift
        local instance="$1"
        local file="$2"
        restore "$instance" "$file"
        ;;
    *)
        usage
        ;;
esac

```

### Usage
```backup
# Full table backup (compressed)
./pgtool.sh backup dev weavix.silver.mytable

# Partial backup (by month, compressed)
./pgtool.sh backup dev weavix.silver.mytable created_at 2025-01

# Partial backup (by day, uncompressed)
./pgtool.sh backup dev weavix.silver.mytable created_at 2025-01-15 --no-compress

# Custom destination folder
./pgtool.sh backup dev weavix.silver.mytable created_at 2025-01 --dest /my/backups
```

### restore
```bash
# Restore from compressed file
./pgtool.sh restore dev /var/backups/postgres/dev_weavix_silver_mytable_created_at_2025-01.csv.gz

# Restore from uncompressed file
./pgtool.sh restore dev /var/backups/postgres/dev_weavix_silver_mytable_created_at_2025-01-15.csv


```
### GEMINI
```bash
#!/bin/bash

# ==============================================================================
# Script: pgtool.sh
# Description: A tool for backing up and restoring PostgreSQL table data.
# It supports full or partial dumps based on a date range and handles
# compression and automatic table creation on restore.
# ==============================================================================

# --- Configuration ---
# Set up a dictionary-like structure for database connection configurations.
# This assumes you have corresponding environment variables for each instance
# (e.g., PGHOST_dev, PGDATABASE_dev, etc.).
declare -A PG_CONFIG
PG_CONFIG["dev"]="PGHOST=$PGHOST_dev PGDATABASE=$PGDATABASE_dev PGUSER=$PGUSER_dev PGPASSWORD=$PGPASSWORD_dev"
PG_CONFIG["prod"]="PGHOST=$PGHOST_prod PGDATABASE=$PGDATABASE_prod PGUSER=$PGUSER_prod PGPASSWORD=$PGPASSWORD_prod"
PG_CONFIG["test"]="PGHOST=$PGHOST_test PGDATABASE=$PGDATABASE_test PGUSER=$PGUSER_test PGPASSWORD=$PGPASSWORD_test"
PG_CONFIG["local"]="PGHOST=$PGHOST_local PGDATABASE=$PGDATABASE_local PGUSER=$PGUSER_local PGPASSWORD=$PGPASSWORD_local"

# Default settings
DEFAULT_DEST_DIR="/var/backups"
DEFAULT_COMPRESS=true

# --- Helper Functions ---

# Function to display script usage
usage() {
    echo "Usage: $0 <command> <instance> <full_table_name> [options]"
    echo "Commands:"
    echo "  backup    Backup a PostgreSQL table."
    echo "  restore   Restore a PostgreSQL table from a file."
    echo ""
    echo "Backup options:"
    echo "  <full_table_name>       Required. Format: <schema>.<table_name>"
    echo "  [timestamptz_column]    Optional. Column for date filtering."
    echo "  [date]                  Optional. YYYY-MM-DD or YYYY-MM for filtering."
    echo "  --no-compress           Optional. Do not compress the output file."
    echo "  --dest-dir <path>       Optional. Destination folder."
    echo ""
    echo "Restore options:"
    echo "  <backup_file>           Required. Path to the backup file (.csv or .csv.gz)."
    echo ""
    exit 1
}

# --- Main Logic ---

# Check for a command and instance argument
if [ "$#" -lt 3 ]; then
    usage
fi

COMMAND=$1
INSTANCE=$2
FULL_TABLE_NAME_OR_FILE=$3

# Check if the instance is valid
if [ -z "${PG_CONFIG[$INSTANCE]}" ]; then
    echo "Error: Invalid instance '$INSTANCE'. Supported instances: ${!PG_CONFIG[@]}"
    usage
fi
PG_CONN=${PG_CONFIG[$INSTANCE]}

# --- Backup Command ---
if [ "$COMMAND" = "backup" ]; then
    echo "Starting backup process for instance '$INSTANCE'..."

    SCHEMA_NAME=$(echo "$FULL_TABLE_NAME_OR_FILE" | cut -d'.' -f1-2)
    TABLE_NAME=$(echo "$FULL_TABLE_NAME_OR_FILE" | cut -d'.' -f3)

    # Validate table name format
    if [[ ! "$FULL_TABLE_NAME_OR_FILE" =~ ^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+$ ]]; then
        echo "Error: Invalid table name format. Use <schema>.<table_name>."
        exit 1
    fi

    TIMESTAMP_COL=
    DATE_FILTER=
    COMPRESS=$DEFAULT_COMPRESS
    DEST_DIR="$DEFAULT_DEST_DIR/$INSTANCE"

    # Parse optional arguments
    shift 3
    while (( "$#" )); do
        case "$1" in
            --no-compress)
                COMPRESS=false
                shift
                ;;
            --dest-dir)
                if [ -n "$2" ] && [ "${2:0:1}" != "-" ]; then
                    DEST_DIR=$2
                    shift 2
                else
                    echo "Error: --dest-dir requires a path."
                    exit 1
                fi
                ;;
            *)
                if [ -z "$TIMESTAMP_COL" ]; then
                    TIMESTAMP_COL=$1
                    shift
                elif [ -z "$DATE_FILTER" ]; then
                    DATE_FILTER=$1
                    shift
                else
                    echo "Error: Unknown argument: $1"
                    usage
                fi
                ;;
        esac
    done

    # Create destination directory if it doesn't exist
    mkdir -p "$DEST_DIR" || { echo "Error: Failed to create directory $DEST_DIR"; exit 1; }

    # Build the WHERE clause for date filtering
    WHERE_CLAUSE=""
    if [ -n "$TIMESTAMP_COL" ] && [ -n "$DATE_FILTER" ]; then
        if [[ "$DATE_FILTER" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
            WHERE_CLAUSE="WHERE \"$TIMESTAMP_COL\" >= '$DATE_FILTER' AND \"$TIMESTAMP_COL\" < '$DATE_FILTER'::date + INTERVAL '1 day'"
            OUTPUT_DATE_PART="_$(echo "$DATE_FILTER" | tr '-' '_')"
        elif [[ "$DATE_FILTER" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
            WHERE_CLAUSE="WHERE \"$TIMESTAMP_COL\" >= '$DATE_FILTER-01' AND \"$TIMESTAMP_COL\" < '$DATE_FILTER-01'::date + INTERVAL '1 month'"
            OUTPUT_DATE_PART="_$(echo "$DATE_FILTER" | tr '-' '_')"
        else
            echo "Error: Invalid date format. Use YYYY-MM-DD or YYYY-MM."
            exit 1
        fi
    fi

    # Construct the output file name
    FILE_NAME="${INSTANCE}_${SCHEMA_NAME}_${TABLE_NAME}"
    if [ -n "$TIMESTAMP_COL" ]; then
        FILE_NAME+="_${TIMESTAMP_COL}"
    fi
    if [ -n "$DATE_FILTER" ]; then
        FILE_NAME+="_$(echo "$DATE_FILTER" | tr '-' '_')"
    fi
    FILE_EXTENSION=".csv"
    if [ "$COMPRESS" = true ]; then
        FILE_EXTENSION=".csv.gz"
    fi
    OUTPUT_FILE="${DEST_DIR}/${FILE_NAME}${FILE_EXTENSION}"

    echo "Dumping data from '$FULL_TABLE_NAME_OR_FILE'..."
    echo "Output file: '$OUTPUT_FILE'"
    echo "SQL Query: SELECT * FROM \"$SCHEMA_NAME\".\"$TABLE_NAME\" $WHERE_CLAUSE;"

    # The actual backup command using psql and COPY
    PGPASSWORD_CMD="$PGPASSWORD" psql -c "\copy (SELECT * FROM \"$SCHEMA_NAME\".\"$TABLE_NAME\" $WHERE_CLAUSE) TO STDOUT WITH (FORMAT CSV, HEADER)" "$PG_CONN"
    
    if [ "$COMPRESS" = true ]; then
        PGPASSWORD_CMD="$PGPASSWORD" psql -c "\copy (SELECT * FROM \"$SCHEMA_NAME\".\"$TABLE_NAME\" $WHERE_CLAUSE) TO STDOUT WITH (FORMAT CSV, HEADER)" "$PG_CONN" | gzip > "$OUTPUT_FILE"
    else
        PGPASSWORD_CMD="$PGPASSWORD" psql -c "\copy (SELECT * FROM \"$SCHEMA_NAME\".\"$TABLE_NAME\" $WHERE_CLAUSE) TO '$OUTPUT_FILE' WITH (FORMAT CSV, HEADER)" "$PG_CONN"
    fi

    if [ "$?" -eq 0 ]; then
        echo "Backup completed successfully."
    else
        echo "Error: Backup failed. Check the parameters and database connection."
        exit 1
    fi

# --- Restore Command ---
elif [ "$COMMAND" = "restore" ]; then
    BACKUP_FILE=$FULL_TABLE_NAME_OR_FILE

    # Validate file existence
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "Error: Backup file '$BACKUP_FILE' not found."
        exit 1
    fi

    echo "Starting restore process to instance '$INSTANCE'..."
    echo "Restoring from file '$BACKUP_FILE'..."

    # Extract original table name from backup file name.
    # Assumes the filename format: <instance>_<schema>.<table_name>...
    TEMP_FILE_NAME=$(basename "$BACKUP_FILE")
    ORIGINAL_TABLE_INFO=$(echo "$TEMP_FILE_NAME" | sed -E "s/^${INSTANCE}_([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)_.*/\1/")
    ORIGINAL_SCHEMA=$(echo "$ORIGINAL_TABLE_INFO" | cut -d'.' -f1-2)
    ORIGINAL_TABLE=$(echo "$ORIGINAL_TABLE_INFO" | cut -d'.' -f3)

    # Determine the new table name based on the backup file name.
    # Example: dev_weavix.silver.mytable_timecol_2025_01.csv -> weavix.silver.mytable_2025_01
    DEST_TABLE_NAME=$(echo "$TEMP_FILE_NAME" | sed -E "s/^${INSTANCE}_([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)_(.*)\.csv\.?gz?/\1_\2/")
    DEST_SCHEMA=$(echo "$DEST_TABLE_NAME" | cut -d'.' -f1-2)
    DEST_TABLE=$(echo "$DEST_TABLE_NAME" | cut -d'.' -f3)

    # Check if the destination table exists
    PGPASSWORD_CMD="$PGPASSWORD" psql -t -c "SELECT 1 FROM pg_tables WHERE schemaname = '$DEST_SCHEMA' AND tablename = '$DEST_TABLE';" "$PG_CONN" | grep -q 1
    if [ "$?" -eq 0 ]; then
        echo "Warning: Destination table '$DEST_TABLE_NAME' already exists. Data will be appended. Press Enter to continue, or Ctrl+C to cancel."
        read -r
    else
        echo "Destination table '$DEST_TABLE_NAME' does not exist. Creating schema and table..."
        
        # Create schema if it doesn't exist.
        PGPASSWORD_CMD="$PGPASSWORD" psql -c "CREATE SCHEMA IF NOT EXISTS \"$DEST_SCHEMA\";" "$PG_CONN"
        if [ "$?" -ne 0 ]; then
            echo "Error: Failed to create schema '$DEST_SCHEMA'."
            exit 1
        fi

        # Use pg_dump to get the schema of the original table, then modify it to create the new table.
        SCHEMA_DUMP=$(PGPASSWORD_CMD="$PGPASSWORD" pg_dump -s -t "$ORIGINAL_SCHEMA.$ORIGINAL_TABLE" --no-owner --no-privileges --no-comments --schema-only "$PG_CONN")
        if [ "$?" -ne 0 ]; then
            echo "Error: Failed to dump schema for '$ORIGINAL_SCHEMA.$ORIGINAL_TABLE'."
            exit 1
        fi
        
        MODIFIED_SCHEMA_DUMP=$(echo "$SCHEMA_DUMP" | sed -E "s/CREATE TABLE \"$ORIGINAL_SCHEMA\"\.\"$ORIGINAL_TABLE\"/CREATE TABLE \"$DEST_SCHEMA\"\.\"$DEST_TABLE\"/")

        # Execute the modified schema dump to create the new table.
        PGPASSWORD_CMD="$PGPASSWORD" psql -c "$MODIFIED_SCHEMA_DUMP" "$PG_CONN"
        if [ "$?" -ne 0 ]; then
            echo "Error: Failed to create destination table '$DEST_TABLE_NAME'."
            exit 1
        fi
        echo "Table '$DEST_TABLE_NAME' created successfully."
    fi

    # The actual restore command
    if [[ "$BACKUP_FILE" =~ \.gz$ ]]; then
        echo "Restoring compressed data..."
        gunzip -c "$BACKUP_FILE" | PGPASSWORD_CMD="$PGPASSWORD" psql -c "\copy \"$DEST_SCHEMA\".\"$DEST_TABLE\" FROM STDIN WITH (FORMAT CSV, HEADER)" "$PG_CONN"
    else
        echo "Restoring uncompressed data..."
        PGPASSWORD_CMD="$PGPASSWORD" psql -c "\copy \"$DEST_SCHEMA\".\"$DEST_TABLE\" FROM '$BACKUP_FILE' WITH (FORMAT CSV, HEADER)" "$PG_CONN"
    fi

    if [ "$?" -eq 0 ]; then
        echo "Restore completed successfully."
    else
        echo "Error: Restore failed. Check the file and table schema."
        exit 1
    fi

else
    echo "Error: Invalid command '$COMMAND'."
    usage
fi


```


## ChatGPT
```bash
#!/usr/bin/env bash
# pgtool.sh — Backup & restore a Postgres table (full or date-filtered partial) to/from CSV (.csv or .csv.zip)
# Requirements: bash, psql (>=10), zip (for compression), unzip (for restore of .zip)
# Notes:
#   * "Partial" backups require BOTH a timestamptz column and a date argument (YYYY-MM or YYYY-MM-DD).
#   * CSVs are produced with a header row. COPY uses client-side \copy (no server file perms needed).
#   * Default is to COMPRESS (produces .csv.zip). Use --no-compress to skip compression.
#   * Restore creates destination table automatically (TEXT columns inferred from CSV header).
#   * If destination table already exists, a warning is shown and rows are APPENDED.
#
# USAGE (backup):
#   pgtool.sh backup <instance> <schema.table> [<timestamptz_col> <YYYY-MM|YYYY-MM-DD>] [--no-compress] [--dest DIR]
#
#   Examples:
#     # Full-table backup (compressed by default)
#     pgtool.sh backup dev weavix.silver.mytable
#
#     # One-month partial backup (January 2025), compressed by default
#     pgtool.sh backup dev weavix.silver.mytable timecol 2025-01
#
#     # One-day partial backup (2025-01-15), UNcompressed to .csv
#     pgtool.sh backup dev weavix.silver.mytable timecol 2025-01-15 --no-compress
#
# USAGE (restore):
#   pgtool.sh restore <instance> </path/to/file.csv|.csv.zip> [--force-append]
#
#   Example:
#     pgtool.sh restore dev /backups/dev_weavix.silver.mytable_2025-01.csv
#     pgtool.sh restore dev weavix.silver.mytable_timecol_2025-01.csv
#
# FILE NAMING (backup output):
#   If FULL:     <dest_dir>/<instance>_<schema.table>.csv[.zip]
#   If PARTIAL:  <dest_dir>/<instance>_<schema.table>_<timecol>_<YYYY-MM or YYYY-MM-DD>.csv[.zip]
#
# DEST DIR DEFAULTS (by instance) — edit these or override via --dest:
#   dev  -> /var/backups/pg/dev
#   prod -> /var/backups/pg/prod
#   test -> /var/backups/pg/test
#   local-> /var/backups/pg/local
#
# CONNECTIONS — customize these URIs or set via env (PGURI_DEV, PGURI_PROD, PGURI_TEST, PGURI_LOCAL):
#   Format examples:
#     postgres://user:pass@host:5432/dbname?sslmode=require
#     "host=/var/run/postgresql dbname=mydb user=me"
set -euo pipefail

# -------- Config: default destination folders --------
DEST_DEV="/var/backups/pg/dev"
DEST_PROD="/var/backups/pg/prod"
DEST_TEST="/var/backups/pg/test"
DEST_LOCAL="/var/backups/pg/local"

# -------- Config: connection strings (override with env) --------
PGURI_DEV="${PGURI_DEV:-postgres://localhost:5432/postgres}"
PGURI_PROD="${PGURI_PROD:-postgres://localhost:5432/postgres}"
PGURI_TEST="${PGURI_TEST:-postgres://localhost:5432/postgres}"
PGURI_LOCAL="${PGURI_LOCAL:-postgres://localhost:5432/postgres}"

die() { echo "ERROR: $*" >&2; exit 1; }
warn() { echo "WARN: $*" >&2; }
info() { echo "INFO: $*" >&2; }

usage() {
  sed -n '1,120p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"; }

PSQL() {
  local uri="$1"; shift
  # shellcheck disable=SC2086
  psql $uri "$@"
}

# Map instance -> PGURI and default dest dir
resolve_instance() {
  local instance="$1"
  case "$instance" in
    dev)   PGURI="$PGURI_DEV";   DEST_DIR_DEFAULT="$DEST_DEV" ;;
    prod)  PGURI="$PGURI_PROD";  DEST_DIR_DEFAULT="$DEST_PROD" ;;
    test)  PGURI="$PGURI_TEST";  DEST_DIR_DEFAULT="$DEST_TEST" ;;
    local) PGURI="$PGURI_LOCAL"; DEST_DIR_DEFAULT="$DEST_LOCAL" ;;
    *) die "Unknown instance '$instance' (expected: dev|prod|test|local)";;
  esac
}

# Validate schema.table and quote identifiers
split_qualname() {
  local qual="$1"
  [[ "$qual" =~ ^[A-Za-z0-9_]+\.{1}[A-Za-z0-9_]+$ ]] || die "Invalid table name '$qual' (expected schema.table)"
  SCHEMA="${qual%%.*}"
  TABLE="${qual##*.}"
  QSCHEMA="\"$SCHEMA\""
  QTABLE="\"$TABLE\""
}

# Build WHERE clause/time window SQL for partial backup
build_time_window_sql() {
  local col="$1" date_arg="$2"
  # col must be a valid SQL identifier (we soft-check)
  [[ "$col" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die "Invalid column name '$col'"
  # YYYY-MM or YYYY-MM-DD
  if [[ "$date_arg" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
    # Month window: [start, next_month)
    TIME_WINDOW_SQL="($col >= date_trunc('month', to_date('$date_arg-01','YYYY-MM-DD')) AND $col < (date_trunc('month', to_date('$date_arg-01','YYYY-MM-DD')) + interval '1 month'))"
  elif [[ "$date_arg" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    # Day window: [day, next_day)
    TIME_WINDOW_SQL="($col >= to_timestamp('$date_arg','YYYY-MM-DD') AND $col < (to_timestamp('$date_arg','YYYY-MM-DD') + interval '1 day'))"
  else
    die "Invalid date '$date_arg' (expected YYYY-MM or YYYY-MM-DD)"
  fi
}

# Verify column exists and is timestamptz
validate_timecol() {
  local schema="$1" table="$2" col="$3"
  local q="
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = $$
      $schema$$ AND table_name = $$${table}$$ AND column_name = $$${col}$$
      AND udt_name IN ('timestamptz','timestamp_tz');"
  if ! PSQL "$PGURI" -Atq -c "$q" | grep -q '^1$'; then
    # Allow plain 'timestamp with time zone' too:
    q="
      SELECT 1
      FROM information_schema.columns
      WHERE table_schema = $$${schema}$$
        AND table_name = $$${table}$$
        AND column_name = $$${col}$$
        AND data_type = 'timestamp with time zone';"
    PSQL "$PGURI" -Atq -c "$q" | grep -q '^1$' || die "Column '$schema.$table.$col' not found or not timestamptz"
  fi
}

# Backup logic
do_backup() {
  local instance="$1"; shift
  local qualname="$1"; shift
  local timecol="" date_arg="" dest_dir="" compress="1"

  # Parse optional positionals + flags
  # Positionals (if present): <timecol> <date>
  if [[ $# -ge 1 && "$1" != --* ]]; then timecol="$1"; shift; fi
  if [[ $# -ge 1 && "$1" != --* ]]; then date_arg="$1"; shift; fi
  # Flags
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-compress) compress="0"; shift ;;
      --dest) dest_dir="${2:-}"; [[ -n "$dest_dir" ]] || die "--dest requires a directory"; shift 2 ;;
      -h|--help) usage ;;
      *) die "Unknown option for backup: $1" ;;
    esac
  done

  resolve_instance "$instance"
  split_qualname "$qualname"
  local out_dir="${dest_dir:-$DEST_DIR_DEFAULT}"
  mkdir -p "$out_dir"

  local filename=""
  local where_sql=""
  if [[ -n "$timecol" || -n "$date_arg" ]]; then
    [[ -n "$timecol" && -n "$date_arg" ]] || die "Partial backup requires BOTH <timestamptz_col> and <date>"
    validate_timecol "$SCHEMA" "$TABLE" "$timecol"
    build_time_window_sql "$timecol" "$date_arg"
    where_sql="WHERE $TIME_WINDOW_SQL"
    filename="${instance}_${SCHEMA}.${TABLE}_${timecol}_${date_arg}.csv"
  else
    filename="${instance}_${SCHEMA}.${TABLE}.csv"
  fi

  local out_csv="$out_dir/$filename"
  local tmp_csv="$out_csv.__tmp__"

  info "Starting backup: $SCHEMA.$TABLE"
  if [[ -n "$where_sql" ]]; then
    local sql="\\copy (SELECT * FROM $QSCHEMA.$QTABLE $where_sql ORDER BY 1) TO STDOUT WITH (FORMAT csv, HEADER, FORCE_QUOTE *)"
    PSQL "$PGURI" -qAt -c "$sql" > "$tmp_csv"
  else
    local sql="\\copy $QSCHEMA.$QTABLE TO STDOUT WITH (FORMAT csv, HEADER, FORCE_QUOTE *)"
    PSQL "$PGURI" -qAt -c "$sql" > "$tmp_csv"
  fi

  # Move into place & (optionally) compress
  mv "$tmp_csv" "$out_csv"
  if [[ "$compress" == "1" ]]; then
    need_cmd zip
    (cd "$out_dir" && zip -q -m "${filename}.zip" "$filename")  # -m deletes original after zipping
    out_csv="${out_csv}.zip"
  fi

  info "Backup complete: $out_csv"
}

# Create schema if not exists
ensure_schema() {
  local schema="$1"
  local sql="DO $$
  BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = '$schema') THEN
      EXECUTE format('CREATE SCHEMA %I', '$schema');
    END IF;
  END
  $$;"
  PSQL "$PGURI" -q -c "$sql"
}

# Check if table exists
table_exists() {
  local schema="$1" table="$2"
  local q="SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname=$$${schema}$$ AND c.relname=$$${table}$$ AND c.relkind='r';"
  PSQL "$PGURI" -Atq -c "$q" | grep -q '^1$'
}

# Create table with TEXT columns inferred from CSV header
create_table_from_csv_header() {
  local schema="$1" table="$2" csv_path="$3"
  local header
  IFS= read -r header < "$csv_path" || die "Failed to read header from $csv_path"
  [[ -n "$header" ]] || die "Empty CSV header in $csv_path"

  # Split header by comma respecting simple quotes (assume clean CSV headers)
  # Convert to text columns and quote identifiers.
  local cols=()
  IFS=',' read -ra cols <<< "$header"
  local coldefs=()
  for raw in "${cols[@]}"; do
    # Trim surrounding whitespace and quotes
    local col="${raw%$'\r'}"
    col="${col//\"/}"          # strip double quotes if any
    col="${col#"${col%%[![:space:]]*}"}"
    col="${col%"${col##*[![:space:]]}"}"
    [[ "$col" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || col="_$(echo "$col" | tr -cs 'A-Za-z0-9_' '_' | sed 's/^_*$//;s/^$/col/' )"
    coldefs+=("\"$col\" text")
  done
  local ddl="CREATE TABLE \"$schema\".\"$table\" ( $(IFS=','; echo "${coldefs[*]}") );"
  ensure_schema "$schema"
  PSQL "$PGURI" -q -c "$ddl"
}

# Parse destination table name from filename base (without .csv or .csv.zip)
# Accepts both:
#   <instance>_<schema.table>[_<timecol>][_YYYY-MM or YYYY-MM-DD]
#   OR
#   <schema.table>[_<timecol>][_YYYY-MM or YYYY-MM-DD]
# We CREATE/APPEND INTO a table named:
#   <schema>.<table>  (plus suffixes _<timecol>_<date> if they are present in filename)
#
# Returns: DEST_SCHEMA, DEST_TABLE
derive_dest_table_from_base() {
  local base="$1" instance="$2"

  # If base starts with "<instance>_", strip it
  if [[ "$base" == "${instance}_"* ]]; then
    base="${base#${instance}_}"
  fi

  # Split base at first '_' to isolate schema.table
  local schema_table="${base%%_*}"
  local rest="${base#${schema_table}}"
  rest="${rest#_}" # drop leading underscore if present (may become empty)

  [[ "$schema_table" =~ ^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$ ]] || die "Cannot parse schema.table from filename base '$base'"

  local schema="${schema_table%%.*}"
  local table="${schema_table##*.}"

  # If there is "rest", append it to table name (so restored table name carries any _timecol_YYYY-MM etc.)
  if [[ -n "$rest" && "$rest" != "$base" ]]; then
    table="${table}_$rest"
  fi

  DEST_SCHEMA="$schema"
  DEST_TABLE="$table"
}

# Restore logic
do_restore() {
  local instance="$1"; shift
  local input="$1"; shift
  local force_append="0"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --force-append) force_append="1"; shift ;;
      -h|--help) usage ;;
      *) die "Unknown option for restore: $1" ;;
    esac
  done

  resolve_instance "$instance"

  [[ -f "$input" ]] || die "Input file not found: $input"

  local work_csv=""
  local tmpdir=""
  if [[ "$input" =~ \.csv\.zip$ ]]; then
    need_cmd unzip
    tmpdir="$(mktemp -d)"
    unzip -q "$input" -d "$tmpdir"
    work_csv="$(find "$tmpdir" -maxdepth 1 -type f -name '*.csv' | head -n1)"
    [[ -n "$work_csv" ]] || die "No .csv inside zip"
  elif [[ "$input" =~ \.csv$ ]]; then
    work_csv="$input"
  else
    die "Input must be .csv or .csv.zip"
  fi

  local base="$(basename "$work_csv")"
  base="${base%.csv}"            # strip .csv
  derive_dest_table_from_base "$base" "$instance"

  info "Restoring into: $DEST_SCHEMA.$DEST_TABLE"
  if table_exists "$DEST_SCHEMA" "$DEST_TABLE"; then
    warn "Destination table $DEST_SCHEMA.$DEST_TABLE already exists; rows will be appended."
    if [[ "$force_append" != "1" ]]; then
      warn "Tip: pass --force-append to suppress this warning."
    fi
  else
    info "Creating $DEST_SCHEMA.$DEST_TABLE from CSV header (all columns TEXT)"
    create_table_from_csv_header "$DEST_SCHEMA" "$DEST_TABLE" "$work_csv"
  fi

  # Perform COPY
  local copy_sql="\\copy \"$DEST_SCHEMA\".\"$DEST_TABLE\" FROM STDIN WITH (FORMAT csv, HEADER)"
  PSQL "$PGURI" -q -c "$copy_sql" < "$work_csv"
  info "Restore complete into: $DEST_SCHEMA.$DEST_TABLE"

  [[ -n "${tmpdir:-}" ]] && rm -rf "$tmpdir"
}

# -------- Main --------
[[ $# -lt 1 ]] && usage
cmd="$1"; shift || true

case "$cmd" in
  backup)
    [[ $# -ge 2 ]] || usage
    need_cmd psql
    do_backup "$@"
    ;;
  restore)
    [[ $# -ge 2 ]] || usage
    need_cmd psql
    do_restore "$@"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    die "Unknown command '$cmd' (use backup|restore)"
    ;;
esac
```
### gzip instead zip for screen above:
```bash
#!/usr/bin/env bash
# pgtool.sh — Backup & restore a Postgres table (full or date-filtered partial) to/from CSV (.csv or .csv.gz)
# Requirements: bash, psql (>=10), gzip (for compression)
#
# USAGE (backup):
#   pgtool.sh backup <instance> <schema.table> [<timestamptz_col> <YYYY-MM|YYYY-MM-DD>] [--no-compress] [--dest DIR]
#
# USAGE (restore):
#   pgtool.sh restore <instance> </path/to/file.csv|.csv.gz> [--force-append]
#
# FILE NAMING:
#   FULL:     <dest_dir>/<instance>_<schema.table>.csv[.gz]
#   PARTIAL:  <dest_dir>/<instance>_<schema.table>_<timecol>_<YYYY-MM or YYYY-MM-DD>.csv[.gz]
#
# DEST DIR DEFAULTS (edit as needed):
DEST_DEV="/var/backups/pg/dev"
DEST_PROD="/var/backups/pg/prod"
DEST_TEST="/var/backups/pg/test"
DEST_LOCAL="/var/backups/pg/local"

# CONNECTIONS — override with env vars (PGURI_DEV, etc.)
PGURI_DEV="${PGURI_DEV:-postgres://localhost:5432/postgres}"
PGURI_PROD="${PGURI_PROD:-postgres://localhost:5432/postgres}"
PGURI_TEST="${PGURI_TEST:-postgres://localhost:5432/postgres}"
PGURI_LOCAL="${PGURI_LOCAL:-postgres://localhost:5432/postgres}"

set -euo pipefail

die() { echo "ERROR: $*" >&2; exit 1; }
warn() { echo "WARN: $*" >&2; }
info() { echo "INFO: $*" >&2; }

PSQL() { local uri="$1"; shift; psql $uri "$@"; }

resolve_instance() {
  case "$1" in
    dev)   PGURI="$PGURI_DEV";   DEST_DIR_DEFAULT="$DEST_DEV" ;;
    prod)  PGURI="$PGURI_PROD";  DEST_DIR_DEFAULT="$DEST_PROD" ;;
    test)  PGURI="$PGURI_TEST";  DEST_DIR_DEFAULT="$DEST_TEST" ;;
    local) PGURI="$PGURI_LOCAL"; DEST_DIR_DEFAULT="$DEST_LOCAL" ;;
    *) die "Unknown instance '$1'";;
  esac
}

split_qualname() {
  [[ "$1" =~ ^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$ ]] || die "Bad table name '$1'"
  SCHEMA="${1%%.*}"; TABLE="${1##*.}"
  QSCHEMA="\"$SCHEMA\""; QTABLE="\"$TABLE\""
}

build_time_window_sql() {
  local col="$1" date_arg="$2"
  if [[ "$date_arg" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
    TIME_WINDOW_SQL="($col >= date_trunc('month', to_date('$date_arg-01','YYYY-MM-DD')) 
      AND $col < (date_trunc('month', to_date('$date_arg-01','YYYY-MM-DD')) + interval '1 month'))"
  elif [[ "$date_arg" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    TIME_WINDOW_SQL="($col >= to_timestamp('$date_arg','YYYY-MM-DD') 
      AND $col < (to_timestamp('$date_arg','YYYY-MM-DD') + interval '1 day'))"
  else
    die "Invalid date '$date_arg'"
  fi
}

# ---------------- BACKUP ----------------
do_backup() {
  local instance="$1" qualname="$2"; shift 2
  local timecol="" date_arg="" dest_dir="" compress=1

  if [[ $# -ge 1 && "$1" != --* ]]; then timecol="$1"; shift; fi
  if [[ $# -ge 1 && "$1" != --* ]]; then date_arg="$1"; shift; fi
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-compress) compress=0; shift ;;
      --dest) dest_dir="$2"; shift 2 ;;
      *) die "Unknown option: $1" ;;
    esac
  done

  resolve_instance "$instance"; split_qualname "$qualname"
  mkdir -p "${dest_dir:-$DEST_DIR_DEFAULT}"

  local filename out_csv where_sql=""
  if [[ -n "$timecol" && -n "$date_arg" ]]; then
    build_time_window_sql "$timecol" "$date_arg"
    where_sql="WHERE $TIME_WINDOW_SQL"
    filename="${instance}_${SCHEMA}.${TABLE}_${timecol}_${date_arg}.csv"
  else
    filename="${instance}_${SCHEMA}.${TABLE}.csv"
  fi
  out_csv="${dest_dir:-$DEST_DIR_DEFAULT}/$filename"

  local sql
  if [[ -n "$where_sql" ]]; then
    sql="\\copy (SELECT * FROM $QSCHEMA.$QTABLE $where_sql ORDER BY 1) TO STDOUT WITH CSV HEADER"
  else
    sql="\\copy $QSCHEMA.$QTABLE TO STDOUT WITH CSV HEADER"
  fi

  info "Backing up $SCHEMA.$TABLE -> $out_csv"
  if [[ $compress -eq 1 ]]; then
    PSQL "$PGURI" -qAt -c "$sql" | gzip > "${out_csv}.gz"
    info "Backup complete: ${out_csv}.gz"
  else
    PSQL "$PGURI" -qAt -c "$sql" > "$out_csv"
    info "Backup complete: $out_csv"
  fi
}

# ---------------- RESTORE ----------------
do_restore() {
  local instance="$1" input="$2"; shift 2
  resolve_instance "$instance"

  [[ -f "$input" ]] || die "File not found: $input"
  local work_csv="$input"
  if [[ "$input" =~ \.gz$ ]]; then
    work_csv="$(mktemp).csv"
    gunzip -c "$input" > "$work_csv"
  fi

  local base="$(basename "$work_csv" .csv)"
  local schema_table="${base%%_*}"  # naive parse, adjust as needed
  local schema="${schema_table%%.*}"
  local table="${schema_table##*.}"

  info "Restoring into $schema.$table"
  local copy_sql="\\copy \"$schema\".\"$table\" FROM STDIN WITH CSV HEADER"
  PSQL "$PGURI" -q -c "$copy_sql" < "$work_csv"
  info "Restore complete."

  [[ "$input" =~ \.gz$ ]] && rm -f "$work_csv"
}

# ---------------- MAIN ----------------
cmd="$1"; shift || true
case "$cmd" in
  backup) do_backup "$@" ;;
  restore) do_restore "$@" ;;
  *) die "Usage: pgtool.sh (backup|restore) ..." ;;
esac

```
