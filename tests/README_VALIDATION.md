# Real-World API Validation Tests

This directory contains comprehensive real-world validation tests for all API integrations in the OpenEdu MCP Server. These tests validate functionality against live services to ensure production readiness.

## Overview

The validation test suite provides:

- **Comprehensive API Testing**: Tests all four API integrations (ArXiv, Wikipedia, Dictionary, OpenLibrary)
- **Educational Feature Validation**: Verifies educational metadata, grade-level filtering, and subject classification
- **Performance Testing**: Measures response times and concurrent request handling
- **Health Monitoring**: Checks API availability and service status
- **Cross-API Integration**: Tests workflows that span multiple APIs
- **Detailed Reporting**: Generates comprehensive reports with metrics and insights

## Test Structure

### Core Test Files

- [`test_real_world_validation.py`](./test_real_world_validation.py) - Main validation test suite
- [`test_config.yaml`](./test_config.yaml) - Test configuration and parameters
- [`../run_validation_tests.py`](../run_validation_tests.py) - Test runner script

### Test Categories

#### 1. ArXiv API Tests
- **Basic Search**: Validates paper search functionality
- **Paper Details**: Tests individual paper retrieval
- **Recent Papers**: Verifies recent publication queries
- **Educational Features**: Tests educational metadata enrichment
- **Research Trends**: Validates trend analysis capabilities
- **Health Check**: Monitors API availability

#### 2. Wikipedia API Tests
- **Search**: Tests article search functionality
- **Article Summary**: Validates summary retrieval
- **Article Content**: Tests full content access
- **Featured Articles**: Checks featured content access
- **Educational Features**: Tests educational article filtering
- **Health Check**: Monitors API availability

#### 3. Dictionary API Tests
- **Word Definition**: Tests definition retrieval
- **Word Examples**: Validates example sentences
- **Phonetics**: Tests pronunciation data
- **Comprehensive Data**: Validates complete word information
- **Educational Features**: Tests grade-level appropriate definitions
- **Vocabulary Analysis**: Tests multi-word analysis
- **Health Check**: Monitors API availability

#### 4. OpenLibrary API Tests
- **Book Search**: Tests book search functionality
- **Book Details**: Validates detailed book information
- **Subject Search**: Tests subject-based queries
- **Educational Features**: Tests educational book filtering
- **Book Recommendations**: Validates recommendation engine
- **Health Check**: Monitors API availability

#### 5. Integration Tests
- **Cross-API Workflow**: Tests educational workflows across APIs
- **Performance Under Load**: Tests concurrent API usage

## Running the Tests

### Quick Start

```bash
# Run all validation tests
python run_validation_tests.py

# Run tests for a specific API
python run_validation_tests.py --api arxiv

# Run quick health checks only
python run_validation_tests.py --quick

# Run with verbose output
python run_validation_tests.py --verbose
```

### Command Line Options

```bash
python run_validation_tests.py [OPTIONS]

Options:
  --api {arxiv,wikipedia,dictionary,openlibrary,all}
                        Specific API to test (default: all)
  --output OUTPUT       Output file for detailed report
  --verbose             Enable verbose output
  --quick               Run quick tests only
  --help                Show help message
```

### Examples

```bash
# Test only Wikipedia API with detailed output
python run_validation_tests.py --api wikipedia --verbose

# Quick health check of all APIs
python run_validation_tests.py --quick

# Full test suite with custom report file
python run_validation_tests.py --output my_validation_report.json

# Test dictionary API only
python run_validation_tests.py --api dictionary
```

## Test Configuration

The test suite uses [`test_config.yaml`](./test_config.yaml) for configuration:

### Key Configuration Sections

- **Execution Settings**: Rate limits, timeouts, retry attempts
- **Test Queries**: Sample queries for each API
- **Thresholds**: Expected performance and quality metrics
- **Educational Features**: Grade levels, subjects, academic levels
- **API-Specific Settings**: Customized parameters per API
- **Performance Testing**: Load testing configuration
- **Reporting**: Output format and metric tracking

### Customizing Tests

Edit `test_config.yaml` to:
- Add new test queries
- Adjust performance thresholds
- Configure educational parameters
- Modify reporting options

## Understanding Test Results

### Test Status Codes
- **PASS**: Test completed successfully
- **FAIL**: Test failed with error
- **SKIP**: Test was skipped

### Report Structure

The validation report includes:

```json
{
  "timestamp": "2025-05-30T20:43:00",
  "total_tests": 28,
  "passed_tests": 26,
  "failed_tests": 2,
  "skipped_tests": 0,
  "total_duration_seconds": 45.2,
  "api_health_status": {
    "arxiv": "PASS",
    "wikipedia": "PASS",
    "dictionary": "FAIL",
    "openlibrary": "PASS"
  },
  "performance_metrics": {
    "average_test_duration": 1.61,
    "fastest_test": "Dictionary Health Check",
    "slowest_test": "ArXiv Research Trends"
  },
  "educational_features_validation": {
    "educational_metadata_present": 4,
    "cross_api_workflow_success": true,
    "grade_level_filtering": true,
    "subject_classification": true
  }
}
```

### Key Metrics

- **Success Rate**: Percentage of tests that passed
- **API Health**: Individual API availability status
- **Response Times**: Performance metrics for each API
- **Educational Features**: Validation of educational functionality

## Troubleshooting

### Common Issues

#### 1. API Rate Limiting
**Symptoms**: Tests fail with rate limit errors
**Solution**: Increase delays in `test_config.yaml` or run tests with `--quick` flag

#### 2. Network Connectivity
**Symptoms**: Multiple API health checks fail
**Solution**: Check internet connection and firewall settings

#### 3. API Service Outages
**Symptoms**: Specific API tests consistently fail
**Solution**: Check API status pages and retry later

#### 4. Educational Feature Failures
**Symptoms**: Educational metadata tests fail
**Solution**: Verify model classes and educational enrichment logic

### Debug Mode

Run tests with verbose output for detailed error information:

```bash
python run_validation_tests.py --verbose
```

### Manual Testing

For debugging specific issues, run individual test methods:

```python
# Example: Test ArXiv search manually
import asyncio
from test_real_world_validation import RealWorldValidator

async def debug_arxiv():
    validator = RealWorldValidator()
    await validator.initialize_services()
    try:
        result = await validator.test_arxiv_basic_search()
        print(f"Result: {result}")
    finally:
        await validator.cleanup_services()

asyncio.run(debug_arxiv())
```

## Continuous Integration

### GitHub Actions Integration

Add to `.github/workflows/validation.yml`:

```yaml
name: API Validation Tests

on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM
  workflow_dispatch:

jobs:
  validate-apis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run validation tests
        run: |
          python run_validation_tests.py --output validation_report.json
      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: validation-report
          path: validation_report.json
```

### Monitoring Integration

The validation tests can be integrated with monitoring systems:

- **Prometheus**: Export metrics from test results
- **Grafana**: Visualize API health and performance trends
- **AlertManager**: Set up alerts for test failures

## Best Practices

### Running Tests

1. **Regular Execution**: Run validation tests daily or before deployments
2. **Environment Isolation**: Use separate test configurations for different environments
3. **Rate Limiting**: Respect API rate limits to avoid service disruption
4. **Error Handling**: Review failed tests promptly and investigate root causes

### Maintaining Tests

1. **Update Test Data**: Regularly refresh test queries and expected results
2. **Monitor API Changes**: Watch for API updates that might affect tests
3. **Performance Baselines**: Update performance thresholds based on historical data
4. **Educational Content**: Keep educational parameters current with curriculum standards

### Interpreting Results

1. **Trend Analysis**: Look for patterns in test results over time
2. **Performance Degradation**: Monitor for gradual performance decreases
3. **Educational Quality**: Ensure educational features maintain high relevance scores
4. **Cross-API Consistency**: Verify that all APIs provide consistent educational value

## Contributing

When adding new tests:

1. Follow the existing test pattern in `RealWorldValidator`
2. Add appropriate assertions and error handling
3. Include educational feature validation where applicable
4. Update test configuration in `test_config.yaml`
5. Document new tests in this README

### Test Method Template

```python
async def test_new_feature(self) -> Dict[str, Any]:
    """Test description."""
    # Perform API call
    result = await self.client.new_method()
    
    # Validate result
    assert result is not None, "Failed to get result"
    assert 'expected_field' in result, "Missing expected field"
    
    # Return test details
    return {
        "feature_tested": "new_feature",
        "result_count": len(result),
        "validation_passed": True
    }
```

## Support

For issues with validation tests:

1. Check the troubleshooting section above
2. Review test logs and error messages
3. Verify API service status
4. Check configuration settings
5. Create an issue with detailed error information

---

**Note**: These tests make real API calls to live services. Ensure you have appropriate network access and respect API terms of service and rate limits.