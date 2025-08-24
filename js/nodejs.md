```bash
which node
/opt/homebrew/bin/node
node --version
v24.6.0
```

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
