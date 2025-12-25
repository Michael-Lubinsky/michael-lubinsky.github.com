Casual dependency between X and Y:  
if we change X then Y is changing, but if we change Y then X is not changing

Intervention: What if I do X?   p(y | do(x),z)
Counterfactuals: What if I had acted differently?  

https://changliu00.github.io/static/causality-basics.pdf

https://towardsdatascience.com/causality-an-introduction-f8a3f6ac4c4a/

https://www.inference.vc/untitled/

https://www.reddit.com/r/CausalInference/comments/1nk5mnc/asking_for_resources/

https://www.reddit.com/r/CausalInference/

https://www.pywhy.org/

https://www.youtube.com/watch?v=DZbLQ-WLrD0 Causal Inference on Time Series Data with the Tigramite Package

https://causalml-book.org/

https://mitpress.mit.edu/9780262037310/elements-of-causal-inference/

https://www.youtube.com/watch?v=gRkUhg9Wb-I  Causal Inference, Part 1. MIT OpenCourseWare

What is causal inference
https://www.youtube.com/watch?v=dFp2Ou52-po 


https://en.wikipedia.org/wiki/Rubin_causal_model

https://www.youtube.com/watch?v=LrmrH26EhSo

https://plato.stanford.edu/entries/causal-models/

https://www.coursera.org/learn/crash-course-in-causality

https://david-salazar.github.io/posts/causality/2020-08-10-causality-counterfactuals-clash-of-worlds.html

https://philsci-archive.pitt.edu/19773/1/Markus_Commentary_Revisions_Unblinded.pdf

https://statmodeling.stat.columbia.edu/2009/07/05/disputes_about/
```
The Rubin Causal Model (RCM) and Judea Pearl's Structural Causal Models (SCMs) are two major frameworks for causal inference, differing mainly in emphasis:

RCM (Potential Outcomes) focuses on what would happen (counterfactuals) to individuals under different treatments
 (e.g., the same person getting drug A vs. drug B),
ideal for experiments and defining causal effects via interventions (like do(X=x)),

whereas SCMs (Graphs/DAGs) use directed acyclic graphs to model relationships between variables, visualizing assumptions and allowing for complex causal structures,
 better at identifying causes for non-manipulable variables and handling collider bias.
While mathematically linked and sometimes equivalent for specific problems, RCM is data-centric (experiments),
and SCMs are model-centric (graphs/mechanisms), leading to different recommendations (e.g., what to control for). 
```



https://opensource.salesforce.com/causalai/latest/index.html

https://www.youtube.com/watch?v=B8J4uefCQMc The Master Algorithm | Pedro Domingos | Talks at Google

Rain leads to mud, not vice versa:
```  
  p(mud | rain) = 1.0
  p(rain | mud) = p(rain) 
```
Rook Cause Analysis Template
https://www.smartsheet.com/free-root-cause-analysis-templates-complete-collection?amp

### Common Cause Principle (Reichenbach’s Principle)

```
If two observables X and Y are statistically dependent, then there exists a variable 
Z such that conditioning on 
Z makes X and Y independent.
This variable Z is a causal explanation of their dependence.

What the principle is saying (intuitively)

If you see a correlation between two variables,
it should not be taken as fundamental.
There must be a causal reason for it. That reason can be:

1. A common cause Z, such 
Z→X and Z→Y

2. A direct causal link
X→Y or Y→X

The principle asserts that mere correlation without causal explanation is incomplete.

The three canonical causal explanations
1. Common cause
      Z
     / \
    X   Y

Z influences both 
X and Y

Conditioning on Z removes the correlation:

X⊥⊥Y∣Z

Example:

Z: degree of urbanization
X: stork population
Y: human birth rate

Urbanization reduces both storks and births → correlation explained.

2. Direct causation: X → Y

X itself is the explanatory variable
Conditioning on X trivially removes dependence
Interpretation:
Storks bring babies
Changes in stork population directly affect birth rate
Here, Z=X is the special case mentioned in the principle.

3. Reverse causation: Y → X
Babies attract storks

Conditioning on Y explains the dependence

Here, Z=Y is the explanatory variable

“If babies attract storks, it is Y→X.”

Why conditioning matters

The key idea is conditional independence:

Before conditioning:

P(X,Y) != P(X)P(Y)

After conditioning on the correct Z

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
But once you condition on 𝑍

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
### Distinguishing Causality from Correlation

```
Distinguishing between <keyword>correlation</keyword> and <keyword>causality</keyword> is a fundamental challenge in statistics and data science.  
While correlation measures the strength and direction of a linear relationship between two variables, causality implies that a change in one variable ($X$) is responsible for a change in another ($Y$).

**1. Formal Definitions and the Identification Problem**

<keyword>Correlation</keyword> is typically quantified by the <keyword>Pearson correlation coefficient</keyword> $\rho_{XY}$, defined as:

$$
\rho_{XY} = \frac{\text{cov}(X, Y)}{\sigma_X \sigma_Y}
$$

where $\text{cov}(X, Y)$ is the covariance and $\sigma$ represents the standard deviation. A non-zero $\rho_{XY}$ indicates that $X$ and $Y$ move together, but it does not specify the direction of influence or the existence of a mechanism.

<keyword>Causality</keyword> is defined using the <keyword>do-calculus</keyword> framework developed by Judea Pearl. We say $X$ causes $Y$ if the intervention to set $X$ to a specific value $x$ changes the probability distribution of $Y$:

$$
P(Y | \text{do}(X = x)) \neq P(Y)
$$

The "Identification Problem" arises because observational data only provides $P(Y | X)$, which may be influenced by <keyword>confounding variables</keyword> ($Z$) that affect both $X$ and $Y$.

**2. The Role of Confounding and Simpson's Paradox**

A common reason correlation fails to imply causation is the presence of a <keyword>confounder</keyword>. This can lead to <keyword>Simpson's Paradox</keyword>, where a trend appears in several groups of data but disappears or reverses when the groups are combined.

Consider a medical study comparing two treatments ($A$ and $B$) for kidney stones, categorized by stone size (small or large).

<d3-visual data-visual-id="vis_1766439368223_bhliygh0" data-visual-order="1" data-visual-status="completed" data-api-url="https://api-prod.gpai.app/api/visual/vis_1766439368223_bhliygh0"></d3-visual>

Using experimental data, we might find the following success rates:
- **Small Stones:** Treatment $A$ ($93.10\%$) > Treatment $B$ ($86.67\%$)
- **Large Stones:** Treatment $A$ ($73.00\%$) > Treatment $B$ ($68.75\%$)
- **Combined:** Treatment $B$ ($82.57\%$) > Treatment $A$ ($78.00\%$)

In this case, the aggregate correlation suggests $B$ is better, but the causal reality (when controlling for the confounder $Z$, stone size) is that $A$ is more effective.

**3. Experimental Solutions: Randomized Controlled Trials (RCTs)**

The "gold standard" for separating causality from correlation is the <keyword>Randomized Controlled Trial</keyword>. By randomly assigning subjects to a treatment group ($X=1$) or a control group ($X=0$), the researcher ensures that $X$ is independent of all potential confounders $Z$.

$$
X \perp Z \implies P(Y | \text{do}(X)) = P(Y | X)
$$

Randomization effectively "breaks" the arrows pointing into $X$ in a causal diagram, ensuring that any observed correlation must be due to the causal effect of $X$ on $Y$.

**4. Observational Solutions: Quasi-Experimental Designs**

When RCTs are unethical or impractical, researchers use econometric and statistical techniques to infer causality from observational data:

- **Instrumental Variables (IV):** Finding a variable $W$ (the instrument) that is correlated with $X$ but has no direct effect on $Y$ except through $X$.
- **Difference-in-Differences (DiD):** Comparing the changes in outcomes over time between a group that received a "treatment" and a group that did not.
  $$ \delta = (Y_{T, \text{post}} - Y_{T, \text{pre}}) - (Y_{C, \text{post}} - Y_{C, \text{pre}}) $$
- **Regression Discontinuity Design (RDD):** Exploiting a threshold or cutoff in a continuous variable that determines treatment assignment, allowing for a comparison of subjects just above and just below the threshold.

**5. Structural Equation Modeling and DAGs**

To formally separate causality, one must construct a <keyword>Structural Causal Model</keyword> (SCM). This involves:
- Mapping the assumptions about the system using <keyword>Directed Acyclic Graphs</keyword> (DAGs).
- Identifying "back-door paths" (paths from $X$ to $Y$ that start with an arrow pointing into $X$).
- Applying the **Back-door Criterion**: To identify the causal effect of $X$ on $Y$, one must condition on a set of variables $Z$ that blocks all back-door paths between $X$ and $Y$.

---

To separate causality from correlation, one must move beyond the data itself and incorporate **structural assumptions** or **experimental interventions**. Correlation is a property of the joint probability distribution $P(X, Y)$, whereas causality is a property of the mechanism that generates that distribution. The separation is achieved by either physically removing confounders via <keyword>randomization</keyword> or mathematically adjusting for them using <keyword>causal inference</keyword> frameworks.

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


 https://benjaminmanning.io/files/rs.pdf

https://arxiv.org/abs/2405.13100
https://github.com/kairong-han/causal_agent
https://openreview.net/pdf?id=pAoqRlTBtY


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


https://arxiv.org/abs/2405.13100 
https://github.com/kairong-han/causal_agent  
https://openreview.net/pdf?id=pAoqRlTBtY  
https://dl.acm.org/doi/fullHtml/10.1145/3397269  
https://imai.fas.harvard.edu/talk/files/AAAI19.pdf  

## AI Agents

https://www.reddit.com/r/AI_Agents/comments/1il8b1i/my_guide_on_what_tools_to_use_to_build_ai_agents/

https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf

n8n

https://medium.com/@neriasebastien/learning-how-to-build-ai-agents-7349f3821c3d


https://learn.microsoft.com/en-us/shows/ai-agents-for-beginners/


Simulating Human Behavior with AI Agents

https://hai.stanford.edu/policy/simulating-human-behavior-with-ai-agents

OASIS: Open Agent Social Interaction Simulations with One Million Agents.

https://github.com/camel-ai/oasis

AI Agents as Humans // Social experiments simulations

https://evoailabs.medium.com/ai-agents-as-humans-social-experiments-simulations-5140553533cd

 
