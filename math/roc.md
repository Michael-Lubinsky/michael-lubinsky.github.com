## ROC
<https://developers.google.com/machine-learning/crash-course/classification/roc-and-auc>

The ROC curve (Receiver Operating Characteristic) shows how well a binary classifier separates classes across different thresholds. 
It plots True Positive Rate (Recall) on the Y-axis,   
and False Positive Rate on the X-axis.
Each point represents a different threshold.

It helps evaluate the trade-off between sensitivity and specificity, where  
- Sensitivity = True Positive / (True Positive + False Negative) or how well model detect positive  
- Specificity = True Negative / (True Negative + False Positive) how well model detects negatives  

A model that’s closer to the top-left corner is better.

Typical Metric derived from it are - 𝐀𝐔𝐂 (𝐀𝐫𝐞𝐚 𝐔𝐧𝐝𝐞𝐫 𝐭𝐡𝐞 𝐂𝐮𝐫𝐯𝐞).  
It ranges from 0.5 (random) to 1.0 (perfect). Higher AUC means better overall classification ability.

Example:
In a house price model predicting if a house will sell above $500k (yes/no),   
the ROC curve helps us choose a threshold for the predicted probability   
that balances catching most “yes” cases (true positives)   
without too many false alarms (false positives).

 
ROC is a threshold-independent way to assess classification performance

<img width="726" height="576" alt="image" src="https://github.com/user-attachments/assets/171c55f1-ad58-4d2f-95ee-487c5a546d94" />



<img width="1080" height="1385" alt="image" src="https://github.com/user-attachments/assets/77dc4728-71e8-47e9-b0aa-f1c279d46b8c" />


<img width="1080" height="1350" alt="image" src="https://github.com/user-attachments/assets/e8e50537-8f36-472b-9ce5-0377c8317ed4" />


**AUPRC** stands for **Area Under the Precision-Recall Curve**. It's a single number that measures how well a binary classifier finds the positive class, and it's especially useful when positives are rare.

### The curve

A classifier outputs a score for each example. Changing the threshold for calling something "positive" trades off two metrics:

- **Precision** = TP / (TP + FP): of everything flagged as positive, how much really is positive?
- **Recall** = TP / (TP + FN): of all real positives, how many were caught?

If you sweep the threshold from high to low and plot precision (y-axis) against recall (x-axis), you get the PR curve. AUPRC is the area under it, a value between 0 and 1.

### How to read it

- **1.0** means a perfect classifier: every positive is ranked above every negative.
- **The baseline is the positive rate, not 0.5.** A random classifier's AUPRC is about equal to the fraction of positives. With 1% fraud, random scores give about 0.01, so 0.30 is a big improvement. This is the most common thing people misread.

### Why use it instead of AUROC

AUROC (area under the ROC curve) uses the false positive rate, FP / (FP + TN). When negatives vastly outnumber positives, TN is huge, so even a large number of false positives barely moves the FPR. A model can score AUROC 0.95 and still bury every true positive under false alarms.

Precision has no TN term, so it shows that problem directly.

Example: 1,000 fraud cases among 1,000,000 transactions. A model catches 900 of them while flagging 9,000 legitimate transactions.
- FPR = 9,000 / 999,000 ≈ 0.9%, so the ROC curve looks excellent.
- Precision = 900 / 9,900 ≈ 9%, so 10 out of 11 alerts are false. That shows up in AUPRC.

**Rule of thumb:** use AUPRC when positives are rare and you care about the quality of what gets flagged (fraud, anomaly detection, medical screening, retrieval or search, defect detection). AUROC is fine for roughly balanced classes, or when both kinds of error matter equally.

### Computing it

```python
from sklearn.metrics import average_precision_score, precision_recall_curve, auc

ap = average_precision_score(y_true, y_score)        # usual choice

prec, rec, _ = precision_recall_curve(y_true, y_score)
auprc_trap = auc(rec, prec)                            # trapezoidal, slightly optimistic
```

**Average Precision (AP)** is a step-wise sum, Σ (Rₙ − Rₙ₋₁) · Pₙ. It's the standard way to estimate AUPRC, and most papers and libraries treat the two names as the same thing. Trapezoidal interpolation between PR points tends to overestimate, because precision doesn't change linearly between thresholds. In Spark, `BinaryClassificationEvaluator(metricName="areaUnderPR")` computes it at scale.
