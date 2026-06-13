"""Generation prompts for the RAG domain."""


def build_generation_prompt(query: str, context: str) -> str:
    """Build prompt for answer generation from retrieved context."""
    return f"""You are a helpful assistant that answers questions based ONLY on the provided context.

Context:
{context}

Question: {query}

Instructions:
1. Answer using ONLY information from the context above
2. If the context does not contain relevant information for the question, say so clearly
3. Provide a clear, well-structured response
4. If information is conflicting, mention the discrepancy
5. Use Vietnamese language for your response
6. Be concise but comprehensive

Answer:"""


def build_regeneration_prompt(
    query: str,
    context: str,
    previous_response: str,
    feedback: str,
) -> str:
    """Build prompt for answer regeneration from quality feedback."""
    return f"""You are improving a previous response based on quality feedback.

Context:
{context}

Question: {query}

Previous Response:
{previous_response}

Feedback for Improvement:
{feedback}

Instructions:
1. Address the specific issues mentioned in the feedback
2. Improve the quality of the response
3. Provide a more complete and accurate answer
4. Use Vietnamese language

Improved Answer:"""


__all__ = ["build_generation_prompt", "build_regeneration_prompt"]
