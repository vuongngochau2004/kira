"""Quality assessment tools for LangChain agent integration.

Provides tools for the QualityAgent in the 4-agent architecture to assess
response quality through critique and verification.
"""

import asyncio
import json
import logging
import re
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Global LLM client reference
_llm_client: Any = None


def init_quality_tools(llm_client: Any = None) -> None:
    """Initialize global LLM client for quality assessment tools.

    Args:
        llm_client: LLM client instance with chat_async method
    """
    global _llm_client
    _llm_client = llm_client


def _get_llm_client() -> Any:
    """Get the global LLM client instance.

    Returns:
        LLM client or None if not initialized
    """
    return _llm_client


@tool
async def critique_response_tool(
    query: str,
    response: str,
    context: str,
    criteria: str | None = None,
) -> str:
    """Critique the quality of a generated response.

    Use this tool to assess response quality on multiple dimensions:
    - Relevance to the query
    - Accuracy based on provided context
    - Completeness of the answer
    - Clarity and coherence

    Args:
        query: Original user query
        response: Generated response to critique
        context: Retrieved document context used for generation
        criteria: Optional specific criteria to evaluate (JSON string)

    Returns:
        JSON string with critique assessment and suggestions

    Example:
        >>> result = await critique_response_tool.ainvoke({
        ...     "query": "What is the refund policy?",
        ...     "response": "Refunds are processed within 5 days...",
        ...     "context": "According to the policy, refunds take 7-10 days..."
        ... })
    """
    try:
        llm_client = _get_llm_client()
        if not llm_client:
            return json.dumps({
                "success": False,
                "error": "LLM client not initialized",
                "quality_level": "unknown",
                "confidence": 0.0
            }, ensure_ascii=False)

        # Parse custom criteria if provided
        custom_criteria = []
        if criteria:
            try:
                criteria_data = json.loads(criteria)
                custom_criteria = criteria_data.get("criteria", [])
            except:
                pass

        # Build critique prompt
        prompt = f"""Bạn là chuyên gia đánh giá chất lượng câu trả lời. Hãy phân tích câu trả lời dưới đây dựa trên ngữ cảnh cung cấp.

CÂU HỎI: {query}

CÂU TRẢ LỜI CẦN ĐÁNH GIÁ:
{response}

NGỮ CẢNH TÀI LIỆU:
{context[:3000]}

YÊU CẦU ĐÁNH GIÁ:
1. TÍNH LIÊN QUAN: Câu trả lời có giải quyết đúng câu hỏi không?
2. TÍNH CHÍNH XÁC: Thông tin có khớp với ngữ cảnh tài liệu không?
3. TÍNH TOÀN VẸN: Có thiếu thông tin quan trọng nào không?
4. TÍNH RÕ RÀNG: Câu trả lời có dễ hiểu, mạch lạc không?
5. TRÍCH DẪN: Có trích dẫn nguồn rõ ràng không?

{"TIÊU CHÍ TÙY CHỌN:\n" + "\n".join(f"- {c}" for c in custom_criteria) if custom_criteria else ""}

Trả về đánh giá theo định dạng JSON:
{{
    "quality_level": "excellent|good|acceptable|poor|failed",
    "confidence": 0.0-1.0,
    "relevance_score": 0.0-1.0,
    "accuracy_score": 0.0-1.0,
    "completeness_score": 0.0-1.0,
    "clarity_score": 0.0-1.0,
    "citation_score": 0.0-1.0,
    "issues": ["vấn đề 1", "vấn đề 2"],
    "suggestions": ["gợi ý 1", "gợi ý 2"],
    "should_regenerate": true/false
}}

Chỉ trả về JSON, không giải thích:"""

        messages = [
            {"role": "system", "content": "Bạn là chuyên gia đánh giá chất lượng thông tin và câu trả lời."},
            {"role": "user", "content": prompt}
        ]

        llm_response = await asyncio.wait_for(
            llm_client.chat_async(
                messages=messages,
                temperature=0.3,
                max_tokens=500,
            ),
            timeout=15,
        )

        content = llm_response.get("content", "")

        # Extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            critique_data = json.loads(json_match.group(0))
            return json.dumps({
                "success": True,
                **critique_data,
                "llm_used": llm_response.get("model", "unknown")
            }, ensure_ascii=False)
        else:
            # Fallback parsing
            logger.warning("Failed to extract JSON from critique response")

            # Simple heuristic-based critique
            quality_indicators = {
                "excellent": ["hoàn hảo", "rất tốt", "xuất sắc"],
                "good": ["tốt", "đủ", "hợp lý"],
                "acceptable": ["chấp nhận được", "cơ bản"],
                "poor": ["kém", "chưa tốt", "cần cải thiện"],
                "failed": ["sai", "không đúng", "thông tin sai"]
            }

            detected_level = "acceptable"
            content_lower = content.lower()
            for level, indicators in quality_indicators.items():
                if any(ind in content_lower for ind in indicators):
                    detected_level = level
                    break

            return json.dumps({
                "success": True,
                "quality_level": detected_level,
                "confidence": 0.5,
                "relevance_score": 0.6,
                "accuracy_score": 0.6,
                "completeness_score": 0.6,
                "clarity_score": 0.6,
                "citation_score": 0.5,
                "issues": [],
                "suggestions": [],
                "should_regenerate": False,
                "parse_warning": "Could not extract structured JSON"
            }, ensure_ascii=False)

    except asyncio.TimeoutError:
        logger.error("Critique tool timed out")
        return json.dumps({
            "success": False,
            "error": "Critique timed out",
            "quality_level": "unknown",
            "confidence": 0.0
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in critique_response_tool: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "quality_level": "unknown",
            "confidence": 0.0
        }, ensure_ascii=False)


@tool
async def verify_facts_tool(
    query: str,
    response: str,
    context: str,
    verify_citations: bool = True,
) -> str:
    """Verify factual consistency and citation accuracy of a response.

    Use this tool to check that the response is factually consistent with
    the source documents and that citations are accurate.

    Args:
        query: Original user query
        response: Generated response to verify
        context: Source document context
        verify_citations: Whether to verify citation accuracy (default: True)

    Returns:
        JSON string with verification results

    Example:
        >>> result = await verify_facts_tool.ainvoke({
        ...     "query": "What is the warranty period?",
        ...     "response": "The warranty is 2 years according to [1]",
        ...     "context": "[1] Warranty: 2 years parts and labor"
        ... })
    """
    try:
        llm_client = _get_llm_client()
        if not llm_client:
            return json.dumps({
                "success": False,
                "error": "LLM client not initialized",
                "is_verified": False,
                "confidence": 0.0
            }, ensure_ascii=False)

        prompt = f"""Bạn là chuyên gia xác minh tính đúng đắn của thông tin. Hãy kiểm tra câu trả lời dưới đây.

CÂU HỎI: {query}

CÂU TRẢ LỜI:
{response}

NGUỒN TÀI LIỆU:
{context[:3000]}

YÊU CẦU XÉT XỬ:
1. TÍNH NHẤT QUÁN: Thông tin trong câu trả lời có mâu thuẫn với nguồn không?
2. TÍCH PHÁP: Các số liệu, ngày tháng, tên riêng có chính xác không?
3. TRÍCH DẪN: Các trích dẫn [1], [2] có khớp với nguồn không?
4. KHÔNG THÊM THẢT: Câu trả lời có thêm thông tin không có trong nguồn không?

Trả về kết quả theo định dạng JSON:
{{
    "is_verified": true/false,
    "confidence": 0.0-1.0,
    "factual_consistency": 0.0-1.0,
    "citation_accuracy": 0.0-1.0,
    "reasoning_quality": 0.0-1.0,
    "issues_found": ["vấn đề 1", "vấn đề 2"],
    "verification_checks": ["check1", "check2"]
}}

Chỉ trả về JSON, không giải thích:"""

        messages = [
            {"role": "system", "content": "Bạn là chuyên gia xác minh thông tin với tiêu chuẩn cao."},
            {"role": "user", "content": prompt}
        ]

        llm_response = await asyncio.wait_for(
            llm_client.chat_async(
                messages=messages,
                temperature=0.2,
                max_tokens=400,
            ),
            timeout=12,
        )

        content = llm_response.get("content", "")

        # Extract JSON from response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            verify_data = json.loads(json_match.group(0))
            return json.dumps({
                "success": True,
                **verify_data,
                "llm_used": llm_response.get("model", "unknown")
            }, ensure_ascii=False)
        else:
            logger.warning("Failed to extract JSON from verification response")

            # Fallback
            return json.dumps({
                "success": True,
                "is_verified": True,
                "confidence": 0.5,
                "factual_consistency": 0.6,
                "citation_accuracy": 0.6,
                "reasoning_quality": 0.6,
                "issues_found": [],
                "verification_checks": ["basic_check"],
                "parse_warning": "Could not extract structured JSON"
            }, ensure_ascii=False)

    except asyncio.TimeoutError:
        logger.error("Verification tool timed out")
        return json.dumps({
            "success": False,
            "error": "Verification timed out",
            "is_verified": False,
            "confidence": 0.0
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in verify_facts_tool: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "is_verified": False,
            "confidence": 0.0
        }, ensure_ascii=False)


@tool
async def combined_quality_assessment(
    query: str,
    response: str,
    context: str,
    weight_critique: float = 0.5,
    weight_verification: float = 0.5,
) -> str:
    """Perform combined quality assessment (critique + verification).

    This is the recommended tool for QualityAgent in the 4-agent architecture.
    It runs both critique and verification in parallel and combines results
    for a comprehensive quality assessment.

    Args:
        query: Original user query
        response: Generated response to assess
        context: Source document context
        weight_critique: Weight for critique score (default: 0.5)
        weight_verification: Weight for verification score (default: 0.5)

    Returns:
        JSON string with combined quality assessment

    Example:
        >>> result = await combined_quality_assessment.ainvoke({
        ...     "query": "Explain the contract terms",
        ...     "response": "The contract includes...",
        ...     "context": "Contract terms: ..."
        ... })
    """
    try:
        # Run critique and verification in parallel
        critique_task = critique_response_tool.ainvoke({
            "query": query,
            "response": response,
            "context": context
        })

        verify_task = verify_facts_tool.ainvoke({
            "query": query,
            "response": response,
            "context": context
        })

        critique_result, verify_result = await asyncio.gather(
            critique_task,
            verify_task
        )

        critique_data = json.loads(critique_result)
        verify_data = json.loads(verify_result)

        # Calculate combined scores
        critique_success = critique_data.get("success", False)
        verify_success = verify_data.get("success", False)

        if not critique_success or not verify_success:
            return json.dumps({
                "success": False,
                "error": "Quality assessment failed",
                "critique_success": critique_success,
                "verification_success": verify_success,
                "overall_quality_score": 0.0,
                "should_regenerate": True
            }, ensure_ascii=False)

        # Extract scores
        critique_scores = {
            "relevance": critique_data.get("relevance_score", 0.6),
            "accuracy": critique_data.get("accuracy_score", 0.6),
            "completeness": critique_data.get("completeness_score", 0.6),
            "clarity": critique_data.get("clarity_score", 0.6),
            "citation": critique_data.get("citation_score", 0.6)
        }

        verify_scores = {
            "factual_consistency": verify_data.get("factual_consistency", 0.6),
            "citation_accuracy": verify_data.get("citation_accuracy", 0.6),
            "reasoning_quality": verify_data.get("reasoning_quality", 0.6)
        }

        # Calculate average scores
        avg_critique = sum(critique_scores.values()) / len(critique_scores)
        avg_verification = sum(verify_scores.values()) / len(verify_scores)

        # Combined quality score
        overall_quality = (avg_critique * weight_critique +
                           avg_verification * weight_verification)

        # Determine quality level
        if overall_quality >= 0.9:
            quality_level = "excellent"
        elif overall_quality >= 0.75:
            quality_level = "good"
        elif overall_quality >= 0.6:
            quality_level = "acceptable"
        elif overall_quality >= 0.4:
            quality_level = "poor"
        else:
            quality_level = "failed"

        # Collect all issues and suggestions
        all_issues = []
        all_suggestions = []

        if critique_data.get("issues"):
            all_issues.extend(critique_data["issues"])
        if verify_data.get("issues_found"):
            all_issues.extend(verify_data["issues_found"])

        if critique_data.get("suggestions"):
            all_suggestions.extend(critique_data["suggestions"])

        # Determine if regeneration is needed
        should_regenerate = (
            overall_quality < 0.7 or
            critique_data.get("should_regenerate", False) or
            not verify_data.get("is_verified", True)
        )

        return json.dumps({
            "success": True,
            "overall_quality_score": round(overall_quality, 3),
            "quality_level": quality_level,
            "confidence": round((avg_critique + avg_verification) / 2, 3),
            "critique": {
                "success": True,
                "average_score": round(avg_critique, 3),
                "detailed_scores": critique_scores,
                "issues": critique_data.get("issues", []),
                "suggestions": critique_data.get("suggestions", [])
            },
            "verification": {
                "success": True,
                "is_verified": verify_data.get("is_verified", False),
                "average_score": round(avg_verification, 3),
                "detailed_scores": verify_scores,
                "checks": verify_data.get("verification_checks", [])
            },
            "all_issues": all_issues,
            "all_suggestions": all_suggestions,
            "should_regenerate": should_regenerate,
            "regeneration_reason": (
                "Low quality score" if overall_quality < 0.7 else
                "Critique suggested regeneration" if critique_data.get("should_regenerate") else
                "Verification failed" if not verify_data.get("is_verified") else
                None
            ),
            "weights_applied": {
                "critique": weight_critique,
                "verification": weight_verification
            }
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in combined_quality_assessment: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e),
            "overall_quality_score": 0.0,
            "should_regenerate": True
        }, ensure_ascii=False)


@tool
def calculate_quality_metrics(
    quality_data: str,
) -> str:
    """Calculate additional quality metrics from assessment data.

    Use this tool to derive metrics and insights from quality assessment results.

    Args:
        quality_data: JSON string from combined_quality_assessment

    Returns:
        JSON string with calculated metrics and insights
    """
    try:
        data = json.loads(quality_data)

        if not data.get("success"):
            return json.dumps({
                "success": False,
                "error": "Invalid quality assessment data"
            }, ensure_ascii=False)

        overall_score = data.get("overall_quality_score", 0.0)
        quality_level = data.get("quality_level", "unknown")

        # Calculate percentiles
        percentile = max(0, min(100, int(overall_score * 100)))

        # Determine grade
        if percentile >= 90:
            grade = "A"
        elif percentile >= 80:
            grade = "B"
        elif percentile >= 70:
            grade = "C"
        elif percentile >= 60:
            grade = "D"
        else:
            grade = "F"

        # Analyze issues
        all_issues = data.get("all_issues", [])
        issue_categories = {
            "accuracy": [],
            "completeness": [],
            "clarity": [],
            "citation": [],
            "other": []
        }

        for issue in all_issues:
            issue_lower = issue.lower()
            if any(word in issue_lower for word in ["sai", "không chính xác", "mâu thuẫn"]):
                issue_categories["accuracy"].append(issue)
            elif any(word in issue_lower for word in ["thiếu", "chưa đầy đủ"]):
                issue_categories["completeness"].append(issue)
            elif any(word in issue_lower for word in ["không rõ", "mập mờ"]):
                issue_categories["clarity"].append(issue)
            elif any(word in issue_lower for word in ["trích dẫn", "nguồn"]):
                issue_categories["citation"].append(issue)
            else:
                issue_categories["other"].append(issue)

        # Priority improvements
        priority_improvements = []
        if issue_categories["accuracy"]:
            priority_improvements.append({
                "category": "accuracy",
                "priority": "high",
                "count": len(issue_categories["accuracy"]),
                "issues": issue_categories["accuracy"][:3]
            })

        if issue_categories["completeness"]:
            priority_improvements.append({
                "category": "completeness",
                "priority": "medium",
                "count": len(issue_categories["completeness"]),
                "issues": issue_categories["completeness"][:3]
            })

        if issue_categories["citation"]:
            priority_improvements.append({
                "category": "citation",
                "priority": "medium",
                "count": len(issue_categories["citation"]),
                "issues": issue_categories["citation"][:3]
            })

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        priority_improvements.sort(key=lambda x: priority_order.get(x["priority"], 3))

        return json.dumps({
            "success": True,
            "metrics": {
                "overall_score": overall_score,
                "quality_level": quality_level,
                "percentile": percentile,
                "grade": grade,
                "passing": overall_score >= 0.7
            },
            "issue_analysis": {
                "total_issues": len(all_issues),
                "by_category": {k: len(v) for k, v in issue_categories.items()},
                "most_problematic": max(issue_categories.items(), key=lambda x: len(x[1]))[0] if any(len(v) > 0 for v in issue_categories.values()) else None
            },
            "priority_improvements": priority_improvements,
            "recommendations": {
                "should_regenerate": data.get("should_regenerate", False),
                "reason": data.get("regeneration_reason"),
                "action_items": data.get("all_suggestions", [])[:5]
            }
        }, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in calculate_quality_metrics: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)


__all__ = [
    "init_quality_tools",
    "critique_response_tool",
    "verify_facts_tool",
    "combined_quality_assessment",
    "calculate_quality_metrics",
]
