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
