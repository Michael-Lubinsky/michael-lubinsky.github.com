
### Python dependency management

https://nielscautaerts.xyz/python-dependency-management-is-a-dumpster-fire.html

https://martynassubonis.substack.com/p/python-project-management-primer

https://martynassubonis.substack.com/p/python-project-management-primer-a55

https://news.ycombinator.com/item?id=42676432

### pip 

https://www.techbeamers.com/python-pip-usage/

https://pip.pypa.io/en/stable/

export PIP_REQUIRE_VIRTUALENV=true`  
will force you to not install packages in the system site-packages.

To check dependencies:  
  python -m pip check  
To get a JSON output of your current virtual environment:  
  python -m pip inspect  
To update stuff automatically:  
  python -m pip install --upgrade   
Or, skip worrying about dependencies:  
  python -m pip install --no-deps
  
Do a dry run installation with full report on what would be installed:  
pip install --ignore-installed --dry-run --quiet --report

Display only those packages that are not dependencies of other installed packages.  
python -m pip list --not-required  
```
python -m pip: This runs the pip module as a script using the specified Python interpreter.
list: This subcommand lists all installed Python packages in the current environment.
--not-required: This flag filters the output to display only those packages that are not dependencies of other installed packages.

If you get SSL errors (common if you are in a hotel or a company network):   
python -m pip install pendulum --trusted-host pypi.org --trusted-host files.pythonhosted.org

If you are behind a corporate proxy that requires authentication:  
python -m pip install pendulum --proxy http://your_username:yourpassword@proxy_address

If you want to download a package without installing it, you can use  
python -m pip download NAME

It will download the package and all its dependencies in the current directory
(the files, called, wheels, have a .whl extension).
You can then install them offline by doing
python -m pip install
on the wheels.

```
### venv

On Windows, use  
   py -3.X -m venv MY_ENV  
to create a virtual environment, and   
   MY_ENV\Scripts\activate  
to use it.

On Mac and Linux, to create a virtual environment:
    python3.X -m venv MY_ENV 
 and to activate it:  
  source MY_ENV/bin/activate” 


Once you have activated a virtual environment, you can install a thing by doing

python -m pip install thing


### 
```
You don't need to activate a virtual environment to use it! This is just a convenience feature.
If you use the commands situated in the Scripts (on windows) or bin (on Unix) folders
in the virtual environment directly,  
 they are specially crafted to only see the virtual environment even without activation.
In fact, activating just make those commands the default ones by manipulating a bunch of environment variables.


The statement "You don't need to activate a virtual environment to use it" means  
that even if you don't explicitly activate a virtual environment  
(e.g., with source venv/bin/activate or .\venv\Scripts\activate),  
 you can still use the environment by referencing its Python executable directly.
```
### How Virtual Environments Work
```
When you create a virtual environment in Python (using python -m venv venv or similar tools like virtualenv), a directory is created with:

A standalone Python interpreter specific to the virtual environment.
Its own site-packages directory for storing dependencies installed within the virtual environment.

Activation
Activating a virtual environment is essentially a convenience feature:

It modifies your shell environment so that:
The virtual environment's Python interpreter is used by default  
(e.g., running python refers to venv/bin/python instead of the system Python).
Commands like pip install packages into the virtual environment.
It often changes the shell prompt to indicate that the virtual environment is active.

Using a Virtual Environment Without Activation
Even if you don't activate the environment, you can use it by directly referencing the Python executable in the virtual environment.

Examples:
Running Python directly:

 
path/to/venv/bin/python script.py      # On macOS/Linux
path\to\venv\Scripts\python script.py  # On Windows

This ensures that the script runs using the virtual environment's Python and its installed packages.

Installing dependencies without activation:
Instead of activating, you can point pip directly to the virtual environment:

 
path/to/venv/bin/pip install requests      # macOS/Linux
path\to\venv\Scripts\pip install requests  # Windows

When Might You Avoid Activation?

In automated scripts or CI/CD pipelines where you can directly specify
the virtual environment's Python executable.
When you want to run isolated commands without modifying your shell environment.
Benefits of Activation
It’s simpler and more intuitive for interactive use.
Ensures that the environment's python and pip are automatically used without needing to specify their full paths every time.
Provides visual feedback via the modified shell prompt to remind you that you're working within the virtual environment.
```


###  pyenv

https://news.ycombinator.com/item?id=42419822

brew info --json python3 | jq -r '.[].versioned_formulae[]'

### pipx

https://zahlman.github.io/posts/2025/01/07/python-packaging-2/

### uv  

https://docs.astral.sh/uv/

https://daniel.fastapicloud.dev/posts/til-2025-08-single-source-version-package-builds-with-uv-redux

https://habr.com/ru/companies/otus/articles/940674/

https://www.saaspegasus.com/guides/uv-deep-dive/

https://martynassubonis.substack.com/p/python-project-management-primer-a55

https://www.peterbe.com/plog/run-standalone-python-2025

https://news.ycombinator.com/item?id=42676432

https://simonwillison.net/2024/Dec/19/one-shot-python-tools/

