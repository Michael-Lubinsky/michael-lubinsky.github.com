### Algorithms

https://github.com/tayllan/awesome-algorithms

https://www.youtube.com/watch?v=JZGacZrf-6M Top Leetcode Algo
#### Prefix sums 

https://habr.com/ru/articles/901190/

https://habr.com/ru/articles/901190/

#### Кнут, Моррис и Пратт  префикс-функцию

https://habr.com/ru/articles/843376/

#### Bloom filter

https://habr.com/ru/companies/ruvds/articles/864354/

#### Алгоритмы поиска путей - 


https://habr.com/ru/articles/856138/ Поиск в ширину Bread First Search

https://habr.com/ru/articles/856166/  Алгоритм Дейкстры

https://habr.com/ru/articles/904508/ dejkstra

https://habr.com/ru/articles/849894/ Поиск соседей в двумерном массиве

https://habr.com/ru/articles/849654/  B-tree vs Hash tables


https://habr.com/ru/companies/ruvds/articles/850474/ Сравнение хранилищ данных AoS и SoA


https://habr.com/ru/articles/850296/  Sorting

https://habr.com/ru/companies/ruvds/articles/845652/  поиск собственных значений матриц

https://habr.com/ru/articles/904130/



### Find the maximum area of connected 0's in a 2D binary array. 
The solution uses Depth-First Search (DFS) to explore connected regions of 0s.  
The function considers 4-directional connectivity (up, down, left, right).  
To include diagonals (8 directions), you'd expand the DFS to check all 8 neighbors.  


```python
def max_area_of_zeros(grid):
    if not grid or not grid[0]:
        return 0

    rows, cols = len(grid), len(grid[0])
    visited = [[False] * cols for _ in range(rows)]

    def dfs(r, c):
        if r < 0 or r >= rows or c < 0 or c >= cols:
            return 0
        if grid[r][c] != 0 or visited[r][c]:
            return 0
        visited[r][c] = True
        area = 1
        # Explore neighbors in 4 directions
        area += dfs(r+1, c)
        area += dfs(r-1, c)
        area += dfs(r, c+1)
        area += dfs(r, c-1)
        return area

    max_area = 0
    for i in range(rows):
        for j in range(cols):
            if grid[i][j] == 0 and not visited[i][j]:
                max_area = max(max_area, dfs(i, j))

    return max_area
```
