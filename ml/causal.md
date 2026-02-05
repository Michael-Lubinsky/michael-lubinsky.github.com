### Causality

https://causalpython.io/

Causal Discovery Algorithms 
https://arxiv.org/pdf/2502.17030

### The Fast Casual Inference (FCI) algorithm
```
is a constraint-based method for causal discovery from observational data that explicitly accounts for the possibility of unobserved (latent) confounders and selection bias. Unlike many other algorithms (e.g., the standard PC algorithm), FCI does not assume "causal sufficiency," making it a robust tool for real-world scenarios where not all relevant variables are measured. Key Concepts Constraint-Based: FCI infers the causal structure by performing a series of conditional independence tests on the observed data.Partial Ancestral Graph (PAG): The output of the FCI algorithm is a PAG, which uses different edge endpoints (circles, arrowheads, tails) to represent the set of possible causal relationships consistent with the observed independencies (a Markov equivalence class). A bi-directed edge (\(\leftrightarrow \)) specifically indicates the presence of a latent confounder between two variables.Asymptotic Correctness: In the large sample limit, given the Causal Markov and Faithfulness assumptions, FCI is guaranteed to produce an asymptotically correct representation of the underlying causal structure, even with latent variables. How the FCI Algorithm Works (General Steps) The algorithm operates in three main stages: Skeleton Discovery: It starts with a complete undirected graph and removes edges between any pair of variables found to be conditionally independent given some subset of the remaining variables. This process uses conditional independence tests of increasing size.Collider Orientation: It identifies "v-structures" (colliders), where two variables are adjacent to a third but not to each other, and orient the edges accordingly (e.g., \(A\rightarrow B\leftarrow C\)).Edge Orientation Rules: A set of orientation rules are applied iteratively to resolve as many remaining ambiguous (circle-endpoint) edges as possible, using information from the already oriented parts of the graph. Advantages and Limitations Advantages: Handles Latent Confounders: The main advantage is its ability to operate and identify potential unmeasured confounders, which is a common problem in observational studies.Principled Uncertainty Representation: The use of PAGs and circle endpoints makes the output transparent about which causal directions are identifiable from the data and which remain uncertain, preventing overconfident claims. Limitations: Computational Cost: The number of conditional independence tests can grow exponentially with the number of variables, making the algorithm slow for large datasets (though variants like RFCI and GFCI have been developed to improve efficiency).Sample Size Sensitivity: The reliability of conditional independence tests depends heavily on sufficient sample size, and poor performance can result from noisy or small samples. Software Implementation The FCI algorithm is implemented in various open-source libraries for R and Python, such as the Tetrad software package and the causal-learn library. 
```
https://www.udemy.com/course/causal-ai-in-a-nutshell/learn/lecture/47006907#overview

https://www.unifr.ch/appecon/en/assets/public/uploads/introcausaldiscovery2.pdf

https://www.emergentmind.com/topics/causal-discovery-algorithms-cdas

https://www.youtube.com/watch?v=DrbqwNhHK9Y NeurIPS 2025 in San Diego. Causal Representations from Observational Data

https://habr.com/ru/companies/kuper/articles/990726/

https://www.youtube.com/watch?v=tvyuJZHJZvA

https://www.youtube.com/watch?v=PS9adB2ErkY

https://www.youtube.com/watch?v=WtNpneVKNoY

https://www.youtube.com/watch?v=g8vyOeLaGh0

https://www.causalmlbook.com/

https://www.amazon.com/Causal-Inference-Press-Essential-Knowledge/dp/0262545195  

https://ods.ai/tracks/causal-inference-in-ml-df2020

https://blog.neoforgelabs.tech/part-1-why-causality-matters-for-ai


https://www.youtube.com/watch?v=yqKJ9pUQ6Q8

https://www.youtube.com/watch?v=mujOFx5oZUQ  
Introduction to Causal Graphical Models: Graphs, d-separation, do-calculus

https://simons.berkeley.edu/sites/default/files/docs/18989/cau22-bcspencergordon.pdf


eyal-kazin.medium.com/causality-mental-hygiene-for-data-science-b7efc302eb72

https://www.youtube.com/watch?v=cnz17Q6g6Lw  
Chao Ma: Towards Causal Foundation Model: on Duality between Causal Inference and  Attention

https://www.youtube.com/watch?v=27ptGVVQflc

Anton Lebedevich: Causal Inference Intro
https://www.youtube.com/watch?v=V4ONp9PZrvk

https://habr.com/ru/companies/avito/articles/981614/

https://www.bradyneal.com/causal-inference-course

https://www.youtube.com/watch?v=1-t2ETBkuxQ


https://www.youtube.com/watch?v=66LBrNG2un0 PyWhy EconoML

https://www.youtube.com/@BradyNealCausalInference

The Granger causality test is a statistical hypothesis test for determining whether one time series is useful in forecasting another,
https://en.wikipedia.org/wiki/Granger_causality

https://bit.ly/m/alex-bio

https://dl.acm.org/doi/fullHtml/10.1145/3397269

Causal Inference and Discovery in Python: Unlock the secrets of modern causal machine learning with DoWhy, EconML, PyTorch and more
by Aleksander Molak 
https://www.amazon.com/dp/1804612987

Causal Inference in Python: Applying Causal Inference in the Tech Industry 
by Matheus Facure 
https://www.amazon.com/dp/1098140257/

https://github.com/py-why/dowhy

https://www.reddit.com/r/AskStatistics/comments/wm4uyg/rubin_causal_model_vs_pearl_causal_model/ 

Casual dependency between X and Y:  
if we change X then Y is changing, but if we change Y then X is not changing


### Inference methods
 - stratification
 - propensity scores
 - outcome regression
   

https://www.youtube.com/watch?v=XBJI-pQKDDY
```
Intervention: What if I do X?   p(y | do(x),z)
Counterfactuals: What if I had acted differently?
```


### Confounder

Confounder	(confounding variable)	a variable causally influences both treatment and outcome

https://en.wikipedia.org/wiki/Confounding
```
        Confounder
          |      |
          V      V
   Treatment  > Outcome

In causal inference, a confounder (or confounding variable) is a third variable
that influences both the exposure (cause) and the outcome (effect),
creating a false or distorted association between them,
 making it seem like the cause directly affects the effect when it's actually the confounder pulling the strings.
Confounders are a major problem in observational studies,
as they make it hard to isolate the true causal effect,
 leading to overestimated, underestimated, or even reversed conclusions about relationships,
like believing ice cream sales cause shark attacks because both rise with summer heat (the confounder). 
Key Characteristics
Common Cause: It's a variable that causes both the treatment/exposure (X) and the outcome (Y).
Not on Causal Pathway: It's not an intermediate step between the cause and effect;
it's external to that direct link.
Causes Bias: Ignoring it creates "confounding bias," distorting the observed relationship. 
Example
Study: Investigating if coffee (exposure) causes heart disease (outcome).
Confounder: Smoking (confounder).
 Smokers are more likely to drink coffee and smoking directly causes heart disease.

Problem: The observed link between coffee and heart disease might actually be due to smoking,
not the coffee itself, if smoking isn't accounted for. 
How to Address Confounding
Randomization: Randomly assigning treatments (like in RCTs) distributes confounders evenly, eliminating their effect.
Matching/Restriction: Ensuring groups are similar on potential confounders
(e.g., matching smokers with non-smokers).
Statistical Adjustment: Using methods like regression to statistically control for known confounders in observational data. 
```
https://changliu00.github.io/static/causality-basics.pdf

https://towardsdatascience.com/causality-an-introduction-f8a3f6ac4c4a/

https://www.inference.vc/untitled/

https://www.reddit.com/r/CausalInference/comments/1nk5mnc/asking_for_resources/

https://www.reddit.com/r/CausalInference/

https://www.pywhy.org/

## Causality in time series
https://www.youtube.com/watch?v=QVQoV22pPak

https://www.youtube.com/watch?v=DZbLQ-WLrD0 Causal Inference on Time Series Data with the Tigramite Package


Inferring causation from time series: state-of-the-art, challenges, and application cases
https://www.youtube.com/watch?v=ZjC8iDUST0E


https://causalml-book.org/

https://mitpress.mit.edu/9780262037310/elements-of-causal-inference/

https://www.youtube.com/watch?v=gRkUhg9Wb-I  Causal Inference, Part 1. MIT OpenCourseWare

https://www.youtube.com/watch?v=g5v-NvNoJQQ Causal Inference, Part 2. MIT OpenCourseWare

What is causal inference
https://www.youtube.com/watch?v=dFp2Ou52-po 


https://causal-learn.readthedocs.io/en/latest/

https://en.wikipedia.org/wiki/Rubin_causal_model

https://www.youtube.com/watch?v=LrmrH26EhSo

https://plato.stanford.edu/entries/causal-models/

https://www.coursera.org/learn/crash-course-in-causality

https://david-salazar.github.io/posts/causality/2020-08-10-causality-counterfactuals-clash-of-worlds.html

https://philsci-archive.pitt.edu/19773/1/Markus_Commentary_Revisions_Unblinded.pdf

https://statmodeling.stat.columbia.edu/2009/07/05/disputes_about/

https://kauzly.io/docs/
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


Kevin Klein - Causal Inference Libraries: What They Do, What I'd Like Them To Do 
https://www.youtube.com/watch?v=cRS4yZt6OU4&t=781s&pp=0gcJCU0KAYcqIYzv

https://mltechniques.com/product/ebook-state-of-the-art-in-genai-llms-creative-projects-with-solutions/

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

 
### diff-diff, the best library for Difference-in-Differences 

https://habr.com/ru/articles/986182/
```
Today we're launching v2, which is up to 2,000x faster than R. That's not a typo. We optimized the core computations and added an optional Rust backend to significantly improve performance.

DiD is the workhorse of causal inference. Policy evaluation, economics research, and testing at scale.

But if you wanted to do serious DiD work, you needed R. The Python ecosystem was fragmented, missing modern methods, and slow.

 What's inside:
 → Callaway-Sant'Anna (2021) for staggered adoption
 → Sun-Abraham interaction-weighted estimator
 → Synthetic DiD
 → Triple Difference (DDD)
 → Honest DiD sensitivity analysis
 → Wild bootstrap for few clusters
 → Event study plots
 → And more...

 The best part? It's validated against R packages (did, synthdid, fixest). Point estimates match to 10+ decimal places. And did I mention it's fast?

 sklearn-like API. Statsmodels-style output. No R dependency.
```
 pip install diff-diff
 


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

 
