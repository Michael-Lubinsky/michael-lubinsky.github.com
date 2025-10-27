### Git

<https://jvns.ca/blog/2024/02/01/dealing-with-diverged-git-branches/>

```git
# undo the last commit
git reset --soft HEAD~1

# fetches all updates from the remote
# and prunes (deletes) references to branches that have been deleted from the remote.
git fetch --all --prune

update the last commit without creating a new one.
git commit --amend
```

<https://habr.com/ru/companies/yandex_praktikum/articles/812139/>  
  
<https://medium.com/the-pythonworld/20-advanced-git-command-line-tricks-every-developer-should-know-03543884d3be>
