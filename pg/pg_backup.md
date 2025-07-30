
https://medium.com/@heinancabouly/the-day-my-bash-script-saved-the-company-2-million-and-other-war-stories-cfa962d71030

```bash
create_redundant_backups() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="emergency_backup_$timestamp"
    
    # Strategy 1: Logical dump
    pg_dump production_db > "/backup/logical/$backup_name.sql" 2>/dev/null &
    local logical_pid=$!
    
    # Strategy 2: Binary backup  
    pg_basebackup -D "/backup/binary/$backup_name" 2>/dev/null &
    local binary_pid=$!
    
    # Strategy 3: Quick table export of critical data
    psql production_db -c "\copy users to '/backup/critical/users_$timestamp.csv' csv header" &
    psql production_db -c "\copy orders to '/backup/critical/orders_$timestamp.csv' csv header" &
    
    # Wait for logical and binary backups
    wait $logical_pid && echo "✅ Logical backup complete"
    wait $binary_pid && echo "✅ Binary backup complete"
    
    # Verify we actually got something
    [[ -s "/backup/logical/$backup_name.sql" ]] || {
        echo "❌ Logical backup failed or empty"
        return 1
    }
    
    echo "🎉 Backup $backup_name completed successfully"
}
# Run every 6 hours, because paranoia pays off
while true; do
    create_redundant_backups
    sleep 21600  # 6 hours
done
```
