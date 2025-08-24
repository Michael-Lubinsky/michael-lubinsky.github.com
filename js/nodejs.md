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
