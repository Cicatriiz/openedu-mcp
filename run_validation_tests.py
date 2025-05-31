#!/usr/bin/env python3
"""
Real-World API Validation Test Runner for OpenEdu MCP Server.

This script runs comprehensive validation tests against live APIs to ensure
all integrations are working correctly in production environments.
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent / "tests"))

from test_real_world_validation import RealWorldValidator


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run real-world validation tests for OpenEdu MCP Server APIs"
    )
    
    parser.add_argument(
        "--api",
        choices=["arxiv", "wikipedia", "dictionary", "openlibrary", "all"],
        default="all",
        help="Specific API to test (default: all)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for detailed report (default: auto-generated)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick tests only (skip performance and integration tests)"
    )
    
    return parser.parse_args()


async def run_specific_api_tests(validator: RealWorldValidator, api: str):
    """Run tests for a specific API."""
    print(f"🎯 Running tests for {api.upper()} API only")
    
    # Map API names to test methods
    api_tests = {
        "arxiv": [
            ("ArXiv Basic Search", "arxiv", validator.test_arxiv_basic_search),
            ("ArXiv Paper Details", "arxiv", validator.test_arxiv_paper_details),
            ("ArXiv Recent Papers", "arxiv", validator.test_arxiv_recent_papers),
            ("ArXiv Educational Features", "arxiv", validator.test_arxiv_educational_features),
            ("ArXiv Research Trends", "arxiv", validator.test_arxiv_research_trends),
            ("ArXiv Health Check", "arxiv", validator.test_arxiv_health_check),
        ],
        "wikipedia": [
            ("Wikipedia Search", "wikipedia", validator.test_wikipedia_search),
            ("Wikipedia Article Summary", "wikipedia", validator.test_wikipedia_article_summary),
            ("Wikipedia Article Content", "wikipedia", validator.test_wikipedia_article_content),
            ("Wikipedia Featured Article", "wikipedia", validator.test_wikipedia_featured_article),
            ("Wikipedia Educational Features", "wikipedia", validator.test_wikipedia_educational_features),
            ("Wikipedia Health Check", "wikipedia", validator.test_wikipedia_health_check),
        ],
        "dictionary": [
            ("Dictionary Word Definition", "dictionary", validator.test_dictionary_word_definition),
            ("Dictionary Word Examples", "dictionary", validator.test_dictionary_word_examples),
            ("Dictionary Phonetics", "dictionary", validator.test_dictionary_phonetics),
            ("Dictionary Comprehensive Data", "dictionary", validator.test_dictionary_comprehensive_data),
            ("Dictionary Educational Features", "dictionary", validator.test_dictionary_educational_features),
            ("Dictionary Vocabulary Analysis", "dictionary", validator.test_dictionary_vocabulary_analysis),
            ("Dictionary Health Check", "dictionary", validator.test_dictionary_health_check),
        ],
        "openlibrary": [
            ("OpenLibrary Book Search", "openlibrary", validator.test_openlibrary_book_search),
            ("OpenLibrary Book Details", "openlibrary", validator.test_openlibrary_book_details),
            ("OpenLibrary Subject Search", "openlibrary", validator.test_openlibrary_subject_search),
            ("OpenLibrary Educational Features", "openlibrary", validator.test_openlibrary_educational_features),
            ("OpenLibrary Book Recommendations", "openlibrary", validator.test_openlibrary_book_recommendations),
            ("OpenLibrary Health Check", "openlibrary", validator.test_openlibrary_health_check),
        ]
    }
    
    await validator.initialize_services()
    
    # Run tests for the specific API
    tests = api_tests.get(api, [])
    for test_name, api_service, test_func in tests:
        await validator.run_test(test_name, api_service, test_func)
        await asyncio.sleep(0.5)  # Rate limiting
    
    await validator.cleanup_services()
    return validator.generate_report()


async def run_quick_tests(validator: RealWorldValidator):
    """Run quick validation tests (health checks and basic functionality)."""
    print("⚡ Running quick validation tests")
    
    quick_tests = [
        ("ArXiv Health Check", "arxiv", validator.test_arxiv_health_check),
        ("ArXiv Basic Search", "arxiv", validator.test_arxiv_basic_search),
        ("Wikipedia Health Check", "wikipedia", validator.test_wikipedia_health_check),
        ("Wikipedia Search", "wikipedia", validator.test_wikipedia_search),
        ("Dictionary Health Check", "dictionary", validator.test_dictionary_health_check),
        ("Dictionary Word Definition", "dictionary", validator.test_dictionary_word_definition),
        ("OpenLibrary Health Check", "openlibrary", validator.test_openlibrary_health_check),
        ("OpenLibrary Book Search", "openlibrary", validator.test_openlibrary_book_search),
    ]
    
    await validator.initialize_services()
    
    for test_name, api_service, test_func in quick_tests:
        await validator.run_test(test_name, api_service, test_func)
        await asyncio.sleep(0.3)  # Shorter delay for quick tests
    
    await validator.cleanup_services()
    return validator.generate_report()


async def main():
    """Main execution function."""
    args = parse_arguments()
    
    print("🔬 OpenEdu MCP Server - Real-World API Validation")
    print("=" * 60)
    
    validator = RealWorldValidator()
    
    try:
        # Run appropriate tests based on arguments
        if args.quick:
            report = await run_quick_tests(validator)
        elif args.api != "all":
            report = await run_specific_api_tests(validator, args.api)
        else:
            report = await validator.run_all_tests()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        success_rate = (report.passed_tests / report.total_tests) * 100 if report.total_tests > 0 else 0
        
        print(f"🕒 Duration: {report.total_duration_seconds:.2f}s")
        print(f"📋 Tests: {report.total_tests}")
        print(f"✅ Passed: {report.passed_tests}")
        print(f"❌ Failed: {report.failed_tests}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        # API Health Summary
        if report.api_health_status:
            print(f"\n🏥 API Health:")
            for api, status in report.api_health_status.items():
                icon = "✅" if status == "PASS" else "❌"
                print(f"  {icon} {api.upper()}")
        
        # Educational Features Summary
        edu_features = report.educational_features_validation
        if edu_features:
            print(f"\n🎓 Educational Features:")
            print(f"  📚 Metadata Tests: {edu_features.get('educational_metadata_present', 0)}")
            workflow_status = "✅" if edu_features.get('cross_api_workflow_success', False) else "❌"
            print(f"  🔗 Cross-API Workflow: {workflow_status}")
        
        # Save report
        if args.output:
            report_file = args.output
        else:
            from datetime import datetime
            report_file = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        import json
        from dataclasses import asdict
        with open(report_file, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        
        print(f"\n📄 Report: {report_file}")
        
        # Exit with appropriate code
        if report.failed_tests > 0:
            print(f"\n⚠️ {report.failed_tests} test(s) failed")
            if args.verbose:
                print("\nFailed tests:")
                for result in report.test_results:
                    if result.status == "FAIL":
                        print(f"  ❌ {result.test_name}: {result.error_message}")
            return False
        else:
            print(f"\n🎉 All tests passed!")
            return True
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)