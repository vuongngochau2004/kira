# RAGAS Evaluation Guide

## Overview

K.I.R.A supports RAGAS-style evaluation to measure RAG system quality across multiple dimensions. This guide explains how to use the evaluation features.

## What is RAGAS?

RAGAS (Retrieval Augmented Generation Assessment) is a framework for evaluating RAG systems. It uses LLM-as-a-judge to assess:

- **Faithfulness**: Is the answer grounded in retrieved contexts?
- **Answer Relevancy**: Does the answer address the question?
- **Context Precision**: Are retrieved contexts relevant to the question?
- **Context Recall**: Were important contexts missed?

## Metrics Explained

### Faithfulness (Độ trung thực)

Measures whether the answer is supported by the retrieved contexts.

- **Score**: 0.0 (not grounded) to 1.0 (fully grounded)
- **Vietnamese Prompt**: "Kiểm tra xem câu trả lời có ĐÚNG với ngữ cảnh không?"
- **Use Case**: Detect hallucinations and unsupported claims

**Example:**
```python
# High faithfulness (0.9-1.0)
Query: "Thủ đô Việt Nam là đâu?"
Answer: "Theo ngữ cảnh, Hà Nội là thủ đô của Việt Nam."
Context: ["Hà Nội là thủ đô của Việt Nam."]

# Low faithfulness (0.0-0.3)
Query: "Thủ đô Việt Nam là đâu?"
Answer: "Theo ngữ cảnh, TP. Hồ Chí Minh là thành phố lớn nhất Việt Nam."
Context: ["Hà Nội là thủ đô của Việt Nam."]
```

### Answer Relevancy (Độ liên quan câu trả lời)

Measures whether the answer addresses the original question.

- **Score**: 0.0 (irrelevant) to 1.0 (highly relevant)
- **Vietnamese Prompt**: "Kiểm tra xem câu trả lời có TRẢ LỜI ĐƯỢC câu hỏi không?"
- **Use Case**: Detect off-topic or incomplete answers

**Example:**
```python
# High relevancy (0.9-1.0)
Query: "Điều kiện kết hôn là gì?"
Answer: "Theo Điều 8, điều kiện kết hôn gồm: đủ 18 tuổi, tự nguyện, và có đầy đủ năng lực hành vi."

# Low relevancy (0.0-0.3)
Query: "Điều kiện kết hôn là gì?"
Answer: "Hôn nhân là cơ sở của gia đình." # Too generic, doesn't answer the question
```

### Context Precision (Độ chính xác ngữ cảnh)

Measures relevance of retrieved contexts to the question.

- **Score**: 0.0 (irrelevant) to 1.0 (highly relevant)
- **Vietnamese Prompt**: "Kiểm tra xem các ngữ cảnh có LIÊN QUAN đến câu hỏi không?"
- **Use Case**: Evaluate retrieval quality

**Example:**
```python
# High precision (0.9-1.0)
Query: "Quy định về thời giờ làm việc?"
Contexts: [
    "Điều 105: Thời giờ làm việc hàng ngày không quá 8 giờ.",
    "Điều 106: Quy định về làm thêm giờ."
]

# Low precision (0.0-0.3)
Query: "Quy định về thời giờ làm việc?"
Contexts: [
    "Điều 50: Quy định về ngày nghỉ phép.",
    "Điều 51: Quy định về tiền lương."
] # Irrelevant contexts
```

### Context Recall (Độ bao quát ngữ cảnh)

Measures whether important contexts were retrieved.

- **Score**: 0.0 (missing important info) to 1.0 (complete)
- **Vietnamese Prompt**: "Kiểm tra xem có BỎ LỠ ngữ cảnh quan trọng không?"
- **Use Case**: Identify retrieval gaps
- **Note**: Requires reference contexts for accurate scoring

## Configuration

### Enable Evaluation

Set environment variable:

```bash
export RAGAS_EVALUATION_ENABLED=true
```

Or add to `.env`:

```env
RAGAS_EVALUATION_ENABLED=true
RAGAS_LLM_PROVIDER=glm
RAGAS_TIMEOUT_SECONDS=30
RAGAS_CACHE_ENABLED=true
```

### Configure in settings.yaml

```yaml
ragas_evaluation:
  enabled: true
  metrics:
    - faithfulness
    - answer_relevancy
    - context_precision
    - context_recall
  timeout_seconds: 30
  cache_enabled: true
  cache_ttl_seconds: 3600
  batch_size: 10
```

## Usage

### Real-time Evaluation

Enable evaluation in your chat request:

#### JavaScript/Frontend

```javascript
const response = await fetch('/api/v1/chat/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify({
    message: 'Điều kiện để kết hôn là gì?',
    evaluate: true,
    evaluation_metrics: ['faithfulness', 'answer_relevancy'],
  }),
});

// Handle SSE stream
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));

      if (data.type === 'evaluation') {
        console.log('Evaluation Results:', data.data);
        console.log('Faithfulness:', data.data.results[0].score);
        console.log('Overall Score:', data.data.overall_score);
      }
    }
  }
}
```

#### Python

```python
import httpx
import json
import asyncio

async def stream_with_evaluation():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            'POST',
            'http://localhost:8006/api/v1/chat/stream',
            json={
                'message': 'Điều kiện để kết hôn là gì?',
                'evaluate': True,
                'evaluation_metrics': ['faithfulness', 'answer_relevancy'],
            },
            headers={'Authorization': f'Bearer {token}'}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    if data['type'] == 'evaluation':
                        print(f"Evaluation: {data}")
```

### Batch Evaluation

Evaluate multiple queries at once:

```python
import httpx

response = httpx.post(
    'http://localhost:8006/api/v1/evaluation/evaluate/batch',
    json={
        'queries': [
            {
                'query': 'Điều kiện kết hôn là gì?',
                'answer': 'Theo Điều 8, điều kiện kết hôn gồm: đủ 18 tuổi...',
                'contexts': ['Điều 8. Điều kiện kết hôn...'],
            },
            {
                'query': 'Thời giờ làm việc bao nhiêu?',
                'answer': 'Theo Điều 105, không quá 8 giờ/ngày...',
                'contexts': ['Điều 105. Thời giờ làm việc...'],
            }
        ],
        'metrics': ['faithfulness', 'answer_relevancy', 'context_precision'],
        'concurrent_evaluations': 5,
    },
    headers={'Authorization': f'Bearer {token}'}
)

results = response.json()
print(f"Batch ID: {results['batch_id']}")
print(f"Overall Score: {results['aggregated_scores']['overall']:.2f}")
print(f"Faithfulness: {results['aggregated_scores']['faithfulness']:.2f}")
```

### Golden Datasets

Create validation dataset for continuous testing:

#### Create Dataset

```python
import httpx

dataset = {
    'dataset_id': 'legal-qa-v1',
    'name': 'Vietnamese Legal QA',
    'description': 'Golden dataset for legal Q&A evaluation',
    'samples': [
        {
            'query': 'Điều kiện kết hôn là gì?',
            'answer': 'Theo Điều 8 Luật Hôn nhân và Gia đình 2014...',
            'contexts': ['Điều 8. Điều kiện kết hôn...'],
            'reference_answer': 'Đủ 18 tuổi, tự nguyện, đầy đủ năng lực hành vi.',
            'metadata': {'domain': 'family_law', 'difficulty': 'basic'},
        },
        # ... more samples
    ],
}

response = httpx.post(
    'http://localhost:8006/api/v1/evaluation/datasets',
    json=dataset,
    headers={'Authorization': f'Bearer {token}'}
)

print(f"Dataset created: {response.json()['dataset_id']}")
```

#### List Datasets

```python
response = httpx.get(
    'http://localhost:8006/api/v1/evaluation/datasets',
    headers={'Authorization': f'Bearer {token}'}
)

datasets = response.json()
for dataset in datasets:
    print(f"{dataset['name']}: {len(dataset['samples'])} samples")
```

#### Evaluate Dataset

```python
dataset_id = 'legal-qa-v1'

response = httpx.get(
    f'http://localhost:8006/api/v1/evaluation/datasets/{dataset_id}/evaluate',
    params={'metrics': ['faithfulness', 'answer_relevancy']},
    headers={'Authorization': f'Bearer {token}'}
)

results = response.json()
print(f"Evaluation Results:")
print(f"  Total: {results['total_queries']}")
print(f"  Successful: {results['successful_evaluations']}")
print(f"  Overall Score: {results['aggregated_scores']['overall']:.2f}")
```

## API Reference

### POST /api/v1/evaluation/evaluate

Evaluate a single RAG output.

**Request:**
```json
{
  "query": "User question",
  "answer": "Generated answer",
  "contexts": ["context1", "context2"],
  "metrics": ["faithfulness", "answer_relevancy"]
}
```

**Response:**
```json
{
  "evaluation_id": "uuid",
  "query": "User question",
  "results": [
    {
      "metric": "faithfulness",
      "score": 0.95,
      "reasoning": "Answer is fully supported by contexts"
    }
  ],
  "overall_score": 0.92,
  "evaluated_at": "2026-06-07T00:00:00Z",
  "evaluation_duration_seconds": 2.5,
  "llm_provider": "glm",
  "llm_model": "glm-4.5"
}
```

### POST /api/v1/evaluation/evaluate/batch

Evaluate multiple RAG outputs.

**Request:**
```json
{
  "queries": [
    {"query": "Q1", "answer": "A1", "contexts": ["C1"]},
    {"query": "Q2", "answer": "A2", "contexts": ["C2"]}
  ],
  "metrics": ["faithfulness"],
  "concurrent_evaluations": 10
}
```

**Response:**
```json
{
  "batch_id": "uuid",
  "total_queries": 2,
  "successful_evaluations": 2,
  "failed_evaluations": 0,
  "results": [...],
  "aggregated_scores": {
    "faithfulness": 0.85,
    "overall": 0.85
  },
  "total_duration_seconds": 5.2
}
```

### GET /api/v1/evaluation/datasets

List all golden datasets.

### POST /api/v1/evaluation/datasets

Create a new golden dataset.

### GET /api/v1/evaluation/datasets/{dataset_id}/evaluate

Evaluate a golden dataset.

### DELETE /api/v1/evaluation/cache

Clear evaluation result cache.

## Cost Considerations

### LLM API Costs

Each metric evaluation requires one LLM call:

- **Single Query**: 4 metrics × ~500 tokens = ~2000 tokens
- **100 Queries**: 100 × 4 × 500 = ~200,000 tokens
- **Vietnamese (GLM-4.5)**: ~$0.001-0.002 per 1K tokens
- **Estimated Cost**: ~$0.40-0.80 per 100 queries with all metrics

### Cost Optimization Tips

1. **Use Fewer Metrics**: Evaluate with `faithfulness` + `answer_relevancy` only (50% cost reduction)
2. **Enable Caching**: Repeated evaluations are cached (default 1-hour TTL)
3. **Batch Mode**: Process multiple queries concurrently to reduce overhead
4. **Sample Testing**: Evaluate random sample instead of full dataset

### Example Cost Comparison

```python
# Expensive: All metrics for 1000 queries
queries = 1000
metrics = 4
tokens_per_metric = 500
total_tokens = queries * metrics * tokens_per_metric  # 2,000,000 tokens
cost = total_tokens * 0.0015 / 1000  # ~$3.00

# Optimized: 2 metrics for 100 queries
queries = 100
metrics = 2  # faithfulness + answer_relevancy only
total_tokens = queries * metrics * tokens_per_metric  # 100,000 tokens
cost = total_tokens * 0.0015 / 1000  # ~$0.15 (95% savings!)
```

## Vietnamese Language Support

All evaluation prompts are localized to Vietnamese for better accuracy with Vietnamese content:

- **Faithfulness**: "Kiểm tra xem câu trả lời có ĐÚNG với ngữ cảnh không?"
- **Answer Relevancy**: "Kiểm tra xem câu trả lời có TRẢ LỜI ĐƯỢC câu hỏi không?"
- **Context Precision**: "Kiểm tra xem các ngữ cảnh có LIÊN QUAN đến câu hỏi không?"
- **Context Recall**: "Kiểm tra xem có BỎ LỠ ngữ cảnh quan trọng không?"

The system uses the same GLM provider as the main RAG pipeline for consistency.

## Best Practices

### 1. Start with 2 Metrics

```python
# Good for quick checks
metrics = ['faithfulness', 'answer_relevancy']

# Use all 4 for deep validation
metrics = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall']
```

### 2. Use Golden Datasets

Create domain-specific golden datasets for validation:

```python
legal_dataset = {
    'samples': [
        # Family law samples
        # Labor law samples
        # Contract law samples
    ]
}
```

### 3. Monitor Trends

Track evaluation scores over time to detect degradation:

```python
# Weekly evaluation
week1_scores = evaluate_dataset(legal_dataset)
week2_scores = evaluate_dataset(legal_dataset)

if week2_scores['overall'] < week1_scores['overall'] - 0.05:
    print("WARNING: Quality degradation detected!")
```

### 4. Set Thresholds

Define acceptable score thresholds:

```python
FAITHFULNESS_THRESHOLD = 0.85
RELEVANCY_THRESHOLD = 0.80

if result['faithfulness'] < FAITHFULNESS_THRESHOLD:
    print("WARNING: Low faithfulness score!")
```

## Troubleshooting

### Evaluation Returns 503 Service Unavailable

**Cause**: RAGAS evaluation is disabled.

**Solution**:
```bash
export RAGAS_EVALUATION_ENABLED=true
```

### Evaluation Timeout

**Cause**: LLM request exceeded timeout.

**Solution**: Increase timeout in config:
```yaml
ragas_evaluation:
  timeout_seconds: 60  # Increase from 30
```

### Low Scores on Good Answers

**Cause**: Vietnamese prompt mistranslation or context mismatch.

**Solution**:
- Check if contexts are actually relevant
- Verify answer is grounded in contexts
- Review LLM's reasoning in `reasoning` field

### Cache Not Working

**Cause**: Cache disabled or TTL too short.

**Solution**:
```yaml
ragas_evaluation:
  cache_enabled: true
  cache_ttl_seconds: 7200  # 2 hours
```

## Examples

See example golden dataset at `data/golden_datasets/example_legal_qa.json`.

Run tests:
```bash
# Unit tests
pytest tests/evaluation/test_evaluation_service.py -v

# Integration tests
pytest tests/integration/test_evaluation_api.py -v
```

## References

- [RAGAS Documentation](https://docs.ragas.io/)
- [Plan Document](../../.claude/plans/valiant-jumping-chipmunk.md)
- [Example Dataset](../data/golden_datasets/example_legal_qa.json)
