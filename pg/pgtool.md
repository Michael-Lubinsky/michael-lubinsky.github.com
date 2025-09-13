Write the bash script pgtool.sh for backup and recovery postgres table. 
It should be compatible with bash   version 3.2.57

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

# pgtool.sh - PostgreSQL table backup and recovery tool (Bash 3.2.5 compatible)
# Usage:
#   Backup: ./pgtool.sh backup <instance> <table> [<time_column>] [<date>] [--no-compress] [--dest <folder>]
#   Restore: ./pgtool.sh restore <instance> <file>

set -euo pipefail

# --- Config ---
# Use environment variables or case statements for instance config
# Example: export PG_DEV="user=dev_user dbname=dev_db host=dev-host port=5432"
# Or set here:
PG_DEV="user=dev_user dbname=dev_db host=dev-host port=5432"
PG_PROD="user=prod_user dbname=prod_db host=prod-host port=5432"
PG_TEST="user=test_user dbname=test_db host=test-host port=5432"
PG_LOCAL="user=postgres dbname=postgres host=localhost port=5432"
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

function get_conn() {
    local instance="$1"
    case "$instance" in
        dev)    echo "$PG_DEV" ;;
        prod)   echo "$PG_PROD" ;;
        test)   echo "$PG_TEST" ;;
        local)  echo "$PG_LOCAL" ;;
        *)      echo "" ;;
    esac
}

function backup() {
    local instance="$1"
    local table="$2"
    local time_column="${3:-}"
    local date_filter="${4:-}"
    local compress="${5:-true}"
    local dest_folder="${6:-${DEFAULT_DEST_FOLDER}}"

    local conn=$(get_conn "$instance")
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
    local conn=$(get_conn "$instance")
    if [[ -z "$conn" ]]; then
        echo "Error: Unknown instance '$instance'"
        usage
    fi

    local filename=$(basename "$file")
    local table_name=$(echo "$filename" | sed 's/\.csv\(\.gz\)\?$//')
    table_name=$(echo "$table_name" | sed "s/^${instance}_//")

    local schema=$(echo "$table_name" | cut -d_ -f1,2)
    local table=$(echo "$table_name" | cut -d_ -f3-)

    # If table_name contains date, extract the base table name
    if [[ "$table" =~ ^([^_]+_[^_]+)_[^_]+_[0-9]{4}-[0-9]{2}(-[0-9]{2})?$ ]]; then
        table=$(echo "$table" | sed 's/_[^_]*_[0-9]\{4\}-[0-9]\{2\}-*[0-9]*$//')
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

```
The script I provided below some Bash 4+ features (declare -A for associative arrays), which are not available in macOS's default Bash 3.2.5.
However, it's easy to adapt the script for Bash 3.2.5 compatibility.
```

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
```
#!/bin/bash

# ==============================================================================
# Script: pgtool.sh
# Description: A tool for backing up and restoring PostgreSQL table data.
# This version is compatible with Bash 3.2.5.
# ==============================================================================

# --- Helper Functions ---

# Function to get the PostgreSQL connection string for a given instance
get_pg_conn() {
    local instance=$1
    case "$instance" in
        dev)
            echo "PGHOST=$PGHOST_dev PGDATABASE=$PGDATABASE_dev PGUSER=$PGUSER_dev PGPASSWORD=$PGPASSWORD_dev"
            ;;
        prod)
            echo "PGHOST=$PGHOST_prod PGDATABASE=$PGDATABASE_prod PGUSER=$PGUSER_prod PGPASSWORD=$PGPASSWORD_prod"
            ;;
        test)
            echo "PGHOST=$PGHOST_test PGDATABASE=$PGDATABASE_test PGUSER=$PGUSER_test PGPASSWORD=$PGPASSWORD_test"
            ;;
        local)
            echo "PGHOST=$PGHOST_local PGDATABASE=$PGDATABASE_local PGUSER=$PGUSER_local PGPASSWORD=$PGPASSWORD_local"
            ;;
        *)
            echo ""
            ;;
    esac
}

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

# Get the connection string using the helper function
PG_CONN=$(get_pg_conn "$INSTANCE")

# Check if the instance is valid
if [ -z "$PG_CONN" ]; then
    echo "Error: Invalid instance '$INSTANCE'. Supported instances: dev, prod, test, local"
    usage
fi

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

    TIMESTAMP_COL=""
    DATE_FILTER=""
    DEFAULT_COMPRESS=true
    COMPRESS=$DEFAULT_COMPRESS
    DEFAULT_DEST_DIR="/var/backups"
    DEST_DIR="$DEFAULT_DEST_DIR/$INSTANCE"

    # Parse optional arguments
    shift 3
    while [ "$#" -gt 0 ]; do
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
            WHERE_CLAUSE="WHERE \"$TIMESTAMP_COL\" >= '$DATE_FILTER' AND \"$TIMESTAMP_COL\" < ('$DATE_FILTER'::date + INTERVAL '1 day')::text"
            OUTPUT_DATE_PART="_$(echo "$DATE_FILTER" | tr '-' '_')"
        elif [[ "$DATE_FILTER" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
            WHERE_CLAUSE="WHERE \"$TIMESTAMP_COL\" >= '$DATE_FILTER-01' AND \"$TIMESTAMP_COL\" < ('$DATE_FILTER-01'::date + INTERVAL '1 month')::text"
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
    if [ "$COMPRESS" = true ]; then
        psql -c "\copy (SELECT * FROM \"$SCHEMA_NAME\".\"$TABLE_NAME\" $WHERE_CLAUSE) TO STDOUT WITH (FORMAT CSV, HEADER)" $PG_CONN | gzip > "$OUTPUT_FILE"
    else
        psql -c "\copy (SELECT * FROM \"$SCHEMA_NAME\".\"$TABLE_NAME\" $WHERE_CLAUSE) TO '$OUTPUT_FILE' WITH (FORMAT CSV, HEADER)" $PG_CONN
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
    TEMP_FILE_NAME=$(basename "$BACKUP_FILE")
    ORIGINAL_TABLE_INFO=$(echo "$TEMP_FILE_NAME" | sed -E "s/^${INSTANCE}_([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)_.*/\1/")
    ORIGINAL_SCHEMA=$(echo "$ORIGINAL_TABLE_INFO" | cut -d'.' -f1-2)
    ORIGINAL_TABLE=$(echo "$ORIGINAL_TABLE_INFO" | cut -d'.' -f3)

    # Determine the new table name based on the backup file name.
    DEST_TABLE_NAME=$(echo "$TEMP_FILE_NAME" | sed -E "s/^${INSTANCE}_([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)_(.*)\.csv\.?gz?/\1_\2/")
    DEST_SCHEMA=$(echo "$DEST_TABLE_NAME" | cut -d'.' -f1-2)
    DEST_TABLE=$(echo "$DEST_TABLE_NAME" | cut -d'.' -f3)

    # Check if the destination table exists
    psql -t -c "SELECT 1 FROM pg_tables WHERE schemaname = '$DEST_SCHEMA' AND tablename = '$DEST_TABLE';" $PG_CONN | grep -q 1
    if [ "$?" -eq 0 ]; then
        echo "Warning: Destination table '$DEST_TABLE_NAME' already exists. Data will be appended. Press Enter to continue, or Ctrl+C to cancel."
        read -r
    else
        echo "Destination table '$DEST_TABLE_NAME' does not exist. Creating schema and table..."
        
        # Create schema if it doesn't exist.
        psql -c "CREATE SCHEMA IF NOT EXISTS \"$DEST_SCHEMA\";" $PG_CONN
        if [ "$?" -ne 0 ]; then
            echo "Error: Failed to create schema '$DEST_SCHEMA'."
            exit 1
        fi

        # Use pg_dump to get the schema of the original table, then modify it to create the new table.
        SCHEMA_DUMP=$(pg_dump -s -t "$ORIGINAL_SCHEMA.$ORIGINAL_TABLE" --no-owner --no-privileges --no-comments --schema-only $PG_CONN)
        if [ "$?" -ne 0 ]; then
            echo "Error: Failed to dump schema for '$ORIGINAL_SCHEMA.$ORIGINAL_TABLE'."
            exit 1
        fi
        
        MODIFIED_SCHEMA_DUMP=$(echo "$SCHEMA_DUMP" | sed -E "s/CREATE TABLE \"$ORIGINAL_SCHEMA\"\.\"$ORIGINAL_TABLE\"/CREATE TABLE \"$DEST_SCHEMA\"\.\"$DEST_TABLE\"/")

        # Execute the modified schema dump to create the new table.
        psql -c "$MODIFIED_SCHEMA_DUMP" $PG_CONN
        if [ "$?" -ne 0 ]; then
            echo "Error: Failed to create destination table '$DEST_TABLE_NAME'."
            exit 1
        fi
        echo "Table '$DEST_TABLE_NAME' created successfully."
    fi

    # The actual restore command
    if [[ "$BACKUP_FILE" =~ \.gz$ ]]; then
        echo "Restoring compressed data..."
        gunzip -c "$BACKUP_FILE" | psql -c "\copy \"$DEST_SCHEMA\".\"$DEST_TABLE\" FROM STDIN WITH (FORMAT CSV, HEADER)" $PG_CONN
    else
        echo "Restoring uncompressed data..."
        psql -c "\copy \"$DEST_SCHEMA\".\"$DEST_TABLE\" FROM '$BACKUP_FILE' WITH (FORMAT CSV, HEADER)" $PG_CONN
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
### gzip  :
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
