## Command line

### lsof - show open files 
lsof +D /path/to/directory #  which processes are using files in a specific directory
lsof /var/log/syslog # which processes are using a particular file
fuser /var/log/syslog

### stdout stderr
```bash
script.sh 2> error.log
script.sh 1> out.log 2> err.log
script.sh &> combined_out_and_err.log
echo "This message goes to stderr" 1>&2
```
### 
```
awk '{print $2}' file.txt 
diff <(ls dir1) <(ls dir2)    # compares 2 folders
command1 & command2 & wait   # starts command1 and command2 in parallel and waits for both to finish.
command1 && command2 # Executes command2 only if command1 is successful.
command1 || command2  # Executes command2 if command1 fails.
myvariable=$(awk '{print $2}' file.txt | sort | uniq) 
```

### Find files: grep, rigrep, fzf, television

find . | grep -i searchpattern  
find / 2>/dev/null | grep -i searchpattern  

fzf (fuzzy finder) <https://junegunn.github.io/fzf/>

Television is a cross-platform, fast and extensible fuzzy finder TUI.
<https://github.com/alexpasmantier/television>
#### rigrep
```
rg '123456789012' -g '*.tf'
rg --type-list
rg "localhost:4531" --type python
rg "localhost:4531" --tpy
rg '123456789012' --type-not markdown
rg "hello" -A 1
rg "hello" -B 1
rg "hello" -C 1
rg crypto -g '!modules/' -g '!pypi/'  # Exclude a directory
rg --files | rg cluster  # find files
```
### tee
```bash
echo "Any text here.." | tee log.txt
./run_process.sh 2>&1 | tee process.log | grep "ERROR"
cat input.txt | tee step1.log | grep "filter_pattern" | tee step2.log | sort | tee final.log
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
Retry with timeout
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
