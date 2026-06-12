"""Generation prompts for the RAG domain."""


def build_generation_prompt(query: str, context: str) -> str:
    """Build prompt for answer generation from retrieved context."""
    return f"""You are a helpful assistant that answers questions based on the provided context. Your goal is to provide accurate, well-structured responses with proper citations.

Context:
{context}

Question: {query}

Instructions:
1. Answer the question using ONLY the provided context
2. If the context doesn't contain enough information, state that clearly
3. Cite the specific document numbers you used (e.g., [Document 1], [Document 2])
4. Provide a clear, structured response
5. If information is conflicting, mention the discrepancy
6. Use Vietnamese language for your response
7. Be concise but comprehensive

Response:"""


def build_regeneration_prompt(
    query: str,
    context: str,
    previous_response: str,
    feedback: str,
) -> str:
    """Build prompt for answer regeneration from quality feedback."""
    return f"""You are improving a previous response based on quality feedback. The original response had some issues that need to be addressed.

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
3. Ensure all citations are accurate
4. Provide a more complete and accurate answer
5. Use Vietnamese language
6. Maintain proper citation format

Improved Response:"""


__all__ = ["build_generation_prompt", "build_regeneration_prompt"]
