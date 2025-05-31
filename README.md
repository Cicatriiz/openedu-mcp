# OpenEdu MCP Server

A comprehensive Model Context Protocol (MCP) server designed to provide educational resources and support curriculum planning for educators. This server integrates with multiple educational APIs to provide access to books, articles, definitions, and research papers with intelligent educational filtering and grade-level appropriateness.

## 🎓 Features

### Complete API Integration Suite
- **📚 Open Library Integration**: Educational book search, recommendations, and metadata
- **🌐 Wikipedia Integration**: Educational article analysis with grade-level filtering
- **📖 Dictionary Integration**: Vocabulary analysis and language learning support
- **🔬 arXiv Integration**: Academic paper search with educational relevance scoring

### Educational Intelligence
- **Grade Level Filtering**: K-2, 3-5, 6-8, 9-12, College level content
- **Subject Classification**: Mathematics, Science, ELA, Social Studies, Arts, PE, Technology
- **Curriculum Alignment**: Common Core, NGSS, State Standards support
- **Educational Metadata**: Complexity scoring, reading levels, educational value assessment

### Performance & Reliability
- **Intelligent Caching**: SQLite-based caching with TTL support
- **Rate Limiting**: Built-in rate limiting to respect API quotas
- **Usage Analytics**: Comprehensive usage tracking and performance metrics
- **Error Handling**: Robust error handling with educational context preservation

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip package manager

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/your-username/opened-mcp.git
cd opened-mcp
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up configuration:**
```bash
cp .env.example .env
# Edit .env with your preferred settings if needed
```

4. **Run the server:**
```bash
python -m src.main
```

5. **Test the installation:**
```bash
python -m src.main
```

### Development Setup

For development, install additional dependencies:
```bash
pip install -r requirements-dev.txt
```

Run tests:
```bash
# Unit tests
pytest tests/

# Integration tests
pytest tests/test_integration/

# Performance tests
pytest tests/test_performance.py
```

Format code:
```bash
black src tests
isort src tests
```

## 🛠️ MCP Tools Reference

The Education MCP Server provides **20+ MCP tools** across four API integrations:

### 📚 Open Library Tools (4 tools)

#### `search_educational_books`
Search for educational books with grade-level and subject filtering.
```python
search_educational_books(
    query="mathematics",
    subject="Mathematics", 
    grade_level="6-8",
    limit=10
)
```

#### `get_book_details_by_isbn`
Get detailed book information by ISBN with educational metadata.
```python
get_book_details_by_isbn(
    isbn="9780134685991",
    include_cover=True
)
```

#### `search_books_by_subject`
Search books by educational subject with curriculum alignment.
```python
search_books_by_subject(
    subject="Science",
    grade_level="3-5",
    limit=10
)
```

#### `get_book_recommendations`
Get curated book recommendations for specific grade levels.
```python
get_book_recommendations(
    grade_level="9-12",
    subject="Physics",
    limit=5
)
```

### 🌐 Wikipedia Tools (5 tools)

#### `search_educational_articles`
Search Wikipedia articles with educational filtering and analysis.
```python
search_educational_articles(
    query="photosynthesis",
    grade_level="3-5",
    subject="Science",
    limit=5
)
```

#### `get_article_summary`
Get article summaries with educational metadata and complexity analysis.
```python
get_article_summary(
    title="Solar System",
    include_educational_analysis=True
)
```

#### `get_article_content`
Get full article content with educational enrichment.
```python
get_article_content(
    title="Photosynthesis",
    include_images=True
)
```

#### `get_featured_article`
Get Wikipedia's featured article with educational analysis.
```python
get_featured_article(
    date="2024/01/15",
    language="en"
)
```

#### `get_articles_by_subject`
Get articles by educational subject with grade-level filtering.
```python
get_articles_by_subject(
    subject="Mathematics",
    grade_level="6-8",
    limit=10
)
```

### 📖 Dictionary Tools (5 tools)

#### `get_word_definition`
Get educational word definitions with grade-appropriate complexity.
```python
get_word_definition(
    word="ecosystem",
    grade_level="6-8",
    include_pronunciation=True
)
```

#### `get_vocabulary_analysis`
Analyze word complexity and educational value.
```python
get_vocabulary_analysis(
    word="photosynthesis",
    context="plant biology lesson"
)
```

#### `get_word_examples`
Get educational examples and usage contexts for vocabulary.
```python
get_word_examples(
    word="fraction",
    grade_level="3-5",
    subject="Mathematics"
)
```

#### `get_pronunciation_guide`
Get phonetic information and pronunciation guides.
```python
get_pronunciation_guide(
    word="photosynthesis",
    include_audio=True
)
```

#### `get_related_vocabulary`
Get synonyms, antonyms, and related educational terms.
```python
get_related_vocabulary(
    word="democracy",
    relationship_type="related",
    grade_level="9-12",
    limit=10
)
```

### 🔬 arXiv Tools (5 tools)

#### `search_academic_papers`
Search academic papers with educational relevance filtering.
```python
search_academic_papers(
    query="machine learning education",
    academic_level="Undergraduate",
    subject="Computer Science",
    max_results=10
)
```

#### `get_paper_summary`
Get paper summaries with educational analysis and accessibility scoring.
```python
get_paper_summary(
    paper_id="2301.00001",
    include_educational_analysis=True
)
```

#### `get_recent_research`
Get recent research papers by educational subject.
```python
get_recent_research(
    subject="Physics",
    days=30,
    academic_level="High School",
    max_results=5
)
```

#### `get_research_by_level`
Get research papers appropriate for specific academic levels.
```python
get_research_by_level(
    academic_level="Graduate",
    subject="Mathematics",
    max_results=10
)
```

#### `analyze_research_trends`
Analyze research trends for educational insights.
```python
analyze_research_trends(
    subject="Artificial Intelligence",
    days=90
)
```

### 🖥️ Server Tools (1 tool)

#### `get_server_status`
Get comprehensive server status and performance metrics.
```python
get_server_status()
```

## 📋 Educational Use Cases

### Elementary Education (K-2)
```python
# Find age-appropriate books
books = await search_educational_books(
    query="animals", 
    grade_level="K-2", 
    subject="Science"
)

# Get simple definitions
definition = await get_word_definition(
    word="habitat", 
    grade_level="K-2"
)

# Find educational articles
articles = await search_educational_articles(
    query="animal homes", 
    grade_level="K-2"
)
```

### Middle School STEM (6-8)
```python
# Get math textbooks
books = await search_books_by_subject(
    subject="Mathematics", 
    grade_level="6-8"
)

# Analyze vocabulary complexity
analysis = await get_vocabulary_analysis(
    word="equation", 
    context="solving math problems"
)

# Find related terms
related = await get_related_vocabulary(
    word="algebra", 
    grade_level="6-8"
)
```

### High School Advanced (9-12)
```python
# Get physics recommendations
books = await get_book_recommendations(
    grade_level="9-12", 
    subject="Physics"
)

# Get detailed articles
article = await get_article_content(
    title="Quantum mechanics"
)

# Find accessible research
papers = await search_academic_papers(
    query="climate change", 
    academic_level="High School"
)
```

### College Research
```python
# Find academic textbooks
books = await search_educational_books(
    query="calculus", 
    grade_level="College"
)

# Get recent research
research = await get_recent_research(
    subject="Computer Science", 
    academic_level="Graduate"
)

# Analyze trends
trends = await analyze_research_trends(
    subject="Machine Learning"
)
```

## ⚙️ Configuration

### Configuration Files
The server uses YAML configuration files in the `config/` directory:

```yaml
# config/default.yaml
server:
  name: "openedu-mcp-server"
  version: "1.0.0"

education:
  grade_levels:
    - "K-2"
    - "3-5" 
    - "6-8"
    - "9-12"
    - "College"
  
  subjects:
    - "Mathematics"
    - "Science"
    - "English Language Arts"
    - "Social Studies"
    - "Arts"
    - "Physical Education"
    - "Technology"

apis:
  open_library:
    rate_limit: 100  # requests per minute
  wikipedia:
    rate_limit: 200  # requests per minute
  dictionary:
    rate_limit: 450  # requests per hour
  arxiv:
    rate_limit: 3    # requests per second
```

### Environment Variables
Override configuration with environment variables:
```bash
export OPENED_MCP_CACHE_TTL=7200
export OPENED_MCP_LOG_LEVEL=DEBUG
export OPENED_MCP_RATE_LIMIT_WIKIPEDIA=300
```

## 🏗️ Architecture

```
Education MCP Server
├── API Layer (FastMCP)
│   ├── 20+ MCP Tools
│   └── Request/Response Handling
├── Service Layer
│   ├── Cache Service (SQLite)
│   ├── Rate Limiting Service
│   └── Usage Tracking Service
├── Tool Layer
│   ├── Open Library Tools
│   ├── Wikipedia Tools
│   ├── Dictionary Tools
│   └── arXiv Tools
├── API Layer
│   ├── Open Library API
│   ├── Wikipedia API
│   ├── Dictionary API
│   └── arXiv API
└── Data Layer
    ├── Educational Models
    ├── Cache Database
    └── Usage Analytics
```

## 📊 Performance

### Caching Strategy
- **Cache Hit Rate**: >70% for repeated queries
- **Response Time**: <500ms for cached requests, <2000ms for uncached
- **Cache Size**: Configurable with automatic cleanup
- **TTL Management**: Intelligent expiration based on content type

### Rate Limiting
- **Open Library**: 100 requests/minute
- **Wikipedia**: 200 requests/minute  
- **Dictionary**: 450 requests/hour
- **arXiv**: 3 requests/second

### Concurrent Handling
- **Async Operations**: Non-blocking I/O for all API calls
- **Connection Pooling**: Efficient HTTP connection management
- **Resource Limits**: Configurable memory and disk usage limits

## 🧪 Testing

### Run All Tests
```bash
# Unit tests
pytest tests/test_tools/ -v

# Integration tests
pytest tests/test_integration/ -v

# Performance tests
pytest tests/test_performance.py -v

# Real API tests (requires internet)
make validate
```

### Test Coverage
```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Validation Tests
```bash
make validate
```

## 🧪 Real API Validation Tests

We've implemented comprehensive real-world validation tests to ensure production readiness. These tests verify functionality against live services, not mocks.

### Features
- Tests all 20+ MCP tools against their respective live APIs
- Validates educational workflows for different grade levels
- Measures performance metrics (response times, cache rates, error rates)
- Tests error handling with invalid inputs and edge cases
- Verifies caching behavior with real API responses

### Running Validation Tests
```bash
python run_validation_tests.py
```

The script will:
1. Test all API integrations (Open Library, Wikipedia, Dictionary, arXiv)
2. Validate educational workflows:
   - Elementary Education (K-2)
   - High School STEM (9-12)
   - College Research
   - Educator Resources
3. Measure performance metrics:
   - Response times for each API
   - Cache hit/miss rates
   - Rate limiting effectiveness
   - Educational filtering processing time
4. Generate a detailed JSON report with test results and performance statistics

### Test Cases
1. **Open Library**:
   - Search for "Harry Potter" with grade-level filtering
   - Get book details by ISBN (e.g., 9780439064866)
   - Check availability for a known book
   - Verify educational metadata enrichment

2. **Wikipedia**:
   - Search for "Quantum Mechanics" with academic level filtering
   - Get article summary for "Albert Einstein"
   - Retrieve featured article of the day
   - Verify content analysis and complexity scoring

3. **Dictionary API**:
   - Get definition for "photosynthesis" with educational context
   - Test pronunciation guide for "quinoa"
   - Verify vocabulary analysis for STEM terms
   - Test grade-level appropriate definitions

4. **arXiv**:
   - Search for "machine learning" papers with educational filtering
   - Get recent AI research papers
   - Verify academic level assessment
   - Test research trend analysis

## 📚 Documentation

- **[Educational Features Guide](docs/EDUCATIONAL_FEATURES.md)**: Complete educational capabilities
- **[API Reference](docs/API_REFERENCE.md)**: Detailed MCP tool documentation
- **[Performance Benchmarks](docs/PERFORMANCE.md)**: Real-world test results and metrics
- **[Deployment Guide](docs/DEPLOYMENT.md)**: Production deployment instructions
- **[Performance Guide](docs/PERFORMANCE.md)**: Optimization and monitoring

## 🔧 Development Status

**✅ COMPLETE - All Features Implemented**

### Core Infrastructure ✅
- [x] Project structure and configuration
- [x] Core services (caching, rate limiting, usage tracking)
- [x] Base models and validation
- [x] FastMCP server setup
- [x] Educational filtering framework

### API Integrations ✅
- [x] Open Library API integration (4 tools)
- [x] Wikipedia API integration (5 tools)
- [x] Dictionary API integration (5 tools)
- [x] arXiv API integration (5 tools)
- [x] Educational content filtering
- [x] Cross-API educational workflows

### Testing & Documentation ✅
- [x] Comprehensive unit tests
- [x] Integration test suite
- [x] Performance benchmarks
- [x] Demo script with all features
- [x] Complete documentation
- [x] API reference guide

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add type hints for all functions
- Include docstrings for all public methods
- Write tests for new features
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For questions, issues, or contributions:

- **Issues**: Create an issue in the repository
- **Documentation**: Check the `docs/` directory
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact the maintainers

## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) framework
- Integrates with Open Library, Wikipedia, Dictionary API, and arXiv
- Designed for educational use cases and curriculum planning
- Inspired by the need for accessible educational technology

---

**Education MCP Server** - Empowering educators with intelligent educational resource discovery and curriculum planning tools.