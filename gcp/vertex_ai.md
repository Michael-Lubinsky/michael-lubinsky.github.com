## Vertex AI 
is Google Cloud’s managed platform for building, training, deploying, and operating AI models.** It supports both traditional machine learning and generative AI. [Google Cloud overview](https://github.com/GoogleCloudPlatform/vertex-ai-samples)

You can use it to:

- **Train custom models**, such as fraud detection or sales forecasting.
- **Use existing foundation models**, including Gemini, through APIs.
- **Deploy models** for real-time predictions or batch processing.
- **Manage the model lifecycle**, including experiments, evaluation, model versions, and pipelines. [Platform capabilities](https://cloud.google.com/archive/terms/services-20260317)

For example, a customer-churn prediction workflow could look like this:

```text
Cloud Storage → BigQuery → Vertex AI training → Predictions
                    ↑                              ↓
               Prepare data                 Save to BigQuery

Airflow coordinates the steps.
```

In this example:

| Service | Responsibility |
|---|---|
| **Cloud Storage** | Stores raw files and model artifacts |
| **BigQuery** | Prepares and analyzes customer data |
| **Vertex AI** | Trains the model and generates predictions |
| **Airflow** | Schedules the workflow and handles dependencies and retries |

**Vertex AI versus Gemini:** Gemini is a family of AI models. Vertex AI is a platform through which you can access models and build production AI applications.

An interview-ready answer:

> “Vertex AI is Google Cloud’s managed AI and machine learning platform. It provides tools for training, evaluating, deploying, and managing models, as well as accessing foundation models such as Gemini. In a data pipeline, BigQuery prepares the data, Vertex AI performs the machine learning, and Airflow coordinates the workflow.”
