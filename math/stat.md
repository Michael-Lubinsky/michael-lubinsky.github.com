### Statistics and Probability

<https://itl.nist.gov/div898/handbook/toolaids/pff/index.htm>

<https://habr.com/ru/articles/1061846/> Все, что нужно знать про построение точечных оценок

### High-Dimensional Probability. Roman Vershinin 
<https://www.math.uci.edu/~rvershyn/papers/HDP-book/HDP-2.pdf>

<https://www.youtube.com/watch?v=nKmYjFoiuYM>

### Statistical Rethinking 2026 by Richard McElreath
<https://www.youtube.com/playlist?list=PLDcUM9US4XdMD5hEU5uinyBYFFPXMYBfn>

<https://leanpub.com/TOBoML2> The Orange Book of Machine Learning - Green edition

<https://stat.cmu.edu/~cshalizi/ADAfaEPoV/ADAfaEPoV.pdf> Advanced Data Analysis Book

<https://habr.com/ru/articles/1093010/> Extreme Events



Statistical Modeling: The Two Cultures. Leo Breiman
<https://projecteuclid.org/journalArticle/Download?urlId=10.1214%2Fss%2F1009213726>

<https://colah.github.io/posts/2015-09-Visual-Information/>

<https://python.plainenglish.io/from-bell-curves-to-rare-events-mastering-probability-distributions-like-a-pro-33b25ce8cc4b>

Hypotesis testing
<https://www.youtube.com/watch?v=AvUtMSI_4pM>

Производящая функция моментов:
<https://habr.com/ru/articles/1020734/>


<https://www.math.uci.edu/~rvershyn/papers/HDP-book/HDP-book.html> High-Dimensional Probability. Roman Vershynin

<https://medium.com/pythoneers/5-underrated-statistical-tests-you-didnt-know-you-needed-4224095233e8>

<https://samwho.dev/reservoir-sampling/> <https://news.ycombinator.com/item?id=43928315>  reservoir sampling

<https://www.mathpages.com/home/iprobabi.htm>



## Statistical Rethinking 2026
<https://www.youtube.com/watch?v=ztbYkBPDOgU> 
Statistical Rethinking 2026 - Lecture A01 by Richard McElreath

https://xcelab.net/rm/ Book: Statistical Rethinking by Richard McElreath

<https://www.tensortonic.com/ml-math/statistics/hypothesis-testing>

https://arxiv.org/abs/2401.00649 Linear Model and Extensions


## **Rejection sampling** 

### We have a function rand7() that generates a uniform random integer in the range [1,7].

Write a function rand10() that generates a uniform random integer in the range [1,10].
This is a classic **rejection sampling** problem.

---

### Solution: 
  Use `rand7()` to simulate a larger uniform space, then map it to `[1..10]`.

#### Step 1: Build a bigger uniform range

Call `rand7()` twice:

$$
num = (rand7() - 1) \times 7 + rand7()
$$


This gives a **uniform integer in [1..49]**.

---

####  Step 2: Rejection sampling

We only want numbers divisible cleanly into 10 buckets.

* Largest multiple of 10 ≤ 49 is **40**
* So:

  * If `num ≤ 40` → use it
  * If `num > 40` → reject and retry

---

####  Step 3: Map to [1..10]

 
$$
result = ((num - 1)\bmod 10) + 1
$$

 
###  Final Code For Rejection Sampling (Python)

```python
import random

def rand7():
    return random.randint(1, 7)

def rand10():
    while True:
        num = (rand7() - 1) * 7 + rand7()  # 1..49
        if num <= 40:
            return (num - 1) % 10 + 1
```

---

## 💡 Why this works

* `(rand7(), rand7())` creates **49 equally likely outcomes**
* We only keep the first 40 → still uniform
* 40 splits perfectly into 10 groups → each number has equal probability

---

## ⚡ Efficiency

* Acceptance rate = (40 / 49 \approx 81.6%)
* Very efficient for this problem

---
 

## Make Biased Coin from Unbiased Coin

We want to simulate a p-biased coin,  
that is, one which flips heads with probability p and tails with probability 1-p. 
But all we have access to is a stream of uniformly random bits.  
The result is that our algorithm will pick a result in an average of two bits, which might be kind of surprising.

The algorithm is:
```python
def biased_coin(p):
  flip = get_random_bit()
  if p < 0.5:
    return 0 if flip == 0 else biased_coin(2 * p)
  if p > 0.5:
    return 1 if flip == 1 else biased_coin(2 * p - 1)
  return flip
```
 
Here's why it works:   
generating an infinite sequence of random bits can be seen as generating a random binary fraction,  
which we then compare to p.   
It's a way to compute rand() < p.

But we actually only need a finite number of bits   
to determine whether that number is less than or greater than p.

b_1 b_2 ...
Where b_i contributes 2^-i to the final number if it's 1, and 0 otherwise.

Imagine the interval [0, 1]. Each time we learn a new digit to this number, we're slicing in half the point in space where it could live.   
If the first digit is 1, we know that it lives in [0.5, 1], for example.   
And in that case, if we know p is less than 0.5,   
we know the number we generated is greater than p.


<https://eyal-kazin.medium.com/>

Bayesian hierarchical time series with Prophet and PyMC3
<https://www.youtube.com/watch?v=jo12CWZ00Lo&list=PLGVZCDnMOq0rLLb519Ah3EntCUAAHPnfU>

РУКОВОДСТВО К РЕШЕНИЮ ЗАДАЧ ПО ТЕОРИИ ВЕРОЯТНОСТЕЙ И МАТЕМАТИЧЕСКОЙ СТАТИСТИКЕ
<https://elenagavrile.narod.ru/ms/gmurman.pdf>



Statistical process control in python  
<https://timothyfraser.com/sigma/statistical-process-control-in-python.html>

https://blog.keithmcnulty.org/



### Find the sum of 2 uniform distributions
- Two independent uniform distributions X ~ U[a,b], Y ~ U[c,d].
- They have the same mean and same standard deviation.


### 1) Determining the ranges:
For a uniform U[p,q]:
- Mean: mu = (p+q)/2
- Standard deviation: sigma = (q-p)/sqrt(12)

Having same mean and standard deviation implies:
b - a = d - c
and
(a + b)/2 = (c + d)/2  
which means:  
a = c, b = d

Thus: X and Y are identically distributed on the same interval [a,b].
 

### 2) Distribution of Z = X + Y

If X and Y are independent and uniform on the same interval [a,b], then:  
- The distribution of Z = X + Y will be the Irwin-Hall distribution of order 2  
  (the convolution of two uniform distributions).

Specifically:  
- The support will be: [2a, 2b]    
- The probability density function (PDF) of Z will be:
  
```
f_Z(z) =
    (z - 2a) / (b - a)^2 ,      for 2a <= z < a + b  
    (2b - z) / (b - a)^2 ,      for a + b <= z <= 2b  
    0 ,                         otherwise  
```
---

### 3) Properties of Z
- Shape: Triangular distribution (tent shape).
- Mean:  
E[Z] = E[X] + E[Y] = 2 * E[X] = 2 * mu
- Variance:  
Var[Z] = Var[X] + Var[Y] = 2 * sigma^2
- Standard deviation:  
sigma_Z = sqrt(2) * sigma


### Summary

The distribution of X + Y where X, Y are independent uniform distributions   
with the same mean and standard deviation is a triangular distribution on [2a, 2b] with a peak at a + b.  

The PDF is explicitly:
```
f_Z(z) =
    (z - 2a) / (b - a)^2 ,      for 2a <= z < a + b  
    (2b - z) / (b - a)^2 ,      for a + b <= z <= 2b  
    0 ,                         otherwise  
```


<https://habr.com/ru/articles/924770/>


### How to find the right distribution for your data

<https://medium.com/data-science-collective/how-to-find-the-right-distribution-for-your-data-a-practical-guide-for-non-statistician-with-two-dc2aa0ed707f>

<https://habr.com/ru/companies/tbank/articles/911900/> к какому классу распределения отнести нашу выборку?

<https://entropicthoughts.com/it-takes-long-to-become-gaussian>

#### Gini index 
<https://medium.com/data-science-collective/what-the-gini-index-really-tells-us-3624cf4189ac>

### Reservoir Sampling

<https://samwho.dev/reservoir-sampling/>

#### Monte Carlo 
<https://thenumb.at/Sampling/>

### Stat Rethinking
https://xcelab.net/rm/statistical-rethinking/  
https://www.goodreads.com/book/show/26619686-statistical-rethinking  
https://github.com/rmcelreath/stat_rethinking_2024

### T-test, Welch test
https://habr.com/ru/companies/X5Tech/articles/896182/

### What is desriptive measure of association

https://tracyrenee61.medium.com/statistics-interview-question-what-are-descriptive-measures-of-association-23ee9c7612b5


### Stat distributions in python
https://medium.com/data-bistrot/log-normal-distribution-with-python-7b8e384e939e  
https://medium.com/data-bistrot/bernoulli-distribution-with-python-0416e196e752  

https://medium.com/data-bistrot/bionomial-distribution-with-python-05d4a1725811  
https://medium.com/data-bistrot/uniform-and-normal-statistical-distribution-in-python-6d07fd5fc552


<https://medium.com/pythoneers/5-underrated-statistical-tests-you-didnt-know-you-needed-4224095233e8>

<https://www.statology.org/understanding-the-difference-between-parametric-and-nonparametric-tests/>


#### Poisson distrib   

https://medium.com/data-bistrot/poisson-distribution-with-python-791d7afad014

https://tracyrenee61.medium.com/use-python-to-understand-the-poisson-distribution-and-the-functions-associated-with-it-605a0bc31375


###  Tools for assessing normality of distribution: 

<https://agency.blastim.ru/media/tpost/me02yfomi1-nuzhno-li-proveryat-dannie-na-normalnost>
Tools for assessing normality of distribution: 
- Shapiro-Wilk test   
- Kolmogorov-Smirnov test  
- Anderson-Darling test  
- Lilliefors test  
- Jarque-Bera test  
 
<https://medium.com/@data-overload/the-shapiro-wilk-test-a-guide-to-normality-testing-d730e820d1a8>
 
```python
from scipy.stats import shapiro

data = [12.4, 14.6, 15.2, 14.9, 13.8, 13.7, 14.0]
stat, p = shapiro(data)
print('W-statistic=%.3f, p=%.3f' % (stat, p))
if p > 0.05:
    print("Data looks normal (fail to reject H₀)")
else:
    print("Data does not look normal (reject H₀)")
```
 
### EDA
https://github.com/ydataai/ydata-profiling

https://realpython.com/python-for-data-analysis/

https://www.kdnuggets.com/2021/07/single-line-exploratory-data-analysis.html

https://habr.com/ru/articles/922454/ кросс-энтропия позволяет оценить разницу между двумя распределениями

Power laws: https://habr.com/ru/companies/yandex_praktikum/articles/952084/

### CLT Central Limit Teorem

<https://news.ycombinator.com/item?id=44909133>

<https://agency.blastim.ru/media/tpost/me02yfomi1-nuzhno-li-proveryat-dannie-na-normalnost>

### Secretary_problem
https://en.wikipedia.org/wiki/Secretary_problem  
https://www.mccme.ru/free-books/mmmf-lectures/book.25.pdf  
https://habr.com/ru/articles/928338/ Разборчивая невеста 1/e

https://users.aalto.fi/~ave/ROS.pdf Regression and Other Stories

https://avehtari.github.io/ROS-Examples/index.html

https://bayesiancomputationbook.com/welcome.html

https://sites.stat.columbia.edu/gelman/book/

https://statmodeling.stat.columbia.edu/

https://sites.stat.columbia.edu/gelman/research/unpublished/stat50.pdf

https://stat110.hsites.harvard.edu/

https://www.pymc.io/projects/docs/en/stable/learn.html

### Paradoxes in Statistics

https://neerc.ifmo.ru/wiki/index.php?title=%D0%9F%D0%B0%D1%80%D0%B0%D0%B4%D0%BE%D0%BA%D1%81%D1%8B_%D1%82%D0%B5%D0%BE%D1%80%D0%B8%D0%B8_%D0%B2%D0%B5%D1%80%D0%BE%D1%8F%D1%82%D0%BD%D0%BE%D1%81%D1%82%D0%B5%D0%B9


https://cameralabs.org/9282-samye-izvestnye-paradoksy-v-teorii-veroyatnostej?ysclid=mgwqafe0pf804334367

https://medium.com/nuances-of-programming/%D0%BF%D1%8F%D1%82%D1%8C-%D0%BF%D0%B0%D1%80%D0%B0%D0%B4%D0%BE%D0%BA%D1%81%D0%BE%D0%B2-%D1%81-%D0%B2%D0%B5%D1%80%D0%BE%D1%8F%D1%82%D0%BD%D0%BE%D1%81%D1%82%D1%8C%D1%8E-%D0%BA%D0%BE%D1%82%D0%BE%D1%80%D1%8B%D0%B5-%D0%B2%D0%B0%D1%81-%D0%BE%D0%B7%D0%B0%D0%B4%D0%B0%D1%87%D0%B0%D1%82-710814dc78b8
