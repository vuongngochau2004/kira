# RAG Evaluation Guide for K.I.R.A

## Overview

This guide explains how to evaluate the quality of your RAG system using multiple metrics and evaluation frameworks.

## Evaluation Frameworks

### 1. RAGAS (Recommended)

**Installation:**
```bash
pip install ragas
```

**Basic Usage:**
```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_relevancy,
    context_precision
)

def evaluate_rag_output(question, answer, contexts, ground_truth=None):
    """
    Evaluate RAG output using RAGAS metrics.

    Args:
        question: User question
        answer: Generated answer from RAG
        contexts: List of retrieved contexts
        ground_truth: Optional ground truth answer

    Returns:
        Dictionary with metric scores
    """
    from datasets import Dataset

    # Prepare evaluation dataset
    data = {
        "question": [question],
        "answer": [answer],
        "contexts": [contexts],
    }

    if ground_truth:
        data["ground_truth"] = [ground_truth]

    dataset = Dataset.from_dict(data)

    # Run evaluation
    results = evaluate(
        dataset=dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_relevancy,
            context_precision
        ]
    )

    return results.to_pandas()
```

### 2. TruLens

**Installation:**
```bash
pip install trulens-eval
```

**Usage:**
```python
from trulens_eval import TruChain, Feedback
from trulens_eval.feedback.provider import OpenAI

# Initialize feedback provider
provider = OpenAI()

# Define feedback functions
from trulens_eval.feedback import Groundedness

grounded = Groundedness(groundedness_provider=provider)

# Wrap your RAG chain
tru_recorder = TruChain(rag_chain, app_id="RAG_Application")

# Run evaluation
with tru_recorder as recording:
    result = rag_chain.invoke("Your question here")

# Get results
tru.run_dashboard()
```

### 3. DeepEval

**Installation:**
```bash
pip install deepeval
```

**Usage:**
```python
from deepeval import evaluate
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualPrecisionMetric
)
from deepeval.test_case import LLMTestCase

# Create test case
test_case = LLMTestCase(
    input="What is the capital of France?",
    actual_output="The capital of France is Paris.",
    retrieval_context=["Paris is the capital city of France..."],
    expected_output="Paris"
)

# Define metrics
faithfulness = FaithfulnessMetric(threshold=0.5)
relevancy = AnswerRelevancyMetric(threshold=0.5)
context_precision = ContextualPrecisionMetric(threshold=0.5)

# Run evaluation
result = evaluate(
    test_cases=[test_case],
    metrics=[faithfulness, relevancy, context_precision]
)
```

## Custom Evaluation Implementation

### LLM-based Faithfulness Evaluator

```python
import os
from typing import List, Dict
from src.agents.llm import LLMClient

class RAGEvaluator:
    """Custom RAG evaluator using LLM-as-a-judge"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def evaluate_faithfulness(
        self,
        answer: str,
        contexts: List[str],
        question: str
    ) -> Dict[str, any]:
        """
        Evaluate if the answer is grounded in the retrieved contexts.

        Returns:
            Dict with:
            - score: 0-1 faithfulness score
            - reasoning: Explanation of the score
            - unsupported_statements: List of statements not in context
        """
        prompt = f"""You are an expert evaluator. Your task is to evaluate the faithfulness of an answer given retrieved contexts.

Question: {question}

Retrieved Contexts:
{" ".join([f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts)])}

Answer to Evaluate: {answer}

Instructions:
1. Break down the answer into individual statements/facts
2. For each statement, verify if it is supported by the retrieved contexts
3. Identify any statements that are not supported (hallucinations)
4. Calculate faithfulness score: (supported_statements / total_statements)

Provide your evaluation in the following JSON format:
{{
    "statements": [
        {{"text": "statement text", "supported": true, "evidence": "source context"}}
    ],
    "unsupported_statements": ["statement 1", "statement 2"],
    "faithfulness_score": 0.0-1.0,
    "reasoning": "Brief explanation of the evaluation"
}}
"""

        response = await self.llm.ainvoke(prompt)
        return self._parse_evaluation(response)

    def evaluate_answer_relevance(
        self,
        question: str,
        answer: str
    ) -> Dict[str, any]:
        """
        Evaluate if the answer actually addresses the question.

        Returns:
            Dict with relevance score and reasoning
        """
        prompt = f"""You are an expert evaluator. Evaluate if the answer actually addresses the question.

Question: {question}
Answer: {answer}

Consider:
- Does the answer directly address the question asked?
- Is the answer complete or does it miss important aspects?
- Is the answer specific to the question or too generic?

Rate the relevance from 0-1 and provide reasoning.

Output JSON:
{{
    "relevance_score": 0.0-1.0,
    "reasoning": "explanation",
    "missing_aspects": ["aspect 1", "aspect 2"]
}}
"""

        response = await self.llm.ainvoke(prompt)
        return self._parse_evaluation(response)

    def evaluate_context_relevance(
        self,
        question: str,
        contexts: List[str]
    ) -> Dict[str, any]:
        """
        Evaluate if retrieved contexts are relevant to the question.

        Returns:
            Dict with context precision and relevance scores
        """
        prompt = f"""You are an expert evaluator. Evaluate the relevance of retrieved contexts to the question.

Question: {question}

Retrieved Contexts:
{" ".join([f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts)])}

For each context, rate its relevance to the question (0-1) and explain why.

Output JSON:
{{
    "context_evaluations": [
        {{"index": 1, "relevance": 0.8, "reasoning": "..."}},
        ...
    ],
    "context_precision": 0.0-1.0,
    "average_relevance": 0.0-1.0
}}
"""

        response = await self.llm.ainvoke(prompt)
        return self._parse_evaluation(response)

    def _parse_evaluation(self, response: str) -> Dict:
        """Parse JSON response from LLM"""
        import json
        try:
            # Extract JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            return json.loads(json_str)
        except:
            return {"error": "Failed to parse evaluation", "raw_response": response}
```

## Integration with K.I.R.A

### 1. Add Evaluation Endpoint

Add to `src/api/chat.py`:

```python
@router.post("/evaluate")
async def evaluate_rag_response(
    request: EvaluationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Evaluate a RAG response using multiple metrics.
    This endpoint is primarily for testing and monitoring.
    """
    evaluator = RAGEvaluator(llm_client=llm)

    # Run all evaluations
    faithfulness = await evaluator.evaluate_faithfulness(
        answer=request.answer,
        contexts=request.contexts,
        question=request.question
    )

    relevance = await evaluator.evaluate_answer_relevance(
        question=request.question,
        answer=request.answer
    )

    context_rel = await evaluator.evaluate_context_relevance(
        question=request.question,
        contexts=request.contexts
    )

    return {
        "faithfulness": faithfulness,
        "answer_relevance": relevance,
        "context_relevance": context_rel,
        "overall_score": (
            faithfulness.get("faithfulness_score", 0) * 0.4 +
            relevance.get("relevance_score", 0) * 0.3 +
            context_rel.get("context_precision", 0) * 0.3
        )
    }
```

### 2. Add Evaluation to Response Metadata

Update `src/agents/routers/rag_router.py` to include evaluation metrics:

```python
# In RAGRouter.handle_stream()
async def handle_stream(self, query: str, user_id: str):
    # ... existing code ...

    # After generating response
    evaluation = await self.evaluate_response(
        question=query,
        answer=final_answer,
        contexts=retrieved_docs
    )

    # Include in metadata
    yield {
        "type": "metadata",
        "data": {
            "status": "success",
            "citations": citations,
            "conversation_id": conv_id,
            "evaluation": evaluation  # Add evaluation scores
        }
    }
```

## Best Practices

### 1. Build Evaluation Dataset

Create a golden dataset with:
- Questions representative of real user queries
- Ground truth answers (from human experts)
- Expected relevant documents

```python
# tests/evaluation_data.yaml
test_cases:
  - question: "Cách tạo conversation mới trong hệ thống?"
    expected_answer: "Bạn có thể tạo conversation mới qua API POST /api/v1/conversations hoặc sử dụng frontend UI."
    relevant_docs: ["api.md", "conversation_management.md"]

  - question: "Hệ thống RAG hoạt động như thế nào?"
    expected_answer: "RAG system sử dụng hybrid retrieval (dense + BM25) với RRF fusion..."
    relevant_docs: ["architecture.md", "retrieval.md"]
```

### 2. Continuous Monitoring

Set up automated evaluation:
- Run evaluation daily on sample queries
- Track metrics over time
- Alert when metrics drop below threshold

### 3. A/B Testing

Compare different RAG configurations:
- Different chunking strategies
- Different embedding models
- Different retrieval parameters (k, rrf_k)

## Metrics Thresholds

Recommended thresholds for production:

| Metric | Good | Acceptable | Needs Improvement |
|--------|------|------------|------------------|
| Faithfulness | > 0.9 | 0.7-0.9 | < 0.7 |
| Answer Relevance | > 0.85 | 0.7-0.85 | < 0.7 |
| Context Precision | > 0.8 | 0.6-0.8 | < 0.6 |
| Context Recall | > 0.75 | 0.5-0.75 | < 0.5 |

## Tools Comparison

| Feature | RAGAS | TruLens | DeepEval |
|---------|-------|---------|----------|
| Ease of Use | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Metrics | 10+ | 6 | 15+ |
| Customization | Medium | High | High |
| Documentation | Good | Good | Excellent |
| Integration | Easy | Medium | Easy |

**Recommendation**: Start with **RAGAS** for simplicity, then consider **DeepEval** for more advanced metrics.

## References

- [RAGAS Documentation](https://docs.ragas.io/)
- [TruLens Documentation](https://www.trulens.org/)
- [DeepEval Documentation](https://docs.confident-ai.com/)
- [RAG Evaluation Best Practices](https://arxiv.org/abs/2309.15217)
