## Linux shell scripting

echo $?

nohup python3 app.py > output.log 2>&1 &

comm file1.txt file2.txt

### SIGTERM and trap
```bash
#!/bin/sh
cleanup() {
    echo "Received SIGTERM, shutting down gracefully..."
    sleep 5
    echo "Cleanup complete, exiting."
    exit 0
}
trap cleanup TERM


echo "App is running..."
while true; do sleep 1; done
```
kill --signal=SIGTERM program_id

```python
import signal
import time

def shutdown_handler(signum, frame):
    print("Received SIGTERM, shutting down gracefully...")
    time.sleep(5)
    print("Cleanup complete, exiting.")
    exit(0)

signal.signal(signal.SIGTERM, shutdown_handler)

print("Application running...")
while True:
    time.sleep(1)
```


### File watcher
```bash
#!/bin/bash
directory="/path/to/watch"
inotifywait -m -r -e create,modify,delete "$directory" |
while read path action file; do
    echo "File $file was $action."
done
```

#### Processing ever growing text file

To safely tail a growing file in real-time, line by line, and ensure only fully written lines  
(i.e., those ending with \n) are processed, you can use a Bash script like the following:  

```bash
#!/bin/bash

INPUT_FILE="/path/to/growing_file.txt"

# Path to the processing program
PROCESSOR="/path/to/your_processor_program"

# Read file in real-time using tail -n0 to avoid historical content
tail -n0 -F "$INPUT_FILE" | while IFS= read -r line; do
    # Only process complete lines (i.e., those ending with \n)
    if [[ -n "$line" ]]; then
        # Invoke external program with line as input
        "$PROCESSOR" "$line"
    fi
done
```


### jq
```bash
#!/bin/bash
json_string='{"name": "John", "age": 30}'
name=$(echo "$json_string" | jq -r '.name')
age=$(echo "$json_string" | jq -r '.age')
echo "Name: $name, Age: $age"
```

### lsof - show open files 
```
lsof +D /path/to/directory #  which processes are using files in a specific directory
lsof /var/log/syslog # which processes are using a particular file
fuser /var/log/syslog
```
### stdout stderr
```bash
script.sh 2> error.log
script.sh 1> out.log 2> err.log
script.sh &> combined_out_and_err.log
echo "This message goes to stderr" 1>&2
```
### awk
```
awk '{print $2}' file.txt
myvariable=$(awk '{print $2}' file.txt | sort | uniq)
```

### command chaining 
```bash
diff <(ls dir1) <(ls dir2)    # compares 2 folders
diff <(sort file1.txt) <(sort file2.txt)

command1 & command2 & wait   # starts command1 and command2 in parallel and waits for both to finish.
command1 && command2 # Executes command2 only if command1 is successful.
command1 || command2  # Executes command2 if command1 fails.

```

### Find files: grep, rigrep, fzf, television
```bash
find . | grep -i searchpattern  
find / 2>/dev/null | grep -i searchpattern  
find /var/log -type f -name "*.log" -exec grep -H "ERROR" {} \;
```
fzf (fuzzy finder) <https://junegunn.github.io/fzf/>

#### Television is a cross-platform, fast and extensible fuzzy finder TUI.
<https://crates.io/crates/television>  
<https://github.com/alexpasmantier/television>

#### ripgrep
https://github.com/BurntSushi/ripgrep
```
rg '123456789012' -g '*.tf'  # using glob to search files whose paths match the specified glob
rg pattern -tcsv --type-add 'csv:*.csv'   # add custom type csv
rg --type-list
rg "localhost:4531" --type python
rg "localhost:4531" --tpy
rg '123456789012' --type-not markdown
rg "hello" -A 1  # one line after
rg "hello" -B 1  # one line before
rg "hello" -C 1  # one line before and 1 line after
rg crypto -g '!modules/' -g '!pypi/'  # Exclude a directory
rg --files | rg cluster  # find files
rg -l 'pattern' -sort path   # return file names only
rg --files-without-match '\b(var|let|const)\b'
rg -F "hello.world" file.txt # searches for exactly hello.world instead of interpreting . as "any character"
```
### tee
```bash
echo "Any text here.." | tee log.txt
./run_process.sh 2>&1 | tee process.log | grep "ERROR"
cat input.txt | tee step1.log | grep "filter_pattern" | tee step2.log | sort | tee final.log
```

### file
```
$ file $(which useradd)
/usr/sbin/useradd: ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2 (...)

$ file $(which adduser)
/usr/sbin/adduser: Perl script text executable
```

### Shebang
```
#! /usr/bin/sh
#! /usr/bin/python3
```
### Monitor memory consumption
```bash
while true; do date; free -h; sleep 10; done >> system_usage.log
```
### Monitor resource consumption with Python
```python
import psutil

def system_stats():
    print("CPU Usage:", psutil.cpu_percent(interval=1), "%")
    print("Memory Usage:", psutil.virtual_memory().percent, "%")
    print("Disk Usage:", psutil.disk_usage('/').percent, "%")

if __name__ == "__main__":
    system_stats()
```
### Read with timeout
```bash
#!/bin/bash
echo "Enter something :"
if read -t 5 userInput; then
  echo "You entered $userInput"
else
  echo "Sorry, time out after 5 sec"
fi
```

### Retry with timeout
```bash
#!/bin/bash
TIMEOUT=5
TRIES=3
attempt=1

while [ $attempt -le $TRIES ]; do
  echo "Attempt$attempt/$TRIES: enter password (5 sec):"
  if read -t $TIMEOUT password; then
    if [ "$password" == "secret" ]; then
      echo "Welcome"
      break
    else
      echo "Wrong entry, try again"
    fi
  else
    echo "Timeout. You are slow."
  fi
  attempt=$((attempt + 1))
done

if [ $attempt -gt $TRIES ]; then
  echo "Sorry, too many attempts."
fi
```

### exec

```bash
#!/bin/bash
# Redirect stdout and stderr into file using exec и tee
exec &> >(tee -a script.log)
echo "This line goes to script.log!"
```
