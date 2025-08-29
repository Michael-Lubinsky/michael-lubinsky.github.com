```bash
which node
/opt/homebrew/bin/node
node --version
v24.6.0
```


 `npm i` is shorthand for `npm install`.

What it does (by default, in the current folder):

* Reads `package.json` and installs all `dependencies` (and `devDependencies` unless you omit them) into `node_modules/`.
* Honors `package-lock.json`/`npm-shrinkwrap.json` if present (installs the exact locked versions; creates `package-lock.json` if missing).
* Runs install lifecycle scripts (e.g., `preinstall`, `install`, `postinstall`, `prepare`).
* Since npm v7+, also installs peer dependencies when possible.

Common variants:

```bash
npm i                 # install deps from package.json
npm i --omit=dev      # skip devDependencies (similar to --production)
npm i lodash          # add to dependencies (writes to package.json)
npm i -D typescript   # add to devDependencies
npm i -g vercel       # install globally
npm i lodash@^4       # install with a version range
npm i --save-exact lodash@4.17.21  # pin exact version
```

Related:
`npm ci` is for clean, reproducible installs in CI: it **only** uses `package-lock.json`, fails if it’s out of sync, and removes `node_modules` before installing.



Install nvm with Homebrew
```bash
brew update
brew install nvm
mkdir -p ~/.nvm
```
Add to ~/.zshrc (zsh is your shell)
```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$(brew --prefix nvm)/nvm.sh" ] && . "$(brew --prefix nvm)/nvm.sh"
[ -s "$(brew --prefix nvm)/etc/bash_completion.d/nvm" ] && . "$(brew --prefix nvm)/etc/bash_completion.d/nvm"
```

Reload shell and install Node 18
```bash
exec zsh
nvm install 18
nvm alias default 18
node -v
npm -v
corepack enable    # enables yarn/pnpm shims included with Node 18
```

Tip: per-project version pin
```bash
echo "18" > .nvmrc
nvm use            # auto-switches to 18 in that folder
```


`"type": "commonjs"` in `package.json` tells Node to treat **.js files as CommonJS modules** by default in that package.

### What that means

* **Default for .js:** `require()` / `module.exports`
* **ESM not enabled for .js:** `import/export` won’t work in plain `.js` unless you use `.mjs` or switch to `"type":"module"`
* **Extensions still override:**

  * `.cjs` → always CommonJS
  * `.mjs` → always ES Module

### Quick matrix

| package.json `"type"` | `.js` behavior | `.cjs`   | `.mjs`    |
| --------------------- | -------------- | -------- | --------- |
| `"commonjs"` (yours)  | CommonJS       | CommonJS | ES Module |
| `"module"`            | ES Module      | CommonJS | ES Module |
| (omitted)             | CommonJS       | CommonJS | ES Module |

### CommonJS vs ESM snippets

```js
// CommonJS (.js with "type":"commonjs" or .cjs)
const express = require('express');
module.exports = { foo: 1 };
```

```js
// ES Module (.mjs or .js with "type":"module")
import express from 'express';
export const foo = 1;
```

### When to change it

* If you want to use `import/export` in `.js`, set `"type": "module"` **or** rename files to `.mjs`.
* If you prefer `require()` everywhere, keep `"commonjs"`.

### Interop tips

* From CJS → ESM package: `const pkg = await import('some-esm-only').then(m => m.default ?? m);`
* From ESM → CJS module: `import pkg from 'some-cjs';` (default import usually works), and use `createRequire` if you need `require`.

Given your earlier “Cannot use import statement outside a module” error: switch to `"type": "module"` **or** rename the file to `.mjs` if you want to keep `import` syntax.



#### JS code example: Simple timer Using setInterval 

Using setInterval (every minute, aligned to the start of each minute)  
File: minute-ticker-interval.js
```js
// file: minute-ticker-interval.js
'use strict';

// Print current time
function logTime() {
  const now = new Date();
  console.log(now.toISOString());
}

// Align to the next :00 second of the next minute, then tick every 60s
(function start() {
  const now = Date.now();
  const msUntilNextMinute = 60_000 - (now % 60_000);

  setTimeout(() => {
    logTime();                     // first tick exactly at HH:MM:00
    setInterval(logTime, 60_000);  // then every minute
  }, msUntilNextMinute);
})();

// graceful exit
process.on('SIGINT', () => {
  console.log('\nStopped.');
  process.exit(0);
});
```

Run
```
node minute-ticker-interval.js
```

#### JS code example: Simple timer Using node-cron
File minute-ticker-cron.js
```
// file: minute-ticker-cron.js
'use strict';

const cron = require('node-cron');

// Print current time
function logTime() {
  const now = new Date();
  console.log(now.toISOString());
}

// Runs at the top of every minute.
// Optionally set a timezone (replace with your TZ if desired).
cron.schedule('* * * * *', logTime, {
  timezone: 'America/Los_Angeles' // omit this line to use system local time
});

console.log('Cron schedule started: * * * * *');
```

Install and run
```
npm init -y
npm i node-cron
node minute-ticker-cron.js
```

`npm init -y` (same as `npm init --yes`) creates a **default `package.json`** in the current folder **without asking any questions**. It auto-answers all prompts with defaults and does **not** install anything.

What it does:

* Generates `package.json` with default fields (name, version, main, scripts.test, license, etc.).
* Uses npm’s init defaults from your config (`npm config get init-*`) when available.
* Does **not** create `node_modules` or `package-lock.json` (those appear when you install packages).

Typical result (example):

```json
{
  "name": "current-folder-name",
  "version": "1.0.0",
  "description": "",
  "main": "index.js",
  "scripts": { "test": "echo \"Error: no test specified\" && exit 1" },
  "keywords": [],
  "author": "",
  "license": "ISC"
}
```

Notes:

* Run it inside your project directory.
* If a `package.json` already exists, `npm init` will use it as a base and fill/update fields using defaults.
* You can set your own defaults once so future `npm init -y` uses them:

  ```
  npm config set init-author-name "Your Name"
  npm config set init-author-email "you@example.com"
  npm config set init-license "MIT"
  npm config set init-version "0.1.0"
  ```
* Check current defaults:

  ```
  npm config get init-author-name
  npm config get init-license
  ```

#### Warning: Failed to load the ES module:  list_all.js. Make sure to set "type": "module" in the nearest package.json file or use the .mjs extension.

npm pkg set type=module

This adds "type": "module" to package.json, so .js files are treated as ES modules.
