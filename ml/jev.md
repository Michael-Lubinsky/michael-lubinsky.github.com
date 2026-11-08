
<https://jeffyclassify.com/>  

<https://learning.nextia-ai.com/>

 Jeffy can run completely locally, free of charge, without OpenAI, Anthropic, or any other paid API provider.

<https://github.com/nicobrenner/jeffy>

## 1. Local execution and cost

| Question                     | Answer                                     |
| ---------------------------- | ------------------------------------------ |
| Runs fully locally?          | &#x20;Yes                                  |
| Free of charge?              | &#x20;Yes                                  |
| Open source?                 | Yes, MIT license for the code              |
| Requires OpenAI API?         | No                                         |
| Requires Hugging Face API?   | No                                         |
| Requires internet?           | Initially, to install and download models  |
| Runs offline afterward?      | Yes, with models cached locally            |
| Requires GPU?                | No, CPU only                               |
| Supports Apple Silicon Mac?  | Expected to work, but verify compatibility |
| Supports custom classifiers? | Yes, with labeled training data            |

 

One licensing caveat: although Jeffy's code is MIT-licensed, some bundled pretrained classifiers use datasets with academic or noncommercial restrictions. Check the repository's `ATTRIBUTION.md` before commercial deployment.

## 2. How Jeffy works internally

Jeffy does not run a large language model for every classification.

Instead, it uses:

Input text: "I was charged twice for my purchase"

Local embedding model: BGE-large converts text into numeric vectors

Logistic regression classifier: Uses pretrained classification weights

Classification result

```json
{
  "label": "transaction_charged_twice",
  "confidence": 0.999
}
```

The embedding model runs locally, followed by a lightweight classifier.&#x20;
 

## 3. Install on your MacBook

You can install it in a Python virtual environment:

```
python3 -m venv jeffy-env
source jeffy-env/bin/activate

pip install jeffy-classify
jeffy-serve
```

Open:

`http://localhost:8400`

You can also call the local HTTP API:

```
curl -X POST http://localhost:8400/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I was charged twice",
    "task": "banking77"
  }'
```

The first run may download the embedding model (approximately 1.2 GB for the English model). Subsequent inference runs locally using the downloaded files.&#x20;



## 4. Does Jeffy provide a free external service?

Yes. The developer also provides a public playground:

[Jeffy Playground](https://playground.jeffyclassify.com/?utm_source=chatgpt.com)

It currently offers free classification without an API key or registration. However, that sends your text to the developer's server, and the repository describes it as a demonstration service rather than a production API.&#x20;


## 5. Important limitation

Jeffy is not a general-purpose zero-shot classifier.

It ships with pretrained classifiers for particular tasks, including spam detection, sentiment analysis, banking intents, and news categorization.

If you want your own categories, such as:

- Technical support
- Billing
- Sales inquiry
- Product feedback

you generally need to train a classifier using labeled examples.

My recommendation: For local text classification on your Apple Silicon MacBook, Jeffy is worth trying. It avoids recurring API charges and offers a simpler inference architecture than running a general-purpose LLM through Ollama. However, its classification quality will depend on whether its pretrained categories match your task or whether you can provide suitable training examples.
