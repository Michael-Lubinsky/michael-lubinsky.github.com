pip install uv

<https://mathspp.com/blog/uv-cheatsheet>

### uv init
This comand creates 4 files:
- .python-version: Specifies the Python version for the project.
- hello.py: A simple starter Python script.
- pyproject.toml: Configures project dependencies, build settings, and metadata.
- README.md: A template for documenting your project’s purpose and usage.

```
uv venv
.venv\Scripts\activate
uv add fastapi  # add dependency
uv remove fastapi
uv run pytest
uv run python --version
uv python install 3.9 3.10 3.11
uv venv --python 3.12.3
```
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

https://blog.dusktreader.dev/2025/03/29/self-contained-python-scripts-with-uv/

### uv  

https://docs.astral.sh/uv/

https://daniel.fastapicloud.dev/posts/til-2025-08-single-source-version-package-builds-with-uv-redux

https://lerner.co.il/2025/08/28/youre-probably-using-uv-wrong/

https://habr.com/ru/companies/otus/articles/940674/

https://www.saaspegasus.com/guides/uv-deep-dive/

https://martynassubonis.substack.com/p/python-project-management-primer-a55

https://www.peterbe.com/plog/run-standalone-python-2025

https://news.ycombinator.com/item?id=42676432

https://simonwillison.net/2024/Dec/19/one-shot-python-tools/

