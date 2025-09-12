Write the bash script pgtool.sh for backup and recovery postgres table. 
It could be a full or partial content of the table.
Output format: csv (optionally - compressed).

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
(without suffix .csv ot csv.zip), it should include the date, if it is part of file name.

If destination table already exists then show warning.

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
