# AI/ML Glossary for Product Managers

Quick reference for AI/ML terminology.

---

## A

**Accuracy**
Percentage of correct predictions out of total predictions. Be cautious with imbalanced data—99% accuracy might mean the model just predicts the majority class.

**Agent**
An AI system that can perceive its environment, make decisions, and take actions to achieve goals. Often uses tools and multi-step reasoning.

**Alignment**
Ensuring AI systems behave according to human values and intentions. A key safety concern for advanced AI.

**API (Application Programming Interface)**
How your application communicates with an AI model. You send requests, get responses.

---

## B

**Batch Processing**
Running predictions on a collection of data at once, rather than one at a time. Good for non-time-sensitive tasks.

**BERT**
Bidirectional Encoder Representations from Transformers. A foundational model for understanding text, released by Google in 2018.

**Bias (Data)**
Systematic errors in training data that lead to unfair or inaccurate predictions for certain groups.

**Bias (Model)**
The tendency of a model to consistently make certain types of errors.

---

## C

**Classification**
Predicting which category something belongs to (spam/not spam, positive/negative sentiment).

**Completion**
The text an LLM generates in response to a prompt.

**Confidence Score**
A number (usually 0-1) indicating how certain the model is about its prediction.

**Context Window**
The maximum amount of text an LLM can process at once. Measured in tokens.

**Cost Function (Loss Function)**
Mathematical formula that measures how wrong the model's predictions are. Training minimizes this.

---

## D

**Data Drift**
When the distribution of input data changes over time, potentially degrading model performance.

**Dataset**
A collection of examples used to train or evaluate a model.

**Deep Learning**
Machine learning using neural networks with many layers. Powers most modern AI.

**Distillation**
Training a smaller model to mimic a larger one. Used to create efficient models.

---

## E

**Embedding**
A numerical representation (vector) of content (text, images) that captures semantic meaning. Similar things have similar embeddings.

**Epoch**
One complete pass through the training dataset during model training.

**Evaluation (Eval)**
Measuring model performance against defined criteria.

---

## F

**Feature**
An input variable used by a model to make predictions. In ML, feature engineering is critical.

**Feature Store**
A centralized system for storing and serving ML features consistently.

**Fine-tuning**
Additional training of a pre-trained model on a specific dataset for a particular task.

**Foundation Model**
A large model trained on broad data that can be adapted to many tasks (GPT, Claude, Llama).

---

## G

**Generative AI**
AI that creates new content (text, images, code, audio) rather than just classifying or predicting.

**GPT (Generative Pre-trained Transformer)**
OpenAI's family of language models.

**Ground Truth**
The known correct answer used to train and evaluate models.

**Guardrails**
Constraints placed on AI systems to prevent undesirable outputs.

---

## H

**Hallucination**
When an AI model generates false or fabricated information that sounds plausible.

**Hyperparameter**
Settings that control the training process (learning rate, batch size), as opposed to parameters learned from data.

---

## I

**Inference**
Using a trained model to make predictions on new data. As opposed to training.

**In-context Learning**
An LLM's ability to learn from examples provided in the prompt, without changing model weights.

---

## J

**JSON Mode**
Forcing an LLM to output valid JSON format. Useful for structured data extraction.

---

## K

**Knowledge Cutoff**
The date after which an LLM has no training data. It doesn't know about events after this date.

---

## L

**Label**
The correct answer for a training example. Human-provided in supervised learning.

**Latency**
Time from request to response. Critical for user-facing AI features.

**LLM (Large Language Model)**
AI models trained on massive text data that can understand and generate human language.

---

## M

**MLOps**
Practices for deploying and maintaining ML models in production. Like DevOps for ML.

**Model**
A mathematical representation learned from data that can make predictions or generate content.

**Model Card**
Documentation describing a model: its purpose, performance, limitations, and ethical considerations.

**Multimodal**
AI that can process multiple types of input (text, images, audio) and potentially generate multiple types of output.

---

## N

**NLP (Natural Language Processing)**
Field of AI focused on understanding and generating human language.

**Neural Network**
Computing system inspired by biological neural networks. Foundation of deep learning.

---

## O

**Overfitting**
When a model performs well on training data but poorly on new data. It memorized rather than learned.

---

## P

**Parameter**
Values the model learns during training. Large models have billions of parameters.

**Pre-training**
Initial training on large, general datasets before fine-tuning for specific tasks.

**Prompt**
The input text given to an LLM. Prompt engineering is crafting effective prompts.

**Prompt Engineering**
The practice of designing prompts to get desired outputs from LLMs.

**Prompt Injection**
Attempts to manipulate AI behavior through malicious prompts.

---

## Q

**Quantization**
Reducing model precision to make it smaller and faster. Trade-off with accuracy.

---

## R

**RAG (Retrieval-Augmented Generation)**
Combining LLMs with retrieval from a knowledge base to ground responses in real data.

**Recall**
Of all actual positive cases, what percentage did the model find? Important when missing cases is costly.

**Regression**
Predicting a continuous number (price, temperature) rather than a category.

**Reinforcement Learning**
Training by rewarding desired behaviors and penalizing undesired ones.

**RLHF (Reinforcement Learning from Human Feedback)**
Training AI using human preferences to make it more helpful and harmless.

---

## S

**Semantic Search**
Search based on meaning rather than keywords. Uses embeddings.

**Supervised Learning**
Learning from labeled examples. The most common ML approach.

**System Prompt**
Instructions given to an LLM that set context, behavior, and constraints. Users don't typically see it.

---

## T

**Temperature**
Parameter controlling randomness in LLM outputs. Lower = more deterministic, higher = more creative.

**Token**
The unit LLMs process. Roughly ¾ of a word. Pricing and limits are in tokens.

**Training**
The process of teaching a model by showing it examples.

**Transformer**
The neural network architecture behind modern LLMs. Introduced in 2017.

---

## U

**Underfitting**
When a model is too simple to capture patterns in the data.

---

## V

**Validation Set**
Data held out during training to tune hyperparameters and prevent overfitting.

**Vector Database**
Database optimized for storing and searching embeddings. Used for semantic search and RAG.

---

## W

**Weights**
The numerical values in a neural network that are adjusted during training.

---

## Z

**Zero-shot**
Model's ability to perform a task without any examples, based only on instructions.

**Few-shot**
Providing a few examples in the prompt to guide the model's behavior.

