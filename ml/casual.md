### Common Cause Principle (Reichenbach’s Principle)

```
If two observables X and Y are statistically dependent, then there exists a variable 
Z such that conditioning on 
Z makes X and Y independent.
This variable Z is a causal explanation of their dependence.

What the principle is saying (intuitively)

If you see a correlation between two variables, it should not be taken as fundamental. There must be a causal reason for it. That reason can be:

A common cause

𝑍
→
𝑋
Z→X and 
𝑍
→
𝑌
Z→Y

A direct causal link

𝑋
→
𝑌
X→Y or 
𝑌
→
𝑋
Y→X

The principle asserts that mere correlation without causal explanation is incomplete.

The three canonical causal explanations
1. Common cause
      Z
     / \
    X   Y


𝑍
Z influences both 
𝑋
X and 
𝑌
Y

Conditioning on 
𝑍
Z removes the correlation:

𝑋
⊥
 ⁣
 ⁣
 ⁣
⊥
𝑌
∣
𝑍
X⊥⊥Y∣Z

Example:

𝑍
Z: degree of urbanization

𝑋
X: stork population

𝑌
Y: human birth rate

Urbanization reduces both storks and births → correlation explained.

2. Direct causation: 
𝑋
→
𝑌
X→Y
X → Y


𝑋
X itself is the explanatory variable

Conditioning on 
𝑋
X trivially removes dependence

Interpretation:

Storks bring babies

Changes in stork population directly affect birth rate

Here, 
𝑍
=
𝑋
Z=X is the special case mentioned in the principle.

3. Reverse causation: 
𝑌
→
𝑋
Y→X
Y → X


Babies attract storks

Conditioning on 
𝑌
Y explains the dependence

Here, 
𝑍
=
𝑌
Z=Y is the explanatory variable

Note: In your text, the sentence
“If babies attract storks, it is X.”
should read:
“If babies attract storks, it is 
𝑌
→
𝑋
Y→X.”

Why conditioning matters

The key idea is conditional independence:

Before conditioning:

𝑃
(
𝑋
,
𝑌
)
≠
𝑃
(
𝑋
)
𝑃
(
𝑌
)
P(X,Y)

=P(X)P(Y)

After conditioning on the correct 
𝑍
Z:

𝑃
(
𝑋
,
𝑌
∣
𝑍
)
=
𝑃
(
𝑋
∣
𝑍
)
𝑃
(
𝑌
∣
𝑍
)
P(X,Y∣Z)=P(X∣Z)P(Y∣Z)

If no such Z exists, your causal model is incomplete.

Why this principle is foundational
1. Separates correlation from causation

Correlation alone does not tell you:

which variable causes which

or whether both are effects of something else

The Common Cause Principle gives the search space for causal explanations.

2. Basis of causal graphs (DAGs)

Modern causal inference (Pearl, Rubin) relies on this idea:

dependencies must be explainable by causal structure

unexplained dependencies signal missing variables

3. Explains Simpson’s paradox

Aggregated data may show correlation:

𝑋
̸
 ⁣
⊥
 ⁣
 ⁣
 ⁣
⊥
𝑌
X

⊥⊥Y

But once you condition on 
𝑍
Z:

𝑋
⊥
 ⁣
 ⁣
 ⁣
⊥
𝑌
∣
𝑍
X⊥⊥Y∣Z

This is exactly the Common Cause Principle in action.

Important limitations

The principle assumes causal sufficiency
(that all relevant common causes can, in principle, be represented)

In quantum mechanics, violations occur (Bell correlations)

In practice, the true Z may be unobserved or unmeasurable

Practical takeaway

When you observe a dependency:Do not stop at correlation

Ask:

Is there a common cause?
Is there direct causation?
Is the causation reversed?

Test whether conditioning on plausible Z removes the dependence

In data engineering / telemetry terms:

Correlated signals often share hidden operational causes

Conditioning on time, device, user, or environment frequently breaks “mysterious” correlations
```
https://en.wikipedia.org/wiki/Causal_model

https://plato.stanford.edu/entries/causal-models/

https://lesswrong.ru/w/%D0%9A%D0%B0%D1%83%D0%B7%D0%B0%D0%BB%D1%8C%D0%BD%D0%BE%D1%81%D1%82%D1%8C_%D0%B1%D1%8B%D1%81%D1%82%D1%80%D0%BE%D0%B5_%D0%B2%D0%B2%D0%B5%D0%B4%D0%B5%D0%BD%D0%B8%D0%B5

https://www.reddit.com/r/CausalInference/comments/1nk5mnc/asking_for_resources/

https://www.amazon.com/dp/1633439917  Causal AI by Robert Osazuwa Ness  

https://www.reddit.com/r/CausalInference/comments/1o7gqlu/timeseries_causal_modeling/

https://static1.squarespace.com/static/675db8b0dd37046447128f5f/t/691fb7706ce66332f0b44467/1763686256720/hernanrobins_WhatIf_21nov25.pdf

https://www.reddit.com/r/CausalInference/

https://en.wikipedia.org/wiki/Causality

https://dl.acm.org/doi/fullHtml/10.1145/3397269

https://arxiv.org/abs/1809.09337

https://yanirseroussi.com/2016/02/14/why-you-should-stop-worrying-about-deep-learning-and-deepen-your-understanding-of-causality-instead/

https://medium.com/@akelleh/a-technical-primer-on-causality-181db2575e41#.e0g0dq5zj

https://aeon.co/essays/causal-understanding-is-not-a-point-of-view-its-a-point-of-do

https://yanirseroussi.com/2016/05/15/diving-deeper-into-causality-pearl-kleinberg-hill-and-untested-assumptions/

https://www.salesforce.com/blog/causalai/

https://github.com/msuzen/looper

https://engineered.network/causality/

https://gwern.net/everything

Judea Pearl   “The Book of Why” 

https://bayes.cs.ucla.edu/BOOK-99/book-toc.html

http://singapore.cs.ucla.edu/LECTURE/lecture_sec1.htm

https://www.michaelnygard.com/blog/2021/06/counterfactuals-are-not-causality/

https://blog.jliszka.org/2013/12/18/bayesian-networks-and-causality.html

https://christian.bock.ml/posts/mlss_causality/

https://arxiv.org/abs/1911.10500

https://arxiv.org/abs/2202.00436

https://github.com/msuzen/looper/blob/v0.2.3/looper.md

https://michaelnielsen.org/ddi/if-correlation-doesnt-imply-causation-then-what-does/

https://news.ycombinator.com/item?id=8158341

https://news.ycombinator.com/item?id=32779896

https://news.ycombinator.com/item?id=40038620

https://news.ycombinator.com/item?id=44118718

https://news.ycombinator.com/item?id=16152808

https://news.ycombinator.com/item?id=27963974

https://news.ycombinator.com/item?id=13542294

https://news.ycombinator.com/item?id=26670312

https://news.ycombinator.com/item?id=37663523

https://news.ycombinator.com/item?id=24931923

https://news.ycombinator.com/item?id=25471098

<https://miguelhernan.org/whatifbook>



https://matheusfacure.github.io/python-causality-handbook/landing-page.html

<https://paperswithcode.com/paper/causalml-python-package-for-causal-machine> 

package for causal inference and statistical modeling in brain time series
<https://github.com/alecrimi/effconnpy>

https://www.cs.cmu.edu/~bziebart/publications/thesis-bziebart.pdf

pycausalimpact: https://pypi.org/project/pycausalimpact/

https://habr.com/ru/articles/832466/

https://scott.am/

https://www.linkedin.com/in/scottamueller/





https://www.dailydoseofds.com/a-crash-course-on-causality-part-1

https://www.youtube.com/watch?v=eyuGTZu6bQk

---

https://habr.com/ru/companies/megafon/articles/657747/

https://habr.com/ru/companies/ru_mts/articles/485980/ uplift

https://habr.com/ru/companies/vk/articles/518100/

https://habr.com/ru/companies/uzum/articles/817473/

https://www.youtube.com/watch?v=KeO2E3UIIwE&list=PLXBwTSS5__Kn9VmkyyhzLicuS3F34M-BG& 

https://habr.com/ru/companies/ods/articles/667730/

https://habr.com/ru/companies/X5Tech/articles/768008/

https://habr.com/ru/articles/693532/

https://habr.com/ru/companies/sberbank/articles/847382/

https://habr.com/ru/companies/sberbank/articles/847406/

https://habr.com/ru/articles/832466/

https://habr.com/ru/companies/piter/articles/852440/

https://habr.com/ru/articles/705694/

https://habr.com/ru/companies/ods/articles/544208/

https://habr.com/ru/articles/870874/ Causal Inference методы на практике

