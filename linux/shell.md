### Command line

script.sh 2> error.log

script.sh 1> out.log 2> err.log

script.sh &> combined_out_and_err.log

echo "This message goes to stderr" 1>&2

grep "pattern" <<< "Here is the long text with pattern inside"


### tee
echo "Any text here.." | tee log.txt

./run_process.sh 2>&1 | tee process.log | grep "ERROR"

cat input.txt | tee step1.log | grep "filter_pattern" | tee step2.log | sort | tee final.log

### Read with timeoot
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
# Файл: read_retry.sh
# Несколько попыток ввода с таймаутом

TIMEOUT=5
TRIES=3
attempt=1

while [ $attempt -le $TRIES ]; do
  echo "Попытка $attempt/$TRIES: введите пароль (5 секунд на ответ):"
  if read -t $TIMEOUT password; then
    if [ "$password" == "secret" ]; then
      echo "Доступ разрешен. Добро пожаловать!"
      break
    else
      echo "Неверный пароль. Попробуйте еще раз."
    fi
  else
    echo "Таймаут! Вы слишком медлили."
  fi
  attempt=$((attempt + 1))
done

if [ $attempt -gt $TRIES ]; then
  echo "Слишком много попыток. Доступ запрещен."
fi
```

### exec

```bash
#!/bin/bash
# Redirect stdout and stderr into file using exec и tee
exec &> >(tee -a script.log)
echo "This line goes to script.log!"
```
