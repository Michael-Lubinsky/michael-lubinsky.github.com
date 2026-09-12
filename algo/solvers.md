## SAT solvers
https://pysathq.github.io/

PySAT aims at providing a simple and unified incremental interface to a number of state-of-art Boolean satisfiability (SAT) solvers.



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

 





