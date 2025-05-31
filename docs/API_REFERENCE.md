# API Reference Guide

This document provides comprehensive documentation for all MCP tools available in the OpenEdu MCP Server.

## 📋 Overview

The OpenEdu MCP Server provides **20+ MCP tools** across four integrated APIs:
- **Open Library Tools** (4 tools): Educational book search and recommendations
- **Wikipedia Tools** (5 tools): Educational article analysis and content filtering
- **Dictionary Tools** (5 tools): Vocabulary analysis and language support
- **arXiv Tools** (5 tools): Academic paper search and educational research
- **Server Tools** (1 tool): Server status and monitoring

All tools support educational filtering, grade-level appropriateness, and curriculum alignment.

## 📚 Open Library Tools

### `search_educational_books`

Search for educational books with grade-level and subject filtering.

**Parameters:**
- `query` (string, required): Search query for books
- `subject` (string, optional): Educational subject filter
- `grade_level` (string, optional): Target grade level (K-2, 3-5, 6-8, 9-12, College)
- `limit` (integer, optional): Maximum number of results (1-50, default: 10)

**Returns:**
List of educational books with metadata

**Example Request:**
```python
await search_educational_books(
    query="mathematics",
    subject="Mathematics",
    grade_level="6-8",
    limit=5
)
```

**Example Response:**
```json
[
    {
        "title": "Algebra Basics for Middle School",
        "author": "Jane Smith",
        "isbn": "9781234567890",
        "grade_level": "6-8",
        "subject": "Mathematics",
        "educational_value": 0.92,
        "reading_level": "Grade 7",
        "curriculum_alignment": ["Common Core"],
        "description": "Introduction to algebraic concepts for middle school students",
        "cover_url": "https://covers.openlibrary.org/b/isbn/9781234567890-L.jpg",
        "publication_year": 2023,
        "page_count": 240,
        "complexity_score": 0.6,
        "learning_objectives": [
            "Understand variables and expressions",
            "Solve linear equations",
            "Graph linear relationships"
        ]
    }
]
```

**Error Handling:**
- `OpenEduMCPError`: Invalid parameters or API failure
- Empty query returns error
- Invalid grade level returns error

---

### `get_book_details_by_isbn`

Get detailed book information by ISBN with educational metadata.

**Parameters:**
- `isbn` (string, required): ISBN-10 or ISBN-13
- `include_cover` (boolean, optional): Whether to include cover image URL (default: true)

**Returns:**
Detailed book information with educational metadata

**Example Request:**
```python
await get_book_details_by_isbn(
    isbn="9780134685991",
    include_cover=True
)
```

**Example Response:**
```json
{
    "title": "Calculus: Early Transcendentals",
    "authors": ["James Stewart", "Daniel Clegg"],
    "isbn_13": "9780134685991",
    "isbn_10": "0134685997",
    "publisher": "Pearson",
    "publication_date": "2020-01-01",
    "page_count": 1368,
    "language": "en",
    "grade_level": "College",
    "subject": "Mathematics",
    "educational_value": 0.98,
    "complexity_score": 0.95,
    "textbook": true,
    "cover_url": "https://covers.openlibrary.org/b/isbn/9780134685991-L.jpg",
    "description": "Comprehensive calculus textbook for undergraduate students",
    "table_of_contents": [
        "Functions and Models",
        "Limits and Derivatives",
        "Differentiation Rules"
    ],
    "prerequisites": ["Pre-calculus", "Trigonometry"],
    "learning_outcomes": [
        "Master differential calculus",
        "Understand integral calculus",
        "Apply calculus to real-world problems"
    ]
}
```

---

### `search_books_by_subject`

Search books by educational subject with curriculum alignment.

**Parameters:**
- `subject` (string, required): Educational subject
- `grade_level` (string, optional): Target grade level
- `limit` (integer, optional): Maximum number of results (1-50, default: 10)

**Returns:**
List of books in the subject area

**Example Request:**
```python
await search_books_by_subject(
    subject="Science",
    grade_level="3-5",
    limit=3
)
```

**Example Response:**
```json
[
    {
        "title": "National Geographic Kids Everything Space",
        "author": "Nadia Higgins",
        "grade_level": "3-5",
        "subject": "Science",
        "educational_value": 0.88,
        "curriculum_alignment": ["NGSS"],
        "topics": ["solar system", "planets", "space exploration"],
        "reading_level": "Grade 4",
        "complexity_score": 0.4
    }
]
```

---

### `get_book_recommendations`

Get curated book recommendations for specific grade levels and subjects.

**Parameters:**
- `grade_level` (string, required): Target grade level (K-2, 3-5, 6-8, 9-12, College)
- `subject` (string, optional): Educational subject
- `limit` (integer, optional): Maximum number of results (1-50, default: 10)

**Returns:**
List of recommended books

**Example Request:**
```python
await get_book_recommendations(
    grade_level="9-12",
    subject="Physics",
    limit=3
)
```

**Example Response:**
```json
[
    {
        "title": "Physics: Principles and Problems",
        "author": "McGraw-Hill Education",
        "grade_level": "9-12",
        "subject": "Physics",
        "educational_value": 0.94,
        "recommendation_score": 0.96,
        "curriculum_alignment": ["AP Physics"],
        "difficulty_level": "Advanced",
        "college_prep": true
    }
]
```

## 🌐 Wikipedia Tools

### `search_educational_articles`

Search Wikipedia articles with educational filtering and analysis.

**Parameters:**
- `query` (string, required): Search query for articles
- `subject` (string, optional): Educational subject filter
- `grade_level` (string, optional): Target grade level
- `language` (string, optional): Language code (default: 'en')
- `limit` (integer, optional): Maximum number of results (1-50, default: 10)

**Returns:**
List of educational articles with summaries

**Example Request:**
```python
await search_educational_articles(
    query="photosynthesis",
    grade_level="3-5",
    subject="Science",
    limit=3
)
```

**Example Response:**
```json
[
    {
        "title": "Photosynthesis",
        "url": "https://en.wikipedia.org/wiki/Photosynthesis",
        "summary": "Photosynthesis is the process by which plants make their own food using sunlight, water, and carbon dioxide.",
        "grade_level": "3-5",
        "subject": "Science",
        "educational_value": 0.91,
        "complexity_score": 0.4,
        "key_concepts": ["plants", "sunlight", "oxygen", "carbon dioxide"],
        "curriculum_alignment": ["NGSS 5-LS1-1"],
        "reading_level": "Grade 4",
        "word_count": 450,
        "estimated_reading_time": "3 minutes"
    }
]
```

---

### `get_article_summary`

Get article summaries with educational metadata and complexity analysis.

**Parameters:**
- `title` (string, required): Article title
- `language` (string, optional): Language code (default: 'en')
- `include_educational_analysis` (boolean, optional): Whether to include educational metadata (default: true)

**Returns:**
Article summary with educational metadata

**Example Request:**
```python
await get_article_summary(
    title="Solar System",
    include_educational_analysis=True
)
```

**Example Response:**
```json
{
    "title": "Solar System",
    "url": "https://en.wikipedia.org/wiki/Solar_System",
    "summary": "The Solar System is the gravitationally bound system of the Sun and the objects that orbit it.",
    "educational_analysis": {
        "grade_level": "6-8",
        "complexity_score": 0.6,
        "reading_level": "Grade 7",
        "key_concepts": ["planets", "orbit", "gravity", "astronomy"],
        "prerequisite_knowledge": ["basic astronomy", "gravity concepts"],
        "learning_objectives": [
            "Understand solar system structure",
            "Identify planets and their characteristics",
            "Explain orbital mechanics"
        ]
    },
    "word_count": 850,
    "estimated_reading_time": "5 minutes",
    "last_modified": "2024-01-15T10:30:00Z"
}
```

---

### `get_article_content`

Get full article content with educational enrichment.

**Parameters:**
- `title` (string, required): Article title
- `language` (string, optional): Language code (default: 'en')
- `include_images` (boolean, optional): Whether to include article images (default: false)

**Returns:**
Full article content with educational metadata

**Example Request:**
```python
await get_article_content(
    title="Photosynthesis",
    include_images=True
)
```

**Example Response:**
```json
{
    "title": "Photosynthesis",
    "content": "Photosynthesis is a process used by plants and other organisms...",
    "sections": [
        {
            "title": "Overview",
            "content": "...",
            "grade_level": "6-8"
        },
        {
            "title": "Light-dependent reactions",
            "content": "...",
            "grade_level": "9-12"
        }
    ],
    "images": [
        {
            "url": "https://upload.wikimedia.org/wikipedia/commons/...",
            "caption": "Diagram of photosynthesis process",
            "educational_value": 0.9
        }
    ],
    "educational_metadata": {
        "overall_grade_level": "6-8",
        "complexity_distribution": {
            "elementary": 0.2,
            "middle_school": 0.5,
            "high_school": 0.3
        }
    }
}
```

---

### `get_featured_article`

Get Wikipedia's featured article with educational analysis.

**Parameters:**
- `date` (string, optional): Date in YYYY/MM/DD format (defaults to today)
- `language` (string, optional): Language code (default: 'en')

**Returns:**
Featured article with educational metadata

**Example Request:**
```python
await get_featured_article(
    date="2024/01/15",
    language="en"
)
```

---

### `get_articles_by_subject`

Get articles by educational subject with grade-level filtering.

**Parameters:**
- `subject` (string, required): Educational subject
- `grade_level` (string, optional): Target grade level
- `language` (string, optional): Language code (default: 'en')
- `limit` (integer, optional): Maximum number of results (default: 10)

**Returns:**
List of articles in the subject area

**Example Request:**
```python
await get_articles_by_subject(
    subject="Mathematics",
    grade_level="6-8",
    limit=5
)
```

## 📖 Dictionary Tools

### `get_word_definition`

Get educational word definitions with grade-appropriate complexity.

**Parameters:**
- `word` (string, required): Word to define
- `grade_level` (string, optional): Target grade level for appropriate complexity
- `include_pronunciation` (boolean, optional): Whether to include pronunciation information (default: true)

**Returns:**
Word definition with educational metadata

**Example Request:**
```python
await get_word_definition(
    word="ecosystem",
    grade_level="6-8",
    include_pronunciation=True
)
```

**Example Response:**
```json
{
    "word": "ecosystem",
    "definitions": [
        {
            "part_of_speech": "noun",
            "definition": "A biological community of interacting organisms and their physical environment",
            "grade_level_definition": "A community of living things and their environment working together",
            "complexity_score": 0.6,
            "examples": [
                "The forest ecosystem includes trees, animals, and soil",
                "Coral reefs are complex marine ecosystems"
            ]
        }
    ],
    "pronunciation": {
        "phonetic": "/ˈiːkoʊˌsɪstəm/",
        "audio_url": "https://api.dictionaryapi.dev/media/pronunciations/ecosystem.mp3"
    },
    "educational_context": {
        "grade_level": "6-8",
        "subject_applications": ["Science", "Environmental Studies"],
        "curriculum_standards": ["NGSS MS-LS2-1"],
        "related_concepts": ["habitat", "biodiversity", "food chain"]
    },
    "etymology": "From Greek 'oikos' (house) + 'systema' (organized whole)",
    "complexity_analysis": {
        "syllable_count": 4,
        "reading_difficulty": "intermediate",
        "academic_frequency": "high"
    }
}
```

---

### `get_vocabulary_analysis`

Analyze word complexity and educational value.

**Parameters:**
- `word` (string, required): Word to analyze
- `context` (string, optional): Optional context for better analysis

**Returns:**
Vocabulary analysis with educational insights

**Example Request:**
```python
await get_vocabulary_analysis(
    word="photosynthesis",
    context="plant biology lesson"
)
```

**Example Response:**
```json
{
    "word": "photosynthesis",
    "analysis": {
        "complexity_score": 0.7,
        "grade_level_recommendation": "6-8",
        "academic_tier": "Tier 3 (Domain-specific)",
        "frequency_rank": 15420,
        "syllable_count": 4,
        "morphological_analysis": {
            "prefix": "photo-",
            "root": "synthesis",
            "meaning_components": ["light", "putting together"]
        }
    },
    "educational_value": {
        "curriculum_importance": 0.9,
        "cross_curricular_potential": 0.8,
        "conceptual_difficulty": 0.7,
        "prerequisite_concepts": ["plants", "energy", "chemical reactions"]
    },
    "teaching_recommendations": {
        "introduction_grade": "3-5",
        "mastery_grade": "6-8",
        "scaffolding_words": ["plant", "sunlight", "food", "energy"],
        "visual_aids_recommended": true
    },
    "context_analysis": {
        "subject_area": "Biology",
        "lesson_fit": "Core concept",
        "assessment_potential": "High"
    }
}
```

---

### `get_word_examples`

Get educational examples and usage contexts for vocabulary.

**Parameters:**
- `word` (string, required): Word to find examples for
- `grade_level` (string, optional): Target grade level for appropriate examples
- `subject` (string, optional): Subject area for context-specific examples

**Returns:**
Educational examples with context

**Example Request:**
```python
await get_word_examples(
    word="fraction",
    grade_level="3-5",
    subject="Mathematics"
)
```

**Example Response:**
```json
{
    "word": "fraction",
    "examples": [
        {
            "sentence": "She ate 1/2 of the pizza",
            "context": "everyday life",
            "grade_level": "3-5",
            "educational_value": 0.8,
            "visual_representation": "pizza divided in half"
        },
        {
            "sentence": "The recipe calls for 3/4 cup of flour",
            "context": "cooking and measurement",
            "grade_level": "3-5",
            "educational_value": 0.9,
            "cross_curricular": ["Life Skills", "Science"]
        }
    ],
    "subject_specific_examples": {
        "Mathematics": [
            "Add the fractions 1/4 + 1/4 = 1/2",
            "Compare fractions: 3/4 > 1/2"
        ],
        "Science": [
            "The solution is 2/3 water and 1/3 salt",
            "3/5 of the plants showed growth"
        ]
    },
    "grade_progression": {
        "K-2": ["1/2 of an apple", "half of the cookies"],
        "3-5": ["3/4 cup of milk", "2/3 of the students"],
        "6-8": ["Convert 0.75 to the fraction 3/4", "Simplify 6/8 to 3/4"]
    }
}
```

---

### `get_pronunciation_guide`

Get phonetic information and pronunciation guides for language learning.

**Parameters:**
- `word` (string, required): Word to get pronunciation for
- `include_audio` (boolean, optional): Whether to include audio URL (default: true)

**Returns:**
Pronunciation guide with phonetic information

**Example Request:**
```python
await get_pronunciation_guide(
    word="photosynthesis",
    include_audio=True
)
```

**Example Response:**
```json
{
    "word": "photosynthesis",
    "pronunciations": [
        {
            "dialect": "American English",
            "phonetic": "/ˌfoʊtoʊˈsɪnθəsɪs/",
            "ipa": "ˌfoʊtoʊˈsɪnθəsɪs",
            "audio_url": "https://api.dictionaryapi.dev/media/pronunciations/photosynthesis-us.mp3"
        },
        {
            "dialect": "British English",
            "phonetic": "/ˌfəʊtəʊˈsɪnθəsɪs/",
            "ipa": "ˌfəʊtəʊˈsɪnθəsɪs",
            "audio_url": "https://api.dictionaryapi.dev/media/pronunciations/photosynthesis-uk.mp3"
        }
    ],
    "syllable_breakdown": {
        "syllables": ["pho", "to", "syn", "the", "sis"],
        "stress_pattern": "secondary-primary-unstressed-unstressed-unstressed",
        "syllable_count": 5
    },
    "teaching_aids": {
        "phonetic_spelling": "FOH-toh-SIN-thuh-sis",
        "rhyming_words": ["synthesis", "hypothesis"],
        "memory_devices": ["Photo + synthesis = making with light"]
    },
    "difficulty_assessment": {
        "pronunciation_difficulty": "intermediate",
        "common_mispronunciations": ["photo-SIN-thesis", "photo-syn-THEE-sis"],
        "teaching_tips": ["Break into familiar parts: photo + synthesis"]
    }
}
```

---

### `get_related_vocabulary`

Get synonyms, antonyms, and related educational terms.

**Parameters:**
- `word` (string, required): Base word
- `relationship_type` (string, optional): Type of relationship (synonyms, antonyms, related, all) (default: "all")
- `grade_level` (string, optional): Target grade level for appropriate vocabulary
- `limit` (integer, optional): Maximum number of related words (default: 10)

**Returns:**
Related vocabulary with educational context

**Example Request:**
```python
await get_related_vocabulary(
    word="democracy",
    relationship_type="related",
    grade_level="9-12",
    limit=8
)
```

**Example Response:**
```json
{
    "word": "democracy",
    "relationships": {
        "synonyms": [
            {
                "word": "republic",
                "grade_level": "9-12",
                "complexity_score": 0.8,
                "educational_context": "Government systems"
            }
        ],
        "related_terms": [
            {
                "word": "voting",
                "relationship": "process",
                "grade_level": "6-8",
                "complexity_score": 0.4,
                "educational_importance": 0.9
            },
            {
                "word": "constitution",
                "relationship": "foundation",
                "grade_level": "9-12",
                "complexity_score": 0.7,
                "curriculum_connection": ["Civics", "History"]
            }
        ],
        "antonyms": [
            {
                "word": "dictatorship",
                "grade_level": "9-12",
                "complexity_score": 0.8,
                "contrast_explanation": "Rule by one person vs. rule by the people"
            }
        ]
    },
    "educational_connections": {
        "subject_areas": ["Social Studies", "Civics", "History"],
        "grade_progression": {
            "6-8": ["voting", "elections", "citizens"],
            "9-12": ["republic", "constitution", "representative government"]
        },
        "cross_curricular": {
            "English Language Arts": ["persuasive writing", "debate"],
            "Mathematics": ["statistics", "polling data"]
        }
    },
    "concept_map": {
        "broader_concepts": ["government", "political systems"],
        "narrower_concepts": ["direct democracy", "representative democracy"],
        "related_concepts": ["freedom", "rights", "citizenship"]
    }
}
```

## 🔬 arXiv Tools

### `search_academic_papers`

Search academic papers with educational relevance filtering.

**Parameters:**
- `query` (string, required): Search query for papers
- `subject` (string, optional): Educational subject filter
- `academic_level` (string, optional): Target academic level (High School, Undergraduate, Graduate, Research)
- `max_results` (integer, optional): Maximum number of results (1-50, default: 10)
- `include_educational_analysis` (boolean, optional): Whether to include educational metadata (default: true)

**Returns:**
List of academic papers with educational metadata

**Example Request:**
```python
await search_academic_papers(
    query="machine learning education",
    academic_level="Undergraduate",
    subject="Computer Science",
    max_results=5
)
```

**Example Response:**
```json
[
    {
        "id": "2301.00001",
        "title": "Introduction to Machine Learning for Computer Science Students",
        "authors": ["Jane Smith", "John Doe"],
        "abstract": "This paper presents a comprehensive introduction to machine learning concepts...",
        "published": "2023-01-01",
        "updated": "2023-01-15",
        "categories": ["cs.LG", "cs.AI"],
        "academic_level": "Undergraduate",
        "educational_analysis": {
            "educational_relevance": 0.92,
            "complexity_score": 0.7,
            "prerequisite_knowledge": ["Linear Algebra", "Statistics", "Programming"],
            "learning_objectives": [
                "Understand ML fundamentals",
                "Implement basic algorithms",
                "Evaluate model performance"
            ],
            "estimated_study_time": "4-6 hours",
            "difficulty_level": "intermediate"
        },
        "subject": "Computer Science",
        "url": "https://arxiv.org/abs/2301.00001",
        "pdf_url": "https://arxiv.org/pdf/2301.00001.pdf"
    }
]
```

---

### `get_paper_summary`

Get paper summaries with educational analysis and accessibility scoring.

**Parameters:**
- `paper_id` (string, required): arXiv paper ID (e.g., '2301.00001')
- `include_educational_analysis` (boolean, optional): Whether to include educational metadata (default: true)

**Returns:**
Paper summary with educational metadata

**Example Request:**
```python
await get_paper_summary(
    paper_id="2301.00001",
    include_educational_analysis=True
)
```

**Example Response:**
```json
{
    "id": "2301.00001",
    "title": "Quantum Computing Fundamentals for High School Students",
    "authors": ["Dr. Alice Johnson", "Prof. Bob Wilson"],
    "abstract": "This paper introduces quantum computing concepts in an accessible way...",
    "summary": "A beginner-friendly introduction to quantum computing that covers basic principles, quantum gates, and simple algorithms. Designed specifically for high school students with basic physics knowledge.",
    "published": "2023-01-01",
    "categories": ["quant-ph", "physics.ed-ph"],
    "educational_analysis": {
        "academic_level": "High School",
        "educational_relevance": 0.88,
        "accessibility_score": 0.85,
        "complexity_breakdown": {
            "mathematical_complexity": 0.6,
            "conceptual_difficulty": 0.7,
            "prerequisite_burden": 0.5
        },
        "pedagogical_features": {
            "visual_aids": true,
            "worked_examples": true,
            "practice_problems": false,
            "real_world_applications": true
        },
        "curriculum_fit": {
            "subjects": ["Physics", "Mathematics", "Computer Science"],
            "standards_alignment": ["NGSS HS-PS4-3"],
            "grade_levels": ["11-12"]
        }
    },
    "key_concepts": ["quantum superposition", "quantum entanglement", "quantum gates"],
    "learning_outcomes": [
        "Understand basic quantum principles",
        "Recognize quantum vs classical computing differences",
        "Identify potential quantum computing applications"
    ]
}
```

---

### `get_recent_research`

Get recent research papers by educational subject.

**Parameters:**
- `subject` (string, required): Educational subject
- `days` (integer, optional): Number of days back to search (1-30, default: 7)
- `academic_level` (string, optional): Target academic level
- `max_results` (integer, optional): Maximum number of results (default: 10)

**Returns:**
List of recent papers in the subject area

**Example Request:**
```python
await get_recent_research(
    subject="Physics",
    days=30,
    academic_level="High School",
    max_results=3
)
```

---

### `get_research_by_level`

Get research papers appropriate for specific academic levels.

**Parameters:**
- `academic_level` (string, required): Target academic level (High School, Undergraduate, Graduate, Research)
- `subject` (string, optional): Subject area filter
- `max_results` (integer, optional): Maximum number of results (default: 10)

**Returns:**
List of papers appropriate for the academic level

**Example Request:**
```python
await get_research_by_level(
    academic_level="Graduate",
    subject="Mathematics",
    max_results=5
)
```

---

### `analyze_research_trends`

Analyze research trends for educational insights.

**Parameters:**
- `subject` (string, required): Educational subject to analyze
- `days` (integer, optional): Number of days to analyze (7-90, default: 30)

**Returns:**
Research trend analysis with educational insights

**Example Request:**
```python
await analyze_research_trends(
    subject="Artificial Intelligence",
    days=60
)
```

**Example Response:**
```json
{
    "subject": "Artificial Intelligence",
    "analysis_period": {
        "days": 60,
        "start_date": "2023-11-01",
        "end_date": "2023-12-31"
    },
    "trends": {
        "total_papers": 1247,
        "daily_average": 20.8,
        "growth_rate": 0.15,
        "trending_topics": [
            {
                "topic": "Large Language Models",
                "paper_count": 156,
                "growth_rate": 0.45,
                "educational_relevance": 0.82
            },
            {
                "topic": "Computer Vision",
                "paper_count": 134,
                "growth_rate": 0.23,
                "educational_relevance": 0.78
            }
        ]
    },
    "educational_insights": {
        "curriculum_implications": [
            "Increased focus on LLM applications in education",
            "Growing need for AI ethics education",
            "Integration of AI tools in computer science curriculum"
        ],
        "skill_demands": [
            "Natural language processing",
            "Ethical AI development",
            "Human-AI interaction design"
        ],
        "recommended_updates": [
            "Add LLM module to AI courses",
            "Include AI safety in curriculum",
            "Develop hands-on AI projects"
        ]
    },
    "academic_level_distribution": {
        "High School": 0.12,
        "Undergraduate": 0.28,
        "Graduate": 0.45,
        "Research": 0.15
    }
}
```

## 🖥️ Server Tools

### `get_server_status`

Get comprehensive server status and performance metrics.

**Parameters:**
None

**Returns:**
Server status information including cache and usage statistics

**Example Request:**
```python
await get_server_status()
```

**Example Response:**
```json
{
    "status": "healthy",
    "server": {
        "name": "openedu-mcp-server",
        "version": "1.0.0",
        "uptime": "2 days, 14 hours, 32 minutes",
        "start_time": "2024-01-13T08:30:00Z"
    },
    "cache": {
        "hit_rate": 0.73,
        "total_requests": 15420,
        "cache_hits": 11256,
        "cache_misses": 4164,
        "cache_size_mb": 45.2,
        "max_size_mb": 100,
        "entries_count": 2847,
        "cleanup_runs": 12,
        "last_cleanup": "2024-01-15T14:20:00Z"
    },
    "rate_limits": {
        "open_library": {
            "limit": 100,
            "remaining": 87,
            "reset_time": "2024-01-15T15:00:00Z",
            "status": "healthy"
        },
        "wikipedia": {
            "limit": 200,
            "remaining": 156,
            "reset_time": "2024-01-15T15:00:00Z",
            "status": "healthy"
        },
        "dictionary": {
            "limit": 450,
            "remaining": 423,
            "reset_time": "2024-01-15T16:00:00Z",
            "status": "healthy"
        },
        "arxiv": {
            "limit": 3,
            "remaining": 2,
            "reset_time": "2024-01-15T14:31:00Z",
            "status": "healthy"
        }
    },
    "usage": {
        "total_tool_calls": 8934,
        "most_used_tools": [
            {"tool": "search_educational_books", "count": 1247},
            {"tool": "get_word_definition", "count": 1156},
            {"tool": "search_educational_articles", "count": 1089}
        ],
        "grade_level_distribution": {
            "K-2": 0.18,
            "3-5": 0.24,
            "6-8": 0.28,
            "9-12": 0.22,
            "College": 0.08
        },
        "subject_distribution": {
            "Mathematics": 0.32,
            "Science": 0.28,
            "English Language Arts": 0.21,
            "Social Studies": 0.12,
            "Other": 0.07
        }
    },
    "performance": {
        "average_response_time_ms": 245,
        "p95_response_time_ms": 890,
        "error_rate": 0.002,
        "concurrent_requests": 3,
        "max_concurrent_requests": 50
    },
    "message": "OpenEdu MCP Server is running with core infrastructure ready"
}
```

## 🚨 Error Handling

### Common Error Types

#### `OpenEduMCPError`
Base exception for all OpenEdu MCP Server errors.

**Common Causes:**
- Invalid parameters
- API failures
- Service unavailable
- Rate limit exceeded

**Example Error Response:**
```json
{
    "error": "OpenEduMCPError",
    "message": "Book search failed: Invalid grade level 'K-13'",
    "code": "INVALID_PARAMETER",
    "details": {
        "parameter": "grade_level",
        "valid_values": ["K-2", "3-5", "6-8", "9-12", "College"]
    }
}
```

### Parameter Validation

#### Grade Level Validation
Valid grade levels: `K-2`, `3-5`, `6-8`, `9-12`, `College`

#### Subject Validation
Valid subjects: `Mathematics`, `Science`, `English Language Arts`, `Social Studies`, `Arts`, `Physical Education`, `Technology`

#### Limit Validation
- Minimum: 1
- Maximum: 50
- Default: 10

### Rate Limiting Errors

When rate limits are exceeded, the server returns:
```json
{
    "error": "RateLimitExceeded",
    "message": "API rate limit exceeded for Wikipedia",
    "retry_after": 60,
    "limit": 200,
    "reset_time": "2024-01-15T15:00:00Z"
}
```

## 📊 Response Formats

### Educational Metadata Structure

All educational content includes standardized metadata:

```json
{
    "educational_metadata": {
        "grade_level": "6-8",
        "subject": "Mathematics",
        "complexity_score": 0.6,
        "educational_value": 0.9,
        "curriculum_alignment": ["Common Core", "NCTM"],
        "learning_objectives": ["Understand linear equations"],
        "prerequisites": ["basic algebra"],
        "estimated_time": "45 minutes",
        "difficulty_level": "intermediate",
        "reading_level": "Grade 7"
    }
}
```

### Pagination

For tools that return lists, pagination information is included:

```json
{
    "results": [...],
    "pagination": {
        "total_count": 156,
        "page": 1,
        "per_page": 10,
        "total_pages": 16,
        "has_next": true,
        "has_previous": false
    }
}
```

## 🔧 Best Practices

### Optimal Usage Patterns

1. **Always specify grade level** for age-appropriate content
2. **Use subject filters** to narrow search results
3. **Check educational value scores** (aim for >0.7)
4. **Consider complexity scores** for difficulty assessment
5. **Leverage curriculum alignment** for standards-based planning

### Performance Optimization

1. **Cache frequently used queries** - the server automatically caches responses
2. **Use appropriate limits** - don't request more results than needed
3. **Batch related requests** - group similar queries together
4. **Monitor rate limits** - check server status regularly

### Error Recovery

1. **Handle rate limiting gracefully** - implement exponential backoff
2. **Validate parameters** - check inputs before making requests
3. **Provide fallbacks** - have alternative content sources
4. **Log errors appropriately** - track issues for debugging

---

This API reference provides comprehensive documentation for all OpenEdu MCP Server tools. For additional examples and use cases, see the [Educational Features Guide](EDUCATIONAL_FEATURES.md) and run the demo script (`demo_education_mcp.py`).