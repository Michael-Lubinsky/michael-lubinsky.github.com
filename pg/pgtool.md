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
```bash
#!/usr/bin/env bash
# pgtool.sh — Backup & restore a Postgres table (full or date-filtered partial) to/from CSV (.csv or .csv.gz)
# Compatible with Bash 3.2 (macOS default). No regex used.
#
# Features
#   • BACKUP: full table, or partial by date window on a timestamptz column.
#   • RESTORE: auto-creates destination table from CSV header (TEXT columns). Warns if table exists (appends).
#   • Compression: gzip by default (.csv.gz). Use --no-compress for plain .csv.
#   • File naming:
#       FULL:     <dest>/<instance>_<schema.table>.csv[.gz]
#       PARTIAL:  <dest>/<instance>_<schema.table>_<timecol>_<YYYY-MM | YYYY-MM-DD>.csv[.gz]
#
# Usage
#   Backup:
#     pgtool.sh backup <instance> <schema.table> [<timestamptz_col> <YYYY-MM|YYYY-MM-DD>] [--no-compress] [--dest DIR]
#     pgtool.sh backup dev weavix.silver.mytable
#     pgtool.sh backup dev weavix.silver.mytable timecol 2025-01
#     pgtool.sh backup dev weavix.silver.mytable timecol 2025-01-15 --no-compress --dest /tmp
#
#   Restore:
#     pgtool.sh restore <instance> </path/to/file.csv|.csv.gz> [--force-append]
#     pgtool.sh restore dev /backups/dev_weavix.silver.mytable_2025-01.csv.gz
#
# Defaults (edit if desired) ----------------------------------------------
DEST_DEV="/var/backups/pg/dev"
DEST_PROD="/var/backups/pg/prod"
DEST_TEST="/var/backups/pg/test"
DEST_LOCAL="/var/backups/pg/local"

# Connection URIs (override via env: PGURI_DEV, PGURI_PROD, PGURI_TEST, PGURI_LOCAL)
PGURI_DEV="${PGURI_DEV:-postgres://localhost:5432/postgres}"
PGURI_PROD="${PGURI_PROD:-postgres://localhost:5432/postgres}"
PGURI_TEST="${PGURI_TEST:-postgres://localhost:5432/postgres}"
PGURI_LOCAL="${PGURI_LOCAL:-postgres://localhost:5432/postgres}"
# -------------------------------------------------------------------------

set -euo pipefail

die()  { echo "ERROR: $*" >&2; exit 1; }
warn() { echo "WARN:  $*" >&2; }
info() { echo "INFO:  $*" >&2; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"; }

PSQL() { local uri="$1"; shift; psql $uri "$@"; }

usage() {
  sed -n '1,120p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

resolve_instance() {
  case "${1:-}" in
    dev)   PGURI="$PGURI_DEV";   DEST_DIR_DEFAULT="$DEST_DEV" ;;
    prod)  PGURI="$PGURI_PROD";  DEST_DIR_DEFAULT="$DEST_PROD" ;;
    test)  PGURI="$PGURI_TEST";  DEST_DIR_DEFAULT="$DEST_TEST" ;;
    local) PGURI="$PGURI_LOCAL"; DEST_DIR_DEFAULT="$DEST_LOCAL" ;;
    *) die "Unknown instance '${1:-}' (expected: dev|prod|test|local)";;
  esac
}

# Identifier checks without regex
is_valid_ident() {
  # letters, digits, underscore; must not be empty
  local s="${1:-}"
  [ -n "$s" ] || return 1
  case "$s" in
    *[!A-Za-z0-9_]* ) return 1 ;;
    * ) return 0 ;;
  esac
}

split_qualname() {
  local qual="${1:-}"
  case "$qual" in
    *.*) : ;;
    *) die "Invalid table name '$qual' (expected schema.table)";;
  esac
  SCHEMA="${qual%%.*}"
  TABLE="${qual##*.}"
  is_valid_ident "$SCHEMA" || die "Invalid schema identifier '$SCHEMA'"
  is_valid_ident "$TABLE"  || die "Invalid table identifier '$TABLE'"
  QSCHEMA="\"$SCHEMA\""; QTABLE="\"$TABLE\""
}

# Date format helpers (no regex)
is_month_fmt() {
  # YYYY-MM
  local d="${1:-}"
  case "$d" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]) return 0 ;;
    *) return 1 ;;
  esac
}
is_day_fmt() {
  # YYYY-MM-DD
  local d="${1:-}"
  case "$d" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) return 0 ;;
    *) return 1 ;;
  esac
}

build_time_window_sql() {
  # Builds TIME_WINDOW_SQL using to_date/to_timestamp and date_trunc
  local col="$1" date_arg="$2"
  is_valid_ident "$col" || die "Invalid column name '$col'"
  if is_month_fmt "$date_arg"; then
    # [first day of month, first day of next month)
    TIME_WINDOW_SQL="($col >= date_trunc('month', to_date('$date_arg-01','YYYY-MM-DD')) AND $col < (date_trunc('month', to_date('$date_arg-01','YYYY-MM-DD')) + interval '1 month'))"
  elif is_day_fmt "$date_arg"; then
    # [day, next day)
    TIME_WINDOW_SQL="($col >= to_timestamp('$date_arg','YYYY-MM-DD') AND $col < (to_timestamp('$date_arg','YYYY-MM-DD') + interval '1 day'))"
  else
    die "Invalid date '$date_arg' (use YYYY-MM or YYYY-MM-DD)"
  fi
}

validate_timecol() {
  local schema="$1" table="$2" col="$3"
  # Check timestamptz by data_type
  local q="
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema=$$${schema}$$
      AND table_name=$$${table}$$
      AND column_name=$$${col}$$
      AND data_type='timestamp with time zone';
  "
  PSQL "$PGURI" -Atq -c "$q" | grep -q '^1$' || die "Column '$schema.$table.$col' not found or not timestamptz"
}

# ---------- BACKUP ----------
do_backup() {
  local instance="$1" qualname="$2"; shift 2
  local timecol="" date_arg="" dest_dir="" compress=1

  # Optionals: <timecol> <date>
  if [ $# -ge 1 ] && [ "${1#--}" = "$1" ]; then timecol="$1"; shift; fi
  if [ $# -ge 1 ] && [ "${1#--}" = "$1" ]; then date_arg="$1"; shift; fi

  # Flags
  while [ $# -gt 0 ]; do
    case "$1" in
      --no-compress) compress=0; shift ;;
      --dest) dest_dir="${2:-}"; [ -n "$dest_dir" ] || die "--dest requires a directory"; shift 2 ;;
      -h|--help) usage ;;
      *) die "Unknown option for backup: $1" ;;
    esac
  done

  resolve_instance "$instance"
  split_qualname "$qualname"

  local out_dir="${dest_dir:-$DEST_DIR_DEFAULT}"
  mkdir -p "$out_dir"

  local filename where_sql=""
  if [ -n "$timecol" ] || [ -n "$date_arg" ]; then
    [ -n "$timecol" ] && [ -n "$date_arg" ] || die "Partial backup requires BOTH <timestamptz_col> and <date>"
    validate_timecol "$SCHEMA" "$TABLE" "$timecol"
    build_time_window_sql "$timecol" "$date_arg"
    where_sql="WHERE $TIME_WINDOW_SQL"
    filename="${instance}_${SCHEMA}.${TABLE}_${timecol}_${date_arg}.csv"
  else
    filename="${instance}_${SCHEMA}.${TABLE}.csv"
  fi

  local out_csv="$out_dir/$filename"
  local sql
  if [ -n "$where_sql" ]; then
    sql="\\copy (SELECT * FROM $QSCHEMA.$QTABLE $where_sql ORDER BY 1) TO STDOUT WITH (FORMAT csv, HEADER, FORCE_QUOTE *)"
  else
    sql="\\copy $QSCHEMA.$QTABLE TO STDOUT WITH (FORMAT csv, HEADER, FORCE_QUOTE *)"
  fi

  info "Backing up $SCHEMA.$TABLE -> $out_csv"
  if [ "$compress" -eq 1 ]; then
    need_cmd gzip
    PSQL "$PGURI" -qAt -c "$sql" | gzip > "${out_csv}.gz"
    info "Backup complete: ${out_csv}.gz"
  else
    PSQL "$PGURI" -qAt -c "$sql" > "$out_csv"
    info "Backup complete: $out_csv"
  fi
}

# ---------- RESTORE HELPERS ----------
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

table_exists() {
  local schema="$1" table="$2"
  local q="SELECT 1
           FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname=$$${schema}$$ AND c.relname=$$${table}$$ AND c.relkind='r';"
  PSQL "$PGURI" -Atq -c "$q" | grep -q '^1$'
}

sanitize_colname() {
  # Keep letters/digits/_ ; replace others with _ ; ensure starts with letter/_.
  local raw="$1"
  # strip CR and quotes and trim spaces
  raw="${raw%$'\r'}"
  raw="${raw//\"/}"
  # squeeze spaces around
  # shellcheck disable=SC2001
  raw="$(echo "$raw" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  local cleaned
  cleaned="$(echo "$raw" | tr -cs 'A-Za-z0-9_' '_' )"
  # ensure not empty
  [ -n "$cleaned" ] || cleaned="col"
  # ensure first char not a digit
  case "$cleaned" in
    [0-9]* ) cleaned="_$cleaned" ;;
  esac
  echo "$cleaned"
}

create_table_from_csv_header() {
  local schema="$1" table="$2" csv_path="$3"
  local header
  IFS= read -r header < "$csv_path" || die "Failed to read header from $csv_path"
  [ -n "$header" ] || die "Empty CSV header in $csv_path"

  # Split by commas into array (Bash 3.2 supports arrays)
  local IFS=',' cols=()
  # shellcheck disable=SC2206
  cols=($header)

  local coldefs=""
  local i
  for i in "${!cols[@]}"; do
    local c
    c="$(sanitize_colname "${cols[$i]}")"
    if [ "$i" -gt 0 ]; then coldefs="$coldefs, "; fi
    coldefs="$coldefs\"$c\" text"
  done

  ensure_schema "$schema"
  local ddl="CREATE TABLE \"$schema\".\"$table\" ( $coldefs );"
  PSQL "$PGURI" -q -c "$ddl"
}

# Derive destination table from filename base (no regex)
# Accepts names like:
#   <instance>_<schema.table>
#   <instance>_<schema.table>_<timecol>_<YYYY-MM or YYYY-MM-DD>
#   or without the instance prefix.
derive_dest_table_from_base() {
  local base="$1" instance="$2"

  # If starts with "<instance>_", strip it
  case "$base" in
    "${instance}_"*) base="${base#${instance}_}" ;;
  esac

  # schema.table is up to first underscore, or whole string if none
  local schema_table rest
  case "$base" in
    *_*)
      schema_table="${base%%_*}"
      rest="${base#${schema_table}_}"
      ;;
    *)
      schema_table="$base"
      rest=""
      ;;
  esac

  case "$schema_table" in
    *.*) : ;;
    *) die "Cannot parse schema.table from '$base'";;
  esac

  DEST_SCHEMA="${schema_table%%.*}"
  DEST_TABLE="${schema_table##*.}"

  # If there is "rest", append to table to keep timecol/date suffix in table name
  if [ -n "$rest" ]; then
    DEST_TABLE="${DEST_TABLE}_$rest"
  fi

  is_valid_ident "$DEST_SCHEMA" || die "Invalid schema parsed from filename: '$DEST_SCHEMA'"
  # Allow underscores in appended parts; sanitize double underscores later if needed
}

# ---------- RESTORE ----------
do_restore() {
  local instance="$1" input="$2"; shift 2
  resolve_instance "$instance"

  [ -f "$input" ] || die "File not found: $input"

  local work_csv="$input"
  local tmp_csv=""
  case "$input" in
    *.gz)
      need_cmd gunzip
      tmp_csv="$(mktemp -t pgtool_restore_XXXX).csv"
      gunzip -c "$input" > "$tmp_csv"
      work_csv="$tmp_csv"
      ;;
    *.csv)
      : ;; # use as-is
    *)
      die "Input must be .csv or .csv.gz"
      ;;
  esac

  local base
  base="$(basename "$work_csv")"
  base="${base%.csv}"  # strip suffix

  derive_dest_table_from_base "$base" "$instance"

  info "Restoring into: $DEST_SCHEMA.$DEST_TABLE"

  if table_exists "$DEST_SCHEMA" "$DEST_TABLE"; then
    warn "Destination table $DEST_SCHEMA.$DEST_TABLE already exists; rows will be appended."
    warn "Pass --force-append to suppress this warning."
  else
    info "Creating $DEST_SCHEMA.$DEST_TABLE from CSV header (all columns TEXT)"
    create_table_from_csv_header "$DEST_SCHEMA" "$DEST_TABLE" "$work_csv"
  fi

  local copy_sql="\\copy \"$DEST_SCHEMA\".\"$DEST_TABLE\" FROM STDIN WITH (FORMAT csv, HEADER)"
  PSQL "$PGURI" -q -c "$copy_sql" < "$work_csv"
  info "Restore complete into: $DEST_SCHEMA.$DEST_TABLE"

  [ -n "${tmp_csv:-}" ] && rm -f "$tmp_csv"
}

# ---------- MAIN ----------
[ $# -lt 1 ] && usage
cmd="$1"; shift || true

case "$cmd" in
  backup)
    [ $# -ge 2 ] || usage
    need_cmd psql
    do_backup "$@"
    ;;
  restore)
    [ $# -ge 2 ] || usage
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

```python
#!/usr/bin/env python3
"""
pgtool.py — Backup & restore a Postgres table (full or date-filtered partial) to/from CSV (.csv or .csv.gz)

Requires: Python 3.8+, psycopg2-binary
  pip install psycopg2-binary

Usage:
  # Full-table backup (gzip by default)
  python pgtool.py backup dev weavix.silver.mytable

  # Month partial backup (January 2025) using timestamptz column "timecol"
  python pgtool.py backup dev weavix.silver.mytable --timecol timecol --date 2025-01

  # Day partial backup, no compression, custom dest dir
  python pgtool.py backup dev weavix.silver.mytable --timecol timecol --date 2025-01-15 --no-compress --dest /tmp

  # Restore from file; auto-creates table (TEXT cols) if it doesn't exist; appends if it does
  python pgtool.py restore dev /backups/dev_weavix.silver.mytable_timecol_2025-01.csv.gz
"""

import argparse
import csv
import gzip
import io
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2 import sql

# -------- Instance configuration (override with env) --------
DEST_DEFAULTS = {
    "dev":   os.environ.get("PGTOOL_DEST_DEV",   "/var/backups/pg/dev"),
    "prod":  os.environ.get("PGTOOL_DEST_PROD",  "/var/backups/pg/prod"),
    "test":  os.environ.get("PGTOOL_DEST_TEST",  "/var/backups/pg/test"),
    "local": os.environ.get("PGTOOL_DEST_LOCAL", "/var/backups/pg/local"),
}

PGURI = {
    "dev":   os.environ.get("PGURI_DEV",   "postgres://localhost:5432/postgres"),
    "prod":  os.environ.get("PGURI_PROD",  "postgres://localhost:5432/postgres"),
    "test":  os.environ.get("PGURI_TEST",  "postgres://localhost:5432/postgres"),
    "local": os.environ.get("PGURI_LOCAL", "postgres://localhost:5432/postgres"),
}
# ------------------------------------------------------------

IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SCHEMA_TABLE_RE = re.compile(r"^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$")
MONTH_FMT_RE = re.compile(r"^\d{4}-\d{2}$")
DAY_FMT_RE   = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)

def info(msg: str):
    print(f"INFO:  {msg}", file=sys.stderr)

def warn(msg: str):
    print(f"WARN:  {msg}", file=sys.stderr)

def assert_ident(name: str, kind: str = "identifier"):
    if not IDENT_RE.match(name or ""):
        die(f"Invalid {kind}: {name!r}")

def assert_schema_table(qual: str):
    if not SCHEMA_TABLE_RE.match(qual or ""):
        die(f"Invalid table name {qual!r} (expected schema.table)")

@contextmanager
def connect(instance: str):
    dsn = PGURI.get(instance)
    if not dsn:
        die(f"Unknown instance {instance!r} (expected dev|prod|test|local)")
    conn = psycopg2.connect(dsn)
    try:
        yield conn
    finally:
        conn.close()

def qualify(schema_table: str):
    assert_schema_table(schema_table)
    schema, table = schema_table.split(".", 1)
    return schema, table

def time_window_sql(timecol: str, date_arg: str) -> sql.SQL:
    assert_ident(timecol, "column")
    if MONTH_FMT_RE.match(date_arg):
        # [first day of month, first day of next month)
        return sql.SQL(
            "({col} >= date_trunc('month', to_date(%s,'YYYY-MM-DD')) "
            "AND {col} < (date_trunc('month', to_date(%s,'YYYY-MM-DD')) + interval '1 month'))"
        ).format(col=sql.Identifier(timecol)), [f"{date_arg}-01", f"{date_arg}-01"]
    if DAY_FMT_RE.match(date_arg):
        # [day, next day)
        return sql.SQL(
            "({col} >= to_timestamp(%s,'YYYY-MM-DD') "
            "AND {col} < (to_timestamp(%s,'YYYY-MM-DD') + interval '1 day'))"
        ).format(col=sql.Identifier(timecol)), [date_arg, date_arg]
    die("Invalid --date (use YYYY-MM or YYYY-MM-DD)")

def validate_timecol(conn, schema: str, table: str, col: str):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s AND column_name=%s
              AND data_type='timestamp with time zone'
        """, (schema, table, col))
        if not cur.fetchone():
            die(f"Column {schema}.{table}.{col} not found or not timestamptz")

def default_dest(instance: str) -> Path:
    d = DEST_DEFAULTS.get(instance)
    if not d:
        die(f"No default destination configured for instance {instance!r}")
    return Path(d)

def build_backup_filename(instance: str, schema: str, table: str,
                          timecol: str | None, date_arg: str | None) -> str:
    if timecol and date_arg:
        return f"{instance}_{schema}.{table}_{timecol}_{date_arg}.csv"
    return f"{instance}_{schema}.{table}.csv"

def backup(args):
    instance = args.instance
    schema, table = qualify(args.schema_table)
    dest_dir = Path(args.dest or default_dest(instance))
    dest_dir.mkdir(parents=True, exist_ok=True)

    timecol = args.timecol
    date_arg = args.date

    with connect(instance) as conn, conn.cursor() as cur:
        where_sql = None
        where_params = []
        if (timecol and not date_arg) or (date_arg and not timecol):
            die("Partial backup requires BOTH --timecol and --date")
        if timecol and date_arg:
            validate_timecol(conn, schema, table, timecol)
            where_sql, where_params = time_window_sql(timecol, date_arg)

        filename = build_backup_filename(instance, schema, table, timecol, date_arg)
        out_path = dest_dir / filename
        compress = not args.no_compress

        # Build COPY command
        if where_sql is None:
            copy_sql = sql.SQL("COPY {}.{} TO STDOUT WITH (FORMAT csv, HEADER, FORCE_QUOTE *)").format(
                sql.Identifier(schema), sql.Identifier(table)
            )
            params = None
        else:
            copy_sql = sql.SQL(
                "COPY (SELECT * FROM {}.{} WHERE {} ORDER BY 1) TO STDOUT WITH (FORMAT csv, HEADER, FORCE_QUOTE *)"
            ).format(
                sql.Identifier(schema),
                sql.Identifier(table),
                where_sql
            )
            params = where_params

        info(f"Backing up {schema}.{table} -> {out_path}{'.gz' if compress else ''}")

        if compress:
            with gzip.open(str(out_path) + ".gz", "wb") as gz:
                cur.copy_expert(copy_sql.as_string(conn), gz, vars=params)
            info(f"Backup complete: {out_path}.gz")
        else:
            with open(out_path, "wb") as f:
                cur.copy_expert(copy_sql.as_string(conn), f, vars=params)
            info(f"Backup complete: {out_path}")

def sanitize_colname(raw: str) -> str:
    # Strip quotes and spaces, keep A-Za-z0-9_, replace others with _
    raw = raw.replace('"', '').strip()
    cleaned = re.sub(r'[^A-Za-z0-9_]', '_', raw)
    if not cleaned:
        cleaned = "col"
    if cleaned[0].isdigit():
        cleaned = "_" + cleaned
    return cleaned

def ensure_schema(conn, schema: str):
    with conn.cursor() as cur:
        cur.execute("""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = %s) THEN
            EXECUTE format('CREATE SCHEMA %I', %s);
          END IF;
        END $$;
        """, (schema, schema))
        conn.commit()

def table_exists(conn, schema: str, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("""
          SELECT 1
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
          WHERE n.nspname=%s AND c.relname=%s AND c.relkind='r'
        """, (schema, table))
        return cur.fetchone() is not None

def create_table_from_csv_header(conn, schema: str, table: str, header_line: str):
    # Build TEXT columns from CSV header
    reader = csv.reader([header_line])
    cols = next(reader)
    if not cols:
        die("Empty CSV header; cannot create table")

    cleaned = [sanitize_colname(c) for c in cols]
    # Build DDL
    col_list = sql.SQL(", ").join(sql.SQL("{} text").format(sql.Identifier(c)) for c in cleaned)
    ddl = sql.SQL("CREATE TABLE {}.{} (").format(sql.Identifier(schema), sql.Identifier(table))
    ddl = sql.SQL("").join([ddl, col_list, sql.SQL(")")])

    ensure_schema(conn, schema)
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()

def parse_dest_table_from_filename(path: Path, instance: str) -> tuple[str, str]:
    """
    Accepts file names like:
      <instance>_<schema.table>.csv[.gz]
      <instance>_<schema.table>_<timecol>_<YYYY-MM>.csv[.gz]
      <schema.table>_<timecol>_<YYYY-MM-DD>.csv
      <schema.table>.csv
    Restored table name includes any suffix after schema.table, appended to the base table.
    """
    base = path.name
    if base.endswith(".gz"): base = base[:-3]
    if base.endswith(".csv"): base = base[:-4]

    # Strip leading "<instance>_"
    prefix = f"{instance}_"
    if base.startswith(prefix):
        base = base[len(prefix):]

    # schema.table is up to first underscore (if any)
    parts = base.split("_", 1)
    schema_table = parts[0]
    rest = parts[1] if len(parts) > 1 else ""

    if not SCHEMA_TABLE_RE.match(schema_table):
        die(f"Cannot parse schema.table from filename: {path.name}")

    schema, table = schema_table.split(".", 1)
    if rest:
        table = f"{table}_{rest}"
    return schema, table

def restore(args):
    instance = args.instance
    infile = Path(args.input)
    if not infile.exists():
        die(f"Input file not found: {infile}")

    with connect(instance) as conn:
        # Open file (gzip or plain)
        if infile.suffix == ".gz":
            opener = lambda p: io.TextIOWrapper(gzip.open(p, "rb"), newline="")
        else:
            opener = lambda p: open(p, "rt", newline="")

        with opener(str(infile)) as f:
            # Peek header safely without losing it
            header_pos = f.tell()
            header_line = f.readline()
            if not header_line:
                die("Input file is empty")
            # Normalize header (ensure one line without trailing newline)
            header_line = header_line.rstrip("\r\n")
            f.seek(header_pos)

            schema, table = parse_dest_table_from_filename(infile, instance)
            info(f"Restoring into: {schema}.{table}")

            # Create table if not exists; warn otherwise
            if table_exists(conn, schema, table):
                warn(f"Destination table {schema}.{table} already exists; rows will be appended.")
                if not args.force_append:
                    warn("Pass --force-append to suppress this warning.")
            else:
                info("Creating table from CSV header (all columns TEXT)")
                create_table_from_csv_header(conn, schema, table, header_line)

            # COPY FROM STDIN
            with conn.cursor() as cur:
                copy_sql = sql.SQL("COPY {}.{} FROM STDIN WITH (FORMAT csv, HEADER)").format(
                    sql.Identifier(schema), sql.Identifier(table)
                )
                cur.copy_expert(copy_sql.as_string(conn), f)
            conn.commit()
            info("Restore complete.")

def main():
    parser = argparse.ArgumentParser(prog="pgtool.py", description="Postgres CSV backup/restore (gzip by default)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_b = sub.add_parser("backup", help="Backup a table to CSV/.csv.gz")
    p_b.add_argument("instance", choices=PGURI.keys())
    p_b.add_argument("schema_table", help="Fully-qualified table name, e.g. weavix.silver.mytable")
    p_b.add_argument("--timecol", help="timestamptz column for date filtering")
    p_b.add_argument("--date", help="YYYY-MM or YYYY-MM-DD to filter by")
    p_b.add_argument("--no-compress", action="store_true", help="Write plain .csv instead of .csv.gz")
    p_b.add_argument("--dest", help="Destination folder (defaults by instance)")
    p_b.set_defaults(func=backup)

    p_r = sub.add_parser("restore", help="Restore CSV/.csv.gz into a table (auto-creates if needed)")
    p_r.add_argument("instance", choices=PGURI.keys())
    p_r.add_argument("input", help="Path to .csv or .csv.gz file")
    p_r.add_argument("--force-append", action="store_true", help="Suppress warning when table exists")
    p_r.set_defaults(func=restore)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

```
