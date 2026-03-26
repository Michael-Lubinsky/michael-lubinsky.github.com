### Algorithms

<https://ru.algorithmica.org/>

<https://cleveralgorithms.com/>

<https://nestedsoftware.com/2018/04/04/exponential-moving-average-on-streaming-data-4hhl.24876.html>

<https://arxiv.org/pdf/2301.00754> Algos for Massive Data

<https://cs.gmu.edu/~sean/book/metaheuristics/>

<https://algorithmsbook.com/optimization/files/optimization.pdf>

<https://web.stanford.edu/group/sisl/public/dmu.pdf> Decision Making Under Uncertainty

<https://mykel.kochenderfer.com/textbooks/>

<https://www.amazon.com/Pearls-Algorithm-Engineering-Paolo-Ferragina/dp/1009123289>


<https://www.cambridge.org/core/books/pearls-of-algorithm-engineering/95061352D7263CCCBD4F243018236EB2>

<https://jeffe.cs.illinois.edu/teaching/algorithms/book/Algorithms-JeffE.pdf>

Book “Information Theory” by Yury Polyanskiy and Yihong Wu.
<https://people.lids.mit.edu/yp/homepage/data/itbook-export.pdf>

<https://www.youtube.com/watch?v=qO-HpEgmd6U>

<https://videolectures.net/authors/david_mackay>

<https://github.com/ahammadmejbah/Fueling-Ambitions-Via-Book-Discoveries/tree/main>

<https://www.amazon.com/Guide-Competitive-Programming-Algorithms-Undergraduate/dp/3031617932>

## Type theory

<https://habr.com/ru/articles/758542/>


## Constraint programming PiCat, MiniZinc, etc
https://cpmpy.readthedocs.io/en/latest/

https://ericpony.github.io/z3py-tutorial/guide-examples.htm  Z3 theorem proover

https://realpython.com/podcasts/rpp/213/

https://news.ycombinator.com/item?id=40867746

https://developers.google.com/optimization/cp

https://github.com/TimefoldAI/timefold-quickstarts

https://lpviz.net/

Here’s a clear comparison between **Picat** and **MiniZinc** — two languages often used for *declarative problem solving*, but with very different goals, paradigms, and ecosystems.

---

## 🔹 Core Purpose

| Feature             | **Picat**                                      | **MiniZinc**                                           |
| ------------------- | ---------------------------------------------- | ------------------------------------------------------ |
| **Paradigm**        | Multi-paradigm: logic, functional, imperative  | *Modeling language* for constraint solving             |
| **Primary Role**    | General programming + logic/CP                 | Constraint modeling for solvers                        |
| **Execution**       | Interpreter/compiler + built-in solver support | Compiles to FlatZinc; solved by external solvers       |
| **Target Audience** | Programmers needing search + logic + scripting | Researchers & modelers focusing on constraint problems |

---

## 🔹 What They’re Designed For

### 📌 Picat

Picat is a **full programming language** that blends:

* Logic programming (like Prolog),
* Functional programming,
* Scripting and control structures,
* Constraint solving.

You write *executable programs* with search, recursion, tables (memoization), CP, SAT/SMT, planning, dynamic programming, etc.

Example areas:

* Combinatorial search
* Dynamic programming
* Classic AI problems
* General scripting/algorithms

### 📌 MiniZinc

MiniZinc is a **declarative modeling language**. You *describe* a constraint problem (variables + constraints + objective) without specifying how to solve it. Then you choose an external solver like:

* Gecode
* Chuffed
* OR-Tools
* CPLEX
* Gurobi

It’s not meant for general programming — it’s meant to produce *models*.

---

## 🔹 Language Style & Syntax

### Picat

* Imperative + logic syntax
* You can write loops, functions, and logic rules
* Has built-in search and constraint constructs
* E.g., solving a puzzle with logic + search directly

### MiniZinc

* Purely declarative
* You define:

  * Variables (domains)
  * Constraints
  * Solve item (minimize, satisfy, etc.)
* No loops with side effects (loops are *generator* constructs)

---

## 🔹 How You Solve Things

### 🧠 In Picat

You write a search procedure *in the language*:

```picat
import cp.

solve(Assignment) =>
    Vars = [A,B,C],
    Vars :: 1..10,
    A + B #= C,
    solve(Vars),
    Assignment = Vars.

main =>
    println(solve(X)).
```

Picat has search built in.

### 📊 In MiniZinc

You *model* the problem, then run a solver:

```minizinc
var 1..10: A;
var 1..10: B;
var 1..10: C;

constraint A + B = C;

solve satisfy;
```

The MiniZinc compiler hands it to a solver.

---

## 🔹 Solvers and Backend

| Aspect                 | **Picat**                                          | **MiniZinc**                                      |
| ---------------------- | -------------------------------------------------- | ------------------------------------------------- |
| **Constraint solving** | Integrated CP + SAT + MIP (varies by version)      | External — you choose solvers                     |
| **Optimization**       | Supported natively through search strategies       | Defined with `solve` and handled by chosen solver |
| **Extension**          | You can embed programming logic around constraints | Focused on modeling; no general program control   |

---

## 🔹 Typical Use Cases

### Picat

✔ Algorithmic problems
✔ Planning + search (AI)
✔ Logic puzzles and heuristics
✔ Dynamic programming
✔ General scripting + constraint solving

### MiniZinc

✔ Scheduling
✔ Timetabling
✔ Classic optimization/CP benchmarks
✔ Research comparisons between solvers
✔ Teaching constraint modeling

---

## 📌 Key Differences Summarized

✔ **Picat is a full language** — you can write scripts and algorithms
✔ **MiniZinc is a modeling language** — you *describe* problems and hand them to solvers
✔ Picat’s constraint solving is built into the language
✔ MiniZinc leverages a *solver ecosystem* — you switch solvers without changing the model

---

## When to Choose Which?

**Pick Picat if:**

* You want a single language to program and solve
* You need custom search strategies or procedural logic
* You like logic programming

**Pick MiniZinc if:**

* You want to compare solvers easily
* You’re solving standard CP/optimization problems
* You don’t need general programming

 


## Idioms
https://programming-idioms.org/all-idioms





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

