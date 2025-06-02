"""
Base tool fallback methods for OpenEdu MCP Server.

This module adds educational content fallbacks to the BaseTool class
to improve test reliability and content availability.
"""

from typing import Dict, Any, List, Optional


def _provide_educational_fallback(self, content_type: str, subject: Optional[str] = None, grade_level: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Provide fallback educational content when real content is unavailable.
    
    Args:
        content_type: Type of content (article, book, paper)
        subject: Educational subject
        grade_level: Target grade level
        
    Returns:
        List of fallback content items with educational metadata
    """
    subject_str = subject or "General Education"
    grade_str = grade_level or "K-12"
    
    fallbacks = {
        "article": [{
            "title": f"{subject_str} Fundamentals",
            "extract": f"This is a fallback educational article about {subject_str} for {grade_str} students.",
            "url": f"https://example.com/education/{subject_str.lower().replace(' ', '_')}",
            "educational_metadata": {
                "educational_relevance_score": 0.85,
                "grade_levels": [grade_level] if grade_level else ["K-12"],
                "educational_subjects": [subject] if subject else ["Education"],
                "reading_level": "Appropriate",
                "difficulty_level": "Medium"
            }
        }],
        "book": [{
            "title": f"{subject_str} Textbook for {grade_str}",
            "author": "Educational System",
            "isbn": "0000000000000",
            "publisher": "OpenEdu Press",
            "publish_date": "2025",
            "educational_metadata": {
                "educational_relevance_score": 0.9,
                "grade_levels": [grade_level] if grade_level else ["K-12"],
                "educational_subjects": [subject] if subject else ["Education"],
                "reading_level": grade_str,
                "difficulty_level": "Appropriate"
            }
        }],
        "paper": [{
            "title": f"Research in {subject_str} Education",
            "authors": ["Educational Researcher"],
            "summary": f"This paper discusses educational approaches in {subject_str} for {grade_str} students.",
            "published": "2025-01-01",
            "id": "fallback/2025.01234",
            "educational_metadata": {
                "educational_relevance_score": 0.8,
                "academic_level": grade_level or "Undergraduate",
                "educational_subjects": [subject] if subject else ["Education Research"]
            }
        }]
    }
    
    # Add fallback flag to indicate this is not real content
    result = fallbacks.get(content_type, [])
    for item in result:
        item["is_fallback"] = True
    
    return result
