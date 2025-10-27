##  YARN
```
cd packages/telemetry-stream-consumer
yarn add -D @azure/identity@^4.5.0 @azure/storage-file-datalake@^12.17.0
yarn workspace @weavix/telemetry-stream-consumer add @azure/storage-file-datalake@^12.17.0
```
Your root package.json file explicitly states:
```
"packageManager": "yarn@4.5.1",
"workspaces": [ "modules/*", "packages/*" ],
```

You need to use the correct package manager (Yarn) to install your dependencies.
```bash
corepack enable                  # comes with Node 16.10+
yarn set version stable
yarn install
yarn add -D typescript tsx @types/node


The -D flag is the equivalent of npm i --save-dev and will add these packages
to the devDependencies of the package.json file in your current working directory.

Since you are in a monorepo, if you want to install these dependencies for a specific package inside your monorepo
(e.g., in the eventhub-processor package), you should navigate to that package's directory and run the command from there.
```
Run index.ts:
```
cd src
npx tsx index.ts name=Alice times=3
```


⚠️ One correction: package names with a slash must be **scoped**. So use **`@weavix/common`** (✅ valid) instead of `weavix/common` (❌ invalid).

---

# File tree

```
weavix/
  common/
    package.json
    test/
      a.ts
  project1/
    package.json
    src/
      index.ts
package.json        # monorepo root
```

---

# 1) Root `package.json` (monorepo)

```json
{
  "name": "weavix-monorepo",
  "private": true,
  "packageManager": "yarn@stable",
  "workspaces": ["weavix/*"]
}
```

> If your repo already has a root `package.json`, just add `"private": true` and `"workspaces": ["weavix/*"]`.

---

# 2) `weavix/common/package.json`

This exposes your TS files directly (nice for dev with `tsx`). We also export the deep path `./test/a`.

```json
{
  "name": "@weavix/common",
  "version": "0.1.0",
  "private": false,
  "exports": {
    ".": "./test/a.ts",
    "./test/a": "./test/a.ts"
  },
  "types": "./test/a.ts"
}
```

> Keeping it simple: no build step; we’ll run with **tsx** which understands TypeScript directly.

---

# 3) `weavix/common/test/a.ts`

```ts
// weavix/common/test/a.ts
export function greet(name: string): string {
  return `Hello, ${name}!`;
}

export function add(a: number, b: number): number {
  return a + b;
}
```

---

# 4) `weavix/project1/package.json`

Declare the workspace dependency:

```json
{
  "name": "@weavix/project1",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "@weavix/common": "workspace:^"
  },
  "devDependencies": {
    "tsx": "^4.7.0",
    "typescript": "^5.5.4",
    "@types/node": "^20.14.2"
  },
  "scripts": {
    "dev": "tsx src/index.ts"
  }
}
```

---

# 5) `weavix/project1/src/index.ts`

You can import either the deep path **`@weavix/common/test/a`** or the package root **`@weavix/common`** (we exported both).

```ts
// weavix/project1/src/index.ts

// Option A: deep path
import { greet, add } from "@weavix/common/test/a";

// Option B: package root (thanks to exports ".": "./test/a.ts")
// import { greet, add } from "@weavix/common";

function main() {
  console.log(greet("Weavix"));
  console.log(`2 + 3 = ${add(2, 3)}`);
}

main();
```

---

# 6) Install & run (Yarn via Corepack)

```bash
# enable modern Yarn
corepack enable
yarn -v

# install deps for the whole monorepo
yarn install

# run project1
yarn workspace @weavix/project1 dev
```

If your repo expects `node_modules` (not PnP), set:

```bash
yarn config set nodeLinker node-modules
# or add to .yarnrc.yml at repo root:
# nodeLinker: node-modules
```

---

## Notes / variations

* If you prefer compiled output, give `@weavix/common` a small build step (tsc) and set `"main": "dist/index.js"`, `"types": "dist/index.d.ts"`. For quick dev, **tsx** is perfect.
* If you insist on npm instead of Yarn, the `workspace:` protocol won’t work—use Yarn for this setup.





You’re importing a **deep path that isn’t exported** by the `@weavix/snowflake-common` package:

```ts
// Fails because package "exports" blocks unknown subpaths:
import { greet, add } from "@weavix/snowflake-common/src/event-util/a";
```

When a package has an `"exports"` field, Node only allows the subpaths you explicitly list. Fix in one of two ways:

## Option A (simplest) — Import the package root

Update your import to use the root export:

```ts
// weavix/packages/telemetry-snowflake/src/index.ts
import { greet, add } from "@weavix/snowflake-common";

function main() {
  console.log(greet("Weavix"));
  console.log(`2 + 3 = ${add(2, 3)}`);
}
main();
```

…and make sure the common package exports that file from its root:

```json
// weavix/packages/snowflake-common/package.json
{
  "name": "@weavix/snowflake-common",
  "version": "0.1.0",
  "private": false,
  "exports": {
    ".": "./src/event-util/a.ts"
  }
}
```

## Option B — Keep a subpath import (export it explicitly)

If you prefer `@weavix/snowflake-common/event-util/a`, add subpath exports:

```json
// weavix/packages/snowflake-common/package.json
{
  "name": "@weavix/snowflake-common",
  "version": "0.1.0",
  "private": false,
  "exports": {
    ".": "./src/event-util/a.ts",
    "./event-util/a": "./src/event-util/a.ts",
    "./event-util/*": "./src/event-util/*.ts"
  }
}
```

Then in `index.ts`:

```ts
import { greet, add } from "@weavix/snowflake-common/event-util/a";
```

## Make sure the workspace is installed

From the **repo root** (where the root `package.json` lists `workspaces`), run Yarn so the workspace link is created:

```bash
corepack enable
yarn config set nodeLinker node-modules   # optional, if you want node_modules instead of PnP
yarn install
```

Then run your file (either):

```bash
# from project dir
yarn workspace @weavix/telemetry-snowflake tsx src/index.ts
# or if tsx is in devDependencies there:
npx tsx src/index.ts
```

> Bonus: your `weavix/packages/snowflake-common/config.json` looks like a `tsconfig.json` but has JSON errors (trailing commas) and a nonstandard name. If you need TS compiler settings, rename it to `tsconfig.json` and fix commas. If you’re only using `tsx`, you can skip it for now.


The issue is with your package exports configuration and how TypeScript/Node.js resolves the modules. Here are the problems and solutions:

## Problem 1: Package Exports Configuration

Your `snowflake-common/package.json` exports are pointing to `.ts` files, but at runtime Node.js needs `.js` files. The exports should point to compiled JavaScript files.

## Problem 2: Missing Main Entry Point

Your `snowflake-common` package doesn't have a `main` field, which can cause resolution issues.

## Problem 3: Import Path Mismatch

You're importing from `@weavix/snowflake-common/src/event-util/a` but your exports define `./event-util/a`, not the full `src/` path.

## Solutions:

**1. Fix snowflake-common/package.json:**
```json
{
  "name": "@weavix/snowflake-common",
  "version": "0.1.0",
  "private": false,
  "main": "dist/event-util/a.js",
  "types": "dist/event-util/a.d.ts",
  "exports": {
    ".": {
      "types": "./dist/event-util/a.d.ts",
      "require": "./dist/event-util/a.js",
      "import": "./dist/event-util/a.js"
    },
    "./event-util/a": {
      "types": "./dist/event-util/a.d.ts",
      "require": "./dist/event-util/a.js",
      "import": "./dist/event-util/a.js"
    }
  },
  "scripts": {
    "build": "tsc",
    "clean": "rm -rf dist"
  }
}
```

**2. Update your import in telemetry-snowflake/src/index.ts:**
```typescript
import { greet, add } from "@weavix/snowflake-common/event-util/a";
// Remove the "src/" part from the import path
```

**3. Build the snowflake-common package first:**
```bash
# From weavix/packages/snowflake-common
npm run build
# or
npx tsc
```

**4. Add root workspace package.json if missing:**
```json
{
  "name": "weavix",
  "private": true,
  "workspaces": [
    "packages/*"
  ]
}
```

**5. Install dependencies from root:**
```bash
# From weavix/ root
yarn install
```

## Alternative Quick Fix (Development Only):

If you want to import TypeScript files directly during development, change your import to use a relative path:
```typescript
import { greet, add } from "../../snowflake-common/src/event-util/a";
```

## Recommended Approach:

The proper solution is to build your TypeScript packages and reference the compiled JavaScript. This ensures your workspace behaves like real npm packages and will work in production environments.

Try building the `snowflake-common` package first, then running your code again. The error should resolve once Node.js can find the compiled JavaScript files.

# JavaScript

When you run a JavaScript program with Node.js, arguments you pass after the script name are available in `process.argv`.

By default:

* `process.argv[0]` → path to the `node` binary
* `process.argv[1]` → path to your script
* `process.argv[2..]` → arguments you typed after the script name

### Example 1: Passing named arguments

```bash
node app.js --name=Michael --age=40 --debug
```

Inside `app.js`:

```js
console.log(process.argv);
// [
//   '/usr/local/bin/node',
//   '/path/to/app.js',
//   '--name=Michael',
//   '--age=40',
//   '--debug'
// ]
```

You’ll need to parse these. A quick manual way:

```js
const args = {};
process.argv.slice(2).forEach(arg => {
  const [key, value] = arg.split("=");
  args[key.replace(/^--/, "")] = value ?? true; // if no value, set true
});

console.log(args); 
// { name: 'Michael', age: '40', debug: true }
```

### Example 2: Using a library (recommended)

Instead of manually parsing, use **minimist** or **yargs**:

```bash
npm install minimist
```

```js
const minimist = require("minimist");
const args = minimist(process.argv.slice(2));
console.log(args);
```

Run:

```bash
node app.js --name=Michael --age=40 --debug
```

Output:

```json
{ _: [], name: "Michael", age: 40, debug: true }
```

---

✅ **Summary:**

* Pass arguments as `--key=value` or `--key value` in the console.
* Access them via `process.argv`.
* For easier parsing, use `minimist` or `yargs`.

Here’s a **minimal reusable boilerplate** for parsing named arguments in a Node.js script without any external libraries:

```js
// args.js

function parseArgs(argv) {
  const args = {};
  argv.slice(2).forEach(arg => {
    if (arg.startsWith("--")) {
      const [key, value] = arg.slice(2).split("=");
      args[key] = value !== undefined ? value : true;
    } else {
      // positional arguments (not prefixed with --)
      if (!args._) args._ = [];
      args._.push(arg);
    }
  });
  return args;
}

// Example usage
const args = parseArgs(process.argv);
console.log(args);
```

### How it works

```bash
node args.js --name=Michael --age=40 --debug file1 file2
```

Output:

```json
{
  "name": "Michael",
  "age": "40",
  "debug": true,
  "_": ["file1", "file2"]
}
```

### Features

* Supports `--key=value` format
* Supports `--flag` (boolean true)
* Captures positional arguments in an array `_`

---

Would you like me to extend this so it also **auto-converts numbers and booleans** (e.g., `"40"` → `40`, `"true"` → `true`)?

Perfect 👍 Here’s the improved boilerplate that also **auto-converts numbers and booleans**:

```js
// args.js

function parseValue(val) {
  if (val === undefined) return true;          // --flag → true
  if (val.toLowerCase?.() === "true") return true;
  if (val.toLowerCase?.() === "false") return false;
  if (!isNaN(val) && val.trim() !== "") return Number(val);
  return val;
}

function parseArgs(argv) {
  const args = {};
  argv.slice(2).forEach(arg => {
    if (arg.startsWith("--")) {
      const [key, value] = arg.slice(2).split("=");
      args[key] = parseValue(value);
    } else {
      // positional arguments
      if (!args._) args._ = [];
      args._.push(parseValue(arg));
    }
  });
  return args;
}

// Example usage
const args = parseArgs(process.argv);
console.log(args);
```

### Example run

```bash
node args.js --name=Michael --age=40 --debug --active=false file1 123
```

### Output

```json
{
  "name": "Michael",
  "age": 40,
  "debug": true,
  "active": false,
  "_": ["file1", 123]
}
```

---

This way you don’t need any external library—booleans and numbers are handled automatically.



## Node
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

npm i @azure/event-hubs @azure/storage-file-datalake @azure/identity
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
