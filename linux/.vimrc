cat ~/.vimrc
syntax on
filetype on
set number
set list
" set listchars=tab:▸-,trail:·
set listchars=tab:!·,trail:·
set hlsearch
set cursorline
set ts=4


set visualbell
set t_vb=
set t_Co=256

au BufNewFile,BufRead *.hql set filetype=sql
set background=dark
set nowrap
"  removes trailing whitespace from every line before saving a file
autocmd BufWritePre * :%s/\s\+$//e
:filetype plugin on
nnoremap <buffer> <F9> :exec 'w !python' shellescape(@%, 1)<cr>
