
Start your Python script like this:
```bash
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "flask==3.*",
# ]
# ///
import flask
# ...
```
And now if you chmod 755 it you can run it on any machine with the uv binary installed like this: ./app.py -  
and it will automatically create its own isolated environment and run itself with the correct installed dependencies  
and even the correctly installed Python version.

All of that from putting uv run in the shebang line!
