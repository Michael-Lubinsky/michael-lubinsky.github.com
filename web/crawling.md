## Web Crawling (scrapping)
robots.txt,
user agent, содержащий мою контактную информацию, 
хранил список исключённых доменов,
Устойчивость к сбоям. 

popular open source scrapers (Scrapy, Beautiful Soup, Selenium, 

<https://habr.com/ru/articles/894406/>

<https://andrewkchan.dev/posts/crawler.html>
<https://habr.com/ru/articles/1003120/>  (russian translation)

1,005 миллиарда веб-страниц

25,5 часа

$462


<img width="775" height="1191" alt="image" src="https://github.com/user-attachments/assets/44085bd3-a578-4b58-b15c-6825c9c28b20" />

### Scrapy (Python).
```
One of the best-known frameworks for web scraping. Written in Python, it is modular and highly efficient—built on top of the asynchronous Twisted network, 
which allows it to perform thousands of requests in parallel. 
Scrapy provides a complete “pipeline” for scraping: from managing the request queue and downloading pages to extracting data with selectors (XPath/CSS) 
and saving the results in the desired format (JSON, CSV, etc.). Out of the box, it supports multithreading, 
automatic adherence to delays between requests, and retrying failed requests. 
Scrapy’s scalability is proven in practice—Zyte (formerly Scrapinghub) processes over 3 billion pages per month using it. 
With proper configuration, this framework is capable of industrial-scale scraping. 
However, Scrapy has a learning curve: you must master its architecture (spiders, pipelines, middleware) and be able to write code for scrapers. 
On the plus side, it has extensive documentation, a large community, and many ready examples. It is BSD-licensed and free for commercial use.  
Scrapy is number one among open source scrapers in terms of capabilities and flexibility—an optimal choice for complex projects requiring speed and scalability.
```
### Selenium (Multilingual).
```
While Scrapy focuses on speed and static sites, Selenium is geared towards emulating a real browser. 
This open tool for browser automation was originally created for testing web applications but is widely used for scraping. 
Selenium supports scripts in various languages (Python, Java, C#, JavaScript, etc.) and controls real browsers (Chrome, Firefox, Safari, Edge) via drivers. 
It allows a scraper to view a page “as a user”: executing JavaScript, clicking buttons, scrolling, filling forms—making it suitable for complex dynamic sites. 
Its main advantage is its high compatibility with any web technology (Selenium can render even complex SPAs built with React/Vue). 
However, there are downsides: Selenium is slow and resource-intensive, as it launches a full-fledged browser. 
For simple pages, it is overkill, and for mass scraping, it is limited by CPU/RAM and is harder to scale (although Selenium Grid allows distributing browsers across multiple nodes). 
Benchmarks show that Selenium is significantly slower than specialized scrapers that do not render pages. Also, by default, 
Selenium does not hide its automation—the browser runs in headless mode and can be detected by a site's anti-bot scripts unless special stealth configurations are applied. 
Developers often enhance it with tools like undetected-chromedriver or by modifying navigator.webdriver to hinder detection.  
Selenium is a project with a rich history and documentation, making it a reliable choice when a full browser is indispensable. It is distributed under Apache 2.0.
```
### Headless Browsers: Puppeteer and Playwright (Node.js, Python).
```
In recent years, headless tools related to Chromium have gained great popularity.
• Puppeteer is a library from Google for Node.js that controls Chrome/Chromium via the DevTools protocol.
• Playwright is a similar tool from Microsoft, newer and supporting not only Chromium but also Firefox and WebKit, with clients available for Python and other languages.

Both tools allow a script to launch a headless browser, load a page, wait for JavaScript execution, and obtain the final HTML (or create screenshots, PDFs, etc.). 
Unlike Selenium, Puppeteer/Playwright work without a separate web driver, interacting directly with the browser engine—often providing better speed and stability.
For example, Playwright can launch multiple browser contexts in parallel, using resources more efficiently. 
Nevertheless, the overhead remains high: Puppeteer requires significant CPU and memory, and Playwright isn’t as lightweight as some alternatives. 
They are best used selectively, for pages where JavaScript rendering is indispensable.

Regarding bypassing protections, headless browsers have an advantage: they fully execute the site’s front-end code, including AJAX and SPA routing, 
and carefully handle timeouts and events. However, websites have learned to detect headless Chrome based on specific environmental properties. 
The community has responded with plugins such as puppeteer-extra-plugin-stealth, 
which mask most differences of headless mode (for example, by adding missing properties to navigator, introducing noise in Canvas, removing flags). 
With such add-ons, Puppeteer/Playwright can pass many anti-bot filters. Yet, this arms race between bot developers and anti-bot systems is ongoing. Overall, 
Puppeteer and Playwright have become the standard for complex scraping: they handle sites that require JavaScript exceptionally well, processing scripts, styles, and fonts like a real browser. 
Playwright stands out with its support for multiple engines and auto-connection capabilities via Docker and CI/CD. Both tools are available under Apache 2.0.
```
### Beautiful Soup and HTML Parsers (Python).
```
If the task is to quickly parse HTML or XML obtained from a server, BeautifulSoup4 is often chosen. 
This popular Python parser simplifies the parsing of HTML markup and searching for elements by tags, attributes, etc.
It is very user-friendly (hence its popularity among beginners) and robust in handling imperfect HTML—able to build a correct tree even from “broken” pages.
Note that BS4 does not download pages by itself; it is typically used alongside modules like requests. 
A nuance in BeautifulSoup’s performance is that it supports different “parsing engines”—the built-in Python html.parser (which is slow), the fast C-based lxml extension, and others. 
Using BeautifulSoup in combination with lxml can improve performance significantly (by approximately 24% in tests).
Nonetheless, pure lxml or specialized parsers can be even faster. 
For instance, the selectolax library (Python) using the lexbor HTML engine demonstrated the best page parsing time in benchmarks—around 0.002 seconds 
compared to approximately 0.05 seconds for BeautifulSoup on the same document. In real-world scenarios, this difference can be critical. 
Thus, for maximum speed, experienced developers might choose selectolax or direct lxml, but BeautifulSoup remains the most versatile and convenient solution. 
It supports CSS selector searches (via BeautifulSoup-select, though not as efficiently as lxml/XPath) and automatically converts various encodings. 
Its only limitation is that it cannot execute JavaScript (for which the aforementioned headless tools are needed). 
BeautifulSoup is licensed under MIT, and documentation is even available in Russian.
```
