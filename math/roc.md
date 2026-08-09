## ROC

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

<img width="1080" height="1424" alt="image" src="https://github.com/user-attachments/assets/26e0fb3c-23ed-4f01-b825-919caa5fb44d" />


<img width="1080" height="1385" alt="image" src="https://github.com/user-attachments/assets/77dc4728-71e8-47e9-b0aa-f1c279d46b8c" />


<img width="1080" height="1350" alt="image" src="https://github.com/user-attachments/assets/e8e50537-8f36-472b-9ce5-0377c8317ed4" />
