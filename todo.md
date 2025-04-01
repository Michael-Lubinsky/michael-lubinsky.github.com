### How to use jekyll for static site:
https://chat-to.dev/post?id=296

https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax


### Jupyter on Jekyll
 
You don't need to manually convert your Jupyter Notebook to an HTML file to publish it on your GitHub Pages (github.io). Instead, you can use the following methods:

#### Option 1: Convert Notebook to HTML and Upload
Convert the .ipynb file to HTML using:


jupyter nbconvert --to html your_notebook.ipynb
Upload the HTML file to your GitHub repository under the docs/ folder or the root directory.

Enable GitHub Pages from your repository settings (set the source to main or docs).

Access your notebook via https://yourusername.github.io/your_notebook.html.

#### Option 2: Use nbviewer
```
If you want to keep your .ipynb file and avoid converting it manually:

Push the .ipynb file to your GitHub repository.
Use nbviewer to generate a public link by entering your GitHub file URL.
You can embed this nbviewer link on your GitHub Pages website.
Get the Raw GitHub URL of Your Notebook
Go to your GitHub repository and open your notebook.
Click the Raw button to get the direct URL of the notebook file.
Example:

https://raw.githubusercontent.com/yourusername/yourrepo/main/your_notebook.ipynb
Open Your Notebook in nbviewer

Visit https://nbviewer.jupyter.org/.

Paste the raw GitHub URL into the search box and click Go.

nbviewer will generate a direct link to view your notebook.

Use the nbviewer Link in Your GitHub Pages

Instead of manually converting your notebook to HTML, add the nbviewer link to your GitHub Pages site (index.md or README.md):
 
[View Notebook](https://nbviewer.jupyter.org/urls/raw.githubusercontent.com/yourusername/yourrepo/main/your_notebook.ipynb)
This ensures that your notebook is always accessible and updated when you push new changes.

Advantages of Using nbviewer
✅ No manual conversion – Always displays the latest version from GitHub.
✅ Supports interactive elements – nbviewer correctly renders rich outputs like plots and tables.
✅ Easy linking – You can share the nbviewer link anywhere, including on your GitHub Pages website.
```



#### Option 3: Use Jekyll and Jupyter Plugin (Advanced)
If you are using Jekyll for your GitHub Pages site, you can use the nbconvert plugin to render .ipynb files directly.


### Stat rethinking
https://xcelab.net/rm/statistical-rethinking/  
https://www.goodreads.com/book/show/26619686-statistical-rethinking  
https://github.com/rmcelreath/stat_rethinking_2024
 

### Probabilistic programming with NumPy powered by JAX for autograd and JIT compilation to GPU/TPU/CPU.
https://news.ycombinator.com/item?id=42156126  
https://num.pyro.ai/en/stable/ 
https://github.com/pyro-ppl/numpyro  

### Job-Scout
https://github.com/ShreeshaBhat1004/Job-scout
```
Job-Scout is a Python-based tool that aggregates remote job postings
in Machine Learning and Data Science from multiple sources, including Hacker News and Twitter (X).
The tool takes your resume in PDF format, analyzes it,
and ranks job listings based on how well they match your skills and experience.
With easy customization, you can also set it up to search for internships or specific job roles!
```
### Ask HN: What open source projects need help?

https://github.com/topics/help-wanted

https://www.codetriage.com/

https://www.codetriage.com/university/picking_a_repo

https://news.ycombinator.com/item?id=42157556

### ML
https://eli.thegreenplace.net/2024/ml-in-go-with-a-python-sidecar/
