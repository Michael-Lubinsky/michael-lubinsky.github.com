## Web Crawling (scrapping)
robots.txt,
user agent, содержащий мою контактную информацию, 
хранил список исключённых доменов,
Устойчивость к сбоям. 

popular open source scrapers (Scrapy, Beautiful Soup, Selenium, 

<https://habr.com/ru/articles/894406/>

<https://habr.com/ru/companies/ruvds/articles/796885/>

<https://andrewkchan.dev/posts/crawler.html>
<https://habr.com/ru/articles/1003120/>  (russian translation)

1,005 миллиарда веб-страниц

25,5 часа

$462

### Scrapy
<https://doc.scrapy.org/en/latest/intro/overview.html>

<https://habr.com/ru/companies/sberbank/articles/748406/>


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


Commercial Solutions: API Services, Platforms, and SaaS for Web Scraping

Commercial tools are designed for situations when you need to “scrape without pain” – avoiding infrastructure management while obtaining a ready-made service. Typically, these are cloud platforms and APIs for scraping, offering powerful capabilities (large proxy pools, automatic bypassing of blocks, visual scraper builders) in exchange for subscription fees or pay-per-volume data pricing. Below, I will review several categories of such solutions:
API Services for Web Scraping and Proxies

These services are accessed via an HTTP API, where you supply a page URL and receive the HTML (or already structured data) in return. Internally, they handle all the “dirty work”: distributing requests across thousands of IP addresses, enforcing delays, solving CAPTCHAs. This approach is convenient for developers—you can integrate such an API call directly into your code without worrying about blocks. Leading API services include:

Scraper API – A specialized service with the slogan “get the HTML of any website via an API call.” Developers claim that with ScraperAPI, getting blocked is nearly impossible since the IP address changes with every request, failed attempts are automatically retried, and CAPTCHAs are solved for you. Indeed, the service substitutes proxies and user-agents, can bypass Cloudflare, and offers JavaScript rendering options. The interface is simple; for example, a GET request like
http://api.scraperapi.com?api_key=APIKEY&url=http://example.com
will return the page’s HTML. SDKs are available for Python, Node.js, and more. The service is in English, but the documentation is very detailed. ScraperAPI offers a free plan (up to 1,000 requests per month) and various pricing tiers starting at $29/month, making it one of the most popular solutions in its class.

Zyte (Scrapinghub) – A comprehensive cloud solution from the creators of Scrapy. It includes several products for scraping:
• Smart Proxy Manager (formerly Crawlera) – a distributed proxy with intelligent management;
• Splash – a proprietary headless browser for rendering pages;
• AutoExtract – an API for structured data extraction based on machine learning; and
• Scrapy Cloud – cloud hosting for your Scrapy crawlers.
Zyte’s approach is interesting because it combines open source and SaaS: you can write a scraper with Scrapy and run it in Scrapy Cloud, using Smart Proxy to bypass blocks and AutoExtract to immediately receive ready entities (products, articles, etc.) without manual rule writing. Zyte offers excellent documentation and SDKs, along with video tutorials and quick-start examples. However, the prices are significantly higher than a DIY approach: proxies start at $99/month for 200k requests, AutoExtract is billed separately, and a full enterprise package can cost thousands of dollars. Zyte is the choice for companies willing to pay for quality and enterprise-level support.

Bright Data (Luminati) – The largest proxy provider, which also offers a ready-made Web Scraping API. Their product, Web Unlocker, is positioned as an “all-in-one” solution for bypassing protections. Simply send a request via their API, and the system automatically sets the required headers, follows redirects, manages cookies, and even solves complex reCAPTCHA if needed. Essentially, Bright Data gives you access to its enormous network of millions of IP addresses (residential and mobile proxies) plus a set of scripts that mimic a real browser. As a result, you receive structured data from the desired website without the headache: “all you need to do is send a request – everything else (IP addresses, headers, cookies, CAPTCHAs) is taken care of by the system.” The downside is the cost: Bright Data is aimed at large businesses, with enterprise-level pricing (hundreds of dollars per month). Alternatives to Bright Data include Oxylabs with its Real-Time Crawler API and Web Unblocker, also targeted at maximum quality (and also expensive).

SerpAPI – A specialized API for obtaining search engine results (Google, Bing, Baidu, etc.). Scraping search results pages is complex due to constant HTML changes and strict rate limits. SerpAPI addresses this by providing ready-made endpoints: you send a request with parameters (e.g., q=USD RUB exchange rate for Google), and the service returns structured JSON with results—headlines, links, snippets, maps, and even widget data (e.g., weather, news). SerpAPI can emulate geolocation, device, and search language for accurate data. As a result, the developer receives search data via a clean API. The service offers a free plan (100 requests/month) and paid plans starting at $50/month. Its documentation and support are quite good, as evidenced by its popularity in SEO applications.
Cloud Platforms and Visual Scrapers (SaaS) - Alternative to free web scrapers

Another major group of commercial solutions are visual scraping tools, often presented as cloud services with a web interface or as desktop applications. Their target audience is not necessarily developers but anyone who needs to scrape something without digging into code; the key is to “set up a scraper without coding” by simply indicating the desired data on the page, after which the service automatically collects a large volume of information. Even experienced automation specialists can save time on routine tasks with these tools.

Octoparse – One of the most popular cloud scrapers featuring a point-and-click interface. The user launches the application (or web version), enters a website URL, and clicks to select the elements to extract. Octoparse builds a visual workflow: first, it navigates to a category page to collect links, then follows those links and extracts fields (such as title, price, etc.). It can simulate scrolling, clicking the “load more” button, logging into a site, and other interactive actions. No programming knowledge is required – everything is done via a GUI. To combat blocks, Octoparse provides automatic IP rotation: when scraping through their cloud, requests come from different IP addresses, protecting against simple bans (“foolproof” protection). It also offers task scheduling (for example, running the scraper every day at 9:00) and cloud storage for results. The free plan allows for up to 10k data points per month, which is sufficient for testing. Paid plans start at $89/month, offering more concurrent threads and data volume. The interface is in English but quite intuitive. Octoparse is popular among internet marketers and content managers attracted by the ability to obtain data “in just a few clicks.”

ParseHub – A similar tool by concept. This is a free desktop application (with a web dashboard) for scraping that also allows you to select data with the mouse. Marketed as “an advanced scraper that lets you extract data as easily as if you were clicking on it,” ParseHub focuses more on structuring results: it can directly export data in JSON, CSV, or Google Sheets via an API. ParseHub can recognize templated pages with pagination, load content that appears upon scrolling (infinite scroll), click on dropdown menus—everything needed for complex sites. The free version is limited to 200 pages per project; paid plans start at around $149/month, offering more parallel tasks and scheduling. ParseHub is an excellent choice when you need to quickly set up one-off scraping without writing code.

WebScraper.io – A well-known Chrome plugin (also available as a cloud service) that allows you to specify extraction elements directly in the browser, forming a kind of site map—a crawl plan. It supports dynamic AJAX sites, proxy servers, and multithreading. Interestingly, WebScraper is available as a free plugin but is monetized through a cloud platform with additional features (data storage, export to Dropbox/Google Sheets, API). In terms of capabilities, it is similar to Octoparse/ParseHub, although its interface is slightly less user-friendly. The paid Cloud Scraper plan starts at $50/month.

Apify – The previously mentioned platform also deserves attention as a SaaS solution. In addition to its open source SDK, Apify provides a ready-made cloud infrastructure: their website features a catalog of ready-made scripts (Actors) for popular websites—from an Amazon product scraper to an Instagram post collector. You can run these Actors and obtain data without writing code, or develop your own based on Crawlee and run it in the cloud. The advantage is its hybrid approach: combining a visual builder with the possibility of custom code. Apify offers a free tier (up to $10 in credits per month), which is sufficient for small projects; beyond that, you pay based on the resources used (RAM per hour and proxy requests). In the Apify interface, you can monitor progress in real time, view logs, and results are stored in a convenient repository. Apify also easily integrates with other services via an Open API and webhooks—allowing you to automate the entire chain (scrape data and immediately send it to Slack or Google Sheets).
Specialized and Unique Solutions

Finally, there are commercial tools that address niche or advanced scraping tasks.

Diffbot – An expensive but powerful AI scraper. Instead of selecting elements via traditional selectors, Diffbot uses computer vision and machine learning to automatically recognize the content of a page (news, product, article, comment, etc.) and extract the necessary fields. For example, if you provide Diffbot with a link to an article, it returns the headline, text, author, date, images—having determined these blocks by their design. There’s no need to write extraction rules—the service is trained on thousands of websites. Diffbot is especially effective for scraping a vast number of different domains (“it allows scaling scraping up to 10,000 domains”), forming a unified Knowledge Graph from all the collected data. It is used by large companies for news monitoring, mention analysis, and more. Pricing starts at $299/month and up (based on the number of pages processed). Nevertheless, it is a unique solution unmatched in intelligent data collection.

A-Parser – A popular desktop software for SEO scraping in the CIS (Windows/Linux). Unlike the other tools mentioned, A-Parser is distributed with a lifetime license (starting from $119) and runs locally. It is more like a combine harvester that integrates 70+ built-in scrapers for various tasks: from search engine results and suggestions from Google/Yandex to sitemap parsing, content collection, bulk link availability checking, etc. Over the years, A-Parser has become a versatile tool for SEO specialists. It offers flexible configuration: in addition to ready-made modules, you can write your own scraping templates using its built-in DSL (supporting RegExp, XPath, JavaScript). It even provides API access, allowing integration with your own scripts and remote task execution. In terms of bypassing blocks, A-Parser is designed for use with your own proxies—it supports hundreds of parallel threads with proxy lists and can randomize request parameters. In the SEO community, it is renowned for its speed and reliability (a program without an elaborate UI, but highly optimized). If your task is to collect search engine-related data, analyze competitors, or check website metrics, A-Parser is an excellent choice.

PhantomBuster – A service well-known in SMM automation circles. It provides a set of ready-made “phantoms” (scripts) for scraping data from social networks and other web platforms where traditional approaches are challenging. For example, there is a Phantom for extracting the contacts of everyone who liked an Instagram post or for collecting a list of event participants on LinkedIn. A distinctive feature of PhantomBuster is that it emulates the actions of a real user in a browser, often requiring you to provide your own cookies or access tokens for the target network. For developers, PhantomBuster is attractive as an outsourcing solution: you don’t need to develop your own bot for each social network—you can use a ready-made one. Prices are relatively low (starting from $30/month) for basic scenarios.
