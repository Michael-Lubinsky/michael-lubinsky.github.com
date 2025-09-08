<https://github.com/crescentpartha/CheatSheets-for-Developers>

Git <https://habr.com/ru/companies/yandex_praktikum/articles/812139/>  
MongoDB TUI <https://github.com/kopecmaciej/vi-mongo>  
Visidata <https://www.visidata.org/>


### JSON tools
command-line json viewer <https://jless.io/> 

```
jq '[path(..)|map(if type=="number" then "[]" else tostring end)|join(".")|split(".[]")|join("[]")]|unique|map("."+.)|.[]'

For example:

    $ curl -s 'https://ip-ranges.amazonaws.com/ip-ranges.json' | jq -r '[path(..)|map(if type=="number" then "[]" else tostring end)|join(".")|split(".[]")|join("[]")]|unique|map("."+.)|.[]'
```
https://news.ycombinator.com/item?id=44637716  jq
https://github.com/noperator/jqfmt

### CSV toolkits
https://github.com/medialab/xan   XAN is a command line tool to process CSV files  
https://bioinf.shenwei.me/csvtk/  
https://qsv.dathere.com/  
https://miller.readthedocs.io/  CSV, JSON processing

### GUI for CSV files
https://superintendent.app/  
https://www.tadviewer.com/

### DB Modelling Tools ERD
<https://medium.com/@kanishks772/from-code-to-diagram-in-seconds-the-lazy-developers-guide-b48987837bd3>  
<https://datasherpa.blog/>  
<https://medium.com/@billcoulam/i-tested-17-data-modeling-tools-one-was-the-clear-winner-ce2b7fc7c20e>

<https://monodraw.helftone.com/> diagram tool

### PDF to text
brew install poppler  
pdftotext -layout your_file.pdf output.txt

### MELD for diff
<https://meldmerge.org/>

### Folders navigation / file manager

https://github.com/jarun/nnn

https://github.com/gokcehan/lf

https://github.com/sxyazi/yazi

https://crates.io/crates/lstr

https://github.com/solidiquis/erdtree

https://github.com/Canop/broot

https://github.com/juftin/browsr

### Others
<https://www.linuxlinks.com/100-awesome-must-have-tui-linux-apps/>

https://github.com/navig-me/telert sends notifications when your terminal commands or Python code completes

гайд по настройке рабочего окружения: Linux, VScode, Python  
<https://habr.com/ru/companies/timeweb/articles/916040/>

### <https://devtoys.app/>
```
30 tools by default, and many more to be downloaded
#### Converters
 Cron Parser
 Date
 JSON Array to Table, CSV
 JSON <> YAML
 Number Base
#### Text
 Escape / Unescape
 List Comparer
 Markdown Preview
 Analyzer & Utilities
 Text Comparer
#### Encoders / Decoders
 Base64 Image
 Base64 Text
 Certificate
 GZIP
 HTML
 JWT
 QR Code
 URL
#### Formatters
 JSON
 SQL
 XML
#### Generators
 Hash / Checksum
 Lorem Ipsum
 Password
 UUID
#### Graphic
 Color Blind Simulator
 Image Converter
#### Testers
 JSONPath
 Regular Expression
 XML / XSD
#### Third party
 Duplicate Detector
 File Splitter
 JSON Schema
 JSON to PHP
 JSON to C#
 PNG Compressor
 Randomizer
 RESX Translator
 RSA Generator
 Semver Calculator
 Text Delimiter
 ULID Generator
 XSD Generator
 ```
