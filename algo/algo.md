### Algorithms

<https://ru.algorithmica.org/>

<https://www.algorithmsilluminated.org/>

<https://computablesecrets.com/videos>

<https://github.com/TheAlgorithms>  <https://the-algorithms.com>

<https://habr.com/ru/companies/timeweb/articles/1070742/> Count-Min Sketch
<https://habr.com/ru/companies/timeweb/articles/1055544/> Bloom Filter
<https://habr.com/ru/companies/timeweb/articles/1046345/> HyperLogLog: как найти уникальные значения в терабайте данных

<https://ledger.khushal.net/>

https://ledger.khushal.net/chapters/lsm-tree/

Advanced Algos by Jelani Nelson
<https://www.youtube.com/playlist?list=PL2SOU6wwxB0uP4rJgf5ayhHWgw7akUWSf>


<https://habr.com/ru/articles/1034790/> Bloom Filter  
<https://habr.com/ru/companies/timeweb/articles/1055544/> Bloom Filter implemented in C

<https://habr.com/ru/articles/1016636/>

<https://www.youtube.com/watch?v=8GieMMkLzMQ>

<https://www.youtube.com/playlist?list=PL4_hYwCyhAvbV381iK1q2d73h7FuIX8Rk>

<img width="471" height="143" alt="image" src="https://github.com/user-attachments/assets/1bfe9d36-f93c-464b-afd1-217a9149eccc" />

<https://www.youtube.com/playlist?list=PL4_hYwCyhAvbV381iK1q2d73h7FuIX8Rk> MPTI

<https://habr.com/ru/articles/985292/>  <https://habr.com/ru/articles/1024570/>

<https://cleveralgorithms.com/>

<https://thealgorithms.github.io/Python/>

<https://nestedsoftware.com/2018/04/04/exponential-moving-average-on-streaming-data-4hhl.24876.html>

<https://arxiv.org/pdf/2301.00754> Algos for Massive Data

<https://cs.gmu.edu/~sean/book/metaheuristics/>

<https://algorithmsbook.com/optimization/files/optimization.pdf>

<https://web.stanford.edu/group/sisl/public/dmu.pdf> Decision Making Under Uncertainty

<https://mykel.kochenderfer.com/textbooks/>

<https://www.amazon.com/Pearls-Algorithm-Engineering-Paolo-Ferragina/dp/1009123289>

## Idioms
<https://programming-idioms.org/all-idioms>

<https://www.cambridge.org/core/books/pearls-of-algorithm-engineering/95061352D7263CCCBD4F243018236EB2>

<https://jeffe.cs.illinois.edu/teaching/algorithms/book/Algorithms-JeffE.pdf>

Book “Information Theory” by Yury Polyanskiy and Yihong Wu.
<https://people.lids.mit.edu/yp/homepage/data/itbook-export.pdf>

<https://www.youtube.com/watch?v=qO-HpEgmd6U>

### Book: Information Theory, Inference, and Learning Algorithms. David J.C. MacKay

<https://www.inference.org.uk/itprnn/book.pdf>  
<https://videolectures.net/authors/david_mackay>

<https://github.com/ahammadmejbah/Fueling-Ambitions-Via-Book-Discoveries/tree/main>

<https://www.amazon.com/Guide-Competitive-Programming-Algorithms-Undergraduate/dp/3031617932>

## Type theory

<https://habr.com/ru/articles/758542/>

<https://habr.com/ru/articles/1063190/>



### Algebraic data types: Union types, sum types and product types

```
struct P {
    year: u16,
    number: u32
}
```
struct P is simply the Cartesian product of the two types,
That's why structs are called product types

#### union type   
is not composed of one field AND another, but instead one field OR another.

#### sum type 
Suppose you want to make a union type that contains either the year of the Gregorian calendar (stored in a u16), or the year according to the Hijri calendar (also stored in a u16). You can't express this as a union type 
``` 
T=u16∪u16=u16, because in your case, these two u16 are different things, that just happen to have the same representation, but shouldn't be conflated.

The solution is pretty straightforward: You create two new types that wrap the u16s, and serve as a "type tag" so the program knows how to interpret the data. Something like:

struct Year_Gregorian {
    val: u16
}

struct Year_Hijri {
    val: u16
}

union type Year {
    Year_Gregorian,
    Year_Hijri
}
This kind of type - a union type with each member tagged - is called a tagged union. It's also called a sum type. By now you can guess why it's called a sum type: The number of values of type Year is exactly the sum of its members: 

∣Year∣=∣Year 
Gregorian
​
 ∣+∣Year 
Hijri
​
 ∣.

Sum types are really useful when you want to be 100% sure you can distinguish all members of your union.
```
<https://viralinstruction.com/posts/uniontypes/>

<https://interjectedfuture.com/what-is-algebraic-about-algebraic-effects/>

https://blog.aiono.dev/posts/algebraic-types-are-not-scary,-actually.html

https://news.ycombinator.com/item?id=45248043

<https://iacgm.com/articles/adts/>

https://habr.com/ru/articles/957848/ Monads



https://cartesian.app/

https://github.com/tayllan/awesome-algorithms

<https://habr.com/ru/articles/924828/>

<https://news.ycombinator.com/item?id=45065705>

<https://www.instantdb.com/essays/count_min_sketch>  COUNT MIN SKETCH


### Hashing
https://habr.com/ru/articles/849654/  B-tree vs Hash tables

https://www.corsix.org/content/my-favourite-small-hash-table

https://javarevisited.substack.com/p/consistent-hashing-why-your-distributed

https://eli.thegreenplace.net/2025/consistent-hashing/

https://news.ycombinator.com/item?id=45411435

https://habr.com/ru/companies/ruvds/articles/850474/ Сравнение хранилищ данных AoS и SoA


https://habr.com/ru/articles/850296/  Sorting

https://habr.com/ru/companies/ruvds/articles/845652/  поиск собственных значений матриц

https://habr.com/ru/articles/904130/

