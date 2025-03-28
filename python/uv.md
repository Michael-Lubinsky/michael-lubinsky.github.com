https://medium.com/@nimritakoul01/uv-package-manager-for-python-f92c5a760a1c

https://thisdavej.com/share-python-scripts-like-a-pro-uv-and-pep-723-for-easy-deployment/
```
# Assuming you have pipx installed, this is the recommended way since it installs
# uv into an isolated environment
pipx install uv

# uv can also be installed this way
pip install uv
```
https://news.ycombinator.com/item?id=42855258

https://news.ycombinator.com/item?id=43500124

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
