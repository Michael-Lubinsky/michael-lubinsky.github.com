### How to serialize MongoDB change stream into Azure Data Lake Storage Gen2 (ADLS v2) 
with partitioned folders like:

Partition path: db/collection/year=YYYY/month=MM/day=DD/hour=HH/
Rolling file name: events-YYYYMMDD-HH.jsonl
with 1 json line per event
