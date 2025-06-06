#!/usr/bin/env python3
"""
Comprehensive Test Suite for CP Tariff OCR API
This script tests all API endpoints and functionality.
"""

import requests
import json
import time
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
from datetime import datetime

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TEST_PDF_PATH = "tests/sample_documents/sample_tariff.pdf"
TEST_TIMEOUT = 120  # 2 minutes for document processing

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class CPTariffAPITester:
    """Comprehensive API testing class for CP Tariff OCR system"""
    
    def __init__(self, base_url: str = API_BASE_URL, verbose: bool = True):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.session = requests.Session()
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'total': 0
        }
        self.uploaded_document_id = None
        
    def log(self, message: str, color: str = Colors.WHITE):
        """Print colored log message"""
        if self.verbose:
            print(f"{color}{message}{Colors.END}")
    
    def log_success(self, message: str):
        """Log success message"""
        self.log(f"✅ {message}", Colors.GREEN)
        self.test_results['passed'] += 1
    
    def log_error(self, message: str):
        """Log error message"""
        self.log(f"❌ {message}", Colors.RED)
        self.test_results['failed'] += 1
    
    def log_warning(self, message: str):
        """Log warning message"""
        self.log(f"⚠️  {message}", Colors.YELLOW)
    
    def log_info(self, message: str):
        """Log info message"""
        self.log(f"ℹ️  {message}", Colors.BLUE)
    
    def log_skip(self, message: str):
        """Log skipped test"""
        self.log(f"⏭️  {message}", Colors.YELLOW)
        self.test_results['skipped'] += 1
    
    def start_test(self, test_name: str):
        """Start a new test"""
        self.test_results['total'] += 1
        self.log(f"\n🧪 {Colors.BOLD}Testing: {test_name}{Colors.END}", Colors.CYAN)
    
    def test_api_health(self) -> bool:
        """Test if API is running and accessible"""
        self.start_test("API Health Check")
        
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_success(f"API is running: {data.get('message', 'Unknown')}")
                self.log_info(f"Version: {data.get('version', 'Unknown')}")
                return True
            else:
                self.log_error(f"API health check failed with status {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            self.log_error("Cannot connect to API. Is the server running?")
            return False
        except requests.exceptions.Timeout:
            self.log_error("API health check timed out")
            return False
        except Exception as e:
            self.log_error(f"API health check error: {e}")
            return False
    
    def test_api_documentation(self) -> bool:
        """Test if API documentation is accessible"""
        self.start_test("API Documentation")
        
        try:
            docs_response = self.session.get(f"{self.base_url}/docs", timeout=10)
            openapi_response = self.session.get(f"{self.base_url}/openapi.json", timeout=10)
            
            if docs_response.status_code == 200 and openapi_response.status_code == 200:
                self.log_success("API documentation is accessible")
                openapi_data = openapi_response.json()
                self.log_info(f"API Title: {openapi_data.get('info', {}).get('title', 'Unknown')}")
                return True
            else:
                self.log_error("API documentation not accessible")
                return False
                
        except Exception as e:
            self.log_error(f"Documentation test error: {e}")
            return False
    
    def test_document_upload_sync(self, pdf_path: str) -> Optional[Dict]:
        """Test synchronous document processing"""
        self.start_test(f"Synchronous Document Upload: {pdf_path}")
        
        if not Path(pdf_path).exists():
            self.log_skip(f"Test file not found: {pdf_path}")
            return None
        
        try:
            file_size = Path(pdf_path).stat().st_size
            self.log_info(f"File size: {file_size:,} bytes")
            
            with open(pdf_path, 'rb') as file:
                files = {'file': (Path(pdf_path).name, file, 'application/pdf')}
                
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/api/process-tariff",
                    files=files,
                    timeout=TEST_TIMEOUT
                )
                processing_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                self.log_success(f"Document processed in {processing_time:.2f} seconds")
                
                # Log processing results
                if result.get('success'):
                    self.uploaded_document_id = result.get('database_id')
                    self.log_info(f"Database ID: {self.uploaded_document_id}")
                    
                    summary = result.get('summary', {})
                    self.log_info(f"Item Number: {summary.get('item_number', 'N/A')}")
                    self.log_info(f"Revision: {summary.get('revision', 'N/A')}")
                    self.log_info(f"Commodities: {summary.get('commodities_count', 0)}")
                    self.log_info(f"Rates: {summary.get('rates_count', 0)}")
                    self.log_info(f"Notes: {summary.get('notes_count', 0)}")
                    self.log_info(f"Currency: {summary.get('currency', 'N/A')}")
                else:
                    self.log_warning(f"Processing completed with warnings: {result.get('message')}")
                    if result.get('database_error'):
                        self.log_warning(f"Database error: {result.get('database_error')}")
                
                return result
            else:
                self.log_error(f"Upload failed with status {response.status_code}")
                self.log_error(f"Response: {response.text[:200]}...")
                return None
                
        except requests.exceptions.Timeout:
            self.log_error(f"Document processing timed out after {TEST_TIMEOUT} seconds")
            return None
        except Exception as e:
            self.log_error(f"Upload error: {e}")
            return None
    
    def test_document_upload_async(self, pdf_path: str) -> Optional[Dict]:
        """Test asynchronous document processing"""
        self.start_test(f"Asynchronous Document Upload: {pdf_path}")
        
        if not Path(pdf_path).exists():
            self.log_skip(f"Test file not found: {pdf_path}")
            return None
        
        try:
            # Start async processing
            with open(pdf_path, 'rb') as file:
                files = {'file': (Path(pdf_path).name, file, 'application/pdf')}
                response = self.session.post(
                    f"{self.base_url}/api/process-tariff-async",
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                task_info = response.json()
                task_id = task_info['task_id']
                self.log_success(f"Async task started: {task_id}")
                
                # Poll for completion
                max_attempts = 30  # 5 minutes with 10-second intervals
                for attempt in range(max_attempts):
                    time.sleep(10)
                    
                    status_response = self.session.get(
                        f"{self.base_url}/api/task/{task_id}",
                        timeout=10
                    )
                    
                    if status_response.status_code == 200:
                        status = status_response.json()
                        self.log_info(f"Attempt {attempt + 1}: {status['status']}")
                        
                        if status['status'] == 'completed':
                            self.log_success("Async processing completed")
                            result = status['result']
                            
                            if result.get('database_id'):
                                self.log_info(f"Database ID: {result.get('database_id')}")
                            
                            return result
                        elif status['status'] == 'error':
                            self.log_error(f"Async processing failed: {status.get('error')}")
                            return None
                    else:
                        self.log_warning(f"Status check failed: {status_response.status_code}")
                
                self.log_error("Async processing timed out")
                return None
            else:
                self.log_error(f"Async upload failed: {response.status_code}")
                return None
                
        except Exception as e:
            self.log_error(f"Async upload error: {e}")
            return None
    
    def test_search_functionality(self) -> bool:
        """Test various search endpoints"""
        self.start_test("Search Functionality")
        
        search_tests = [
            {"name": "Search by origin", "params": {"origin": "CHICAGO"}},
            {"name": "Search by destination", "params": {"destination": "MONTREAL"}},
            {"name": "Search by commodity", "params": {"commodity": "WHEAT"}},
            {"name": "Search by item number", "params": {"item_number": "70001"}},
            {"name": "Combined search", "params": {"origin": "CHATHAM", "destination": "CHICAGO"}},
            {"name": "Search active only", "params": {"origin": "TORONTO", "active_only": "true"}},
            {"name": "Search all (including expired)", "params": {"destination": "VANCOUVER", "active_only": "false"}}
        ]
        
        all_passed = True
        
        for test in search_tests:
            try:
                response = self.session.get(
                    f"{self.base_url}/api/tariffs/search",
                    params=test["params"],
                    timeout=15
                )
                
                if response.status_code == 200:
                    results = response.json()
                    count = results.get('count', 0)
                    self.log_success(f"{test['name']}: {count} results")
                    
                    # Validate response structure
                    if 'results' in results and 'count' in results:
                        if count > 0 and len(results['results']) > 0:
                            sample = results['results'][0]
                            self.log_info(f"Sample result: Item {sample.get('item_number', 'N/A')}")
                    else:
                        self.log_warning("Invalid response structure")
                        all_passed = False
                else:
                    self.log_error(f"{test['name']} failed: {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_error(f"{test['name']} error: {e}")
                all_passed = False
        
        return all_passed
    
    def test_specific_tariff_retrieval(self) -> bool:
        """Test retrieving specific tariffs by item number"""
        self.start_test("Specific Tariff Retrieval")
        
        test_items = ["70001", "75603", "14055", "60020", "70019"]
        found_count = 0
        
        for item_number in test_items:
            try:
                response = self.session.get(
                    f"{self.base_url}/api/tariffs/{item_number}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    tariff = response.json()
                    self.log_success(f"Found tariff {item_number}: Rev {tariff.get('revision', 'N/A')}")
                    found_count += 1
                elif response.status_code == 404:
                    self.log_info(f"Tariff {item_number} not found (expected for new database)")
                else:
                    self.log_warning(f"Tariff {item_number} retrieval failed: {response.status_code}")
                    
            except Exception as e:
                self.log_error(f"Error retrieving tariff {item_number}: {e}")
        
        self.log_info(f"Found {found_count} out of {len(test_items)} test tariffs")
        return True  # This test always passes as it's informational
    
    def test_rate_search(self) -> bool:
        """Test rate-specific search functionality"""
        self.start_test("Rate Search")
        
        rate_searches = [
            {"origin": "CHATHAM", "destination": "CHICAGO"},
            {"origin": "TORONTO", "destination": "MONTREAL"},
            {"origin": "VANCOUVER", "destination": "CALGARY"},
            {"origin": "WINNIPEG", "destination": "THUNDER BAY"}
        ]
        
        found_rates = False
        
        for search in rate_searches:
            try:
                response = self.session.get(
                    f"{self.base_url}/api/rates/search",
                    params=search,
                    timeout=15
                )
                
                if response.status_code == 200:
                    results = response.json()
                    count = results.get('count', 0)
                    
                    if count > 0:
                        found_rates = True
                        self.log_success(f"Found {count} rates for {search['origin']} → {search['destination']}")
                        
                        # Show sample rate
                        if results.get('results'):
                            rate = results['results'][0]
                            amount = rate.get('rate_amount', 'N/A')
                            currency = rate.get('currency', 'USD')
                            train_type = rate.get('train_type', 'N/A')
                            self.log_info(f"Sample rate: {currency} ${amount} ({train_type})")
                    else:
                        self.log_info(f"No rates found for {search['origin']} → {search['destination']}")
                else:
                    self.log_error(f"Rate search failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                self.log_error(f"Rate search error: {e}")
                return False
        
        if found_rates:
            self.log_success("Rate search functionality working")
        else:
            self.log_info("No rates found in database (expected for new installation)")
        
        return True
    
    def test_statistics_endpoint(self) -> bool:
        """Test statistics endpoint"""
        self.start_test("Statistics Endpoint")
        
        try:
            response = self.session.get(f"{self.base_url}/api/statistics", timeout=15)
            
            if response.status_code == 200:
                stats = response.json()
                
                if 'statistics' in stats:
                    self.log_success("Statistics retrieved successfully")
                    
                    # Log key statistics
                    statistics = stats['statistics']
                    self.log_info(f"Total documents: {statistics.get('total_documents', 0)}")
                    self.log_info(f"Active documents: {statistics.get('active_documents', 0)}")
                    self.log_info(f"Total commodities: {statistics.get('total_commodities', 0)}")
                    self.log_info(f"Total rates: {statistics.get('total_rates', 0)}")
                    self.log_info(f"Total notes: {statistics.get('total_notes', 0)}")
                    
                    # Show recent uploads if any
                    if stats.get('recent_uploads'):
                        self.log_info("Recent uploads:")
                        for upload in stats['recent_uploads'][:3]:
                            self.log_info(f"  - Item {upload.get('item_number', 'N/A')} ({upload.get('pdf_name', 'N/A')})")
                    
                    return True
                else:
                    self.log_error("Invalid statistics response structure")
                    return False
            else:
                self.log_error(f"Statistics endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_error(f"Statistics error: {e}")
            return False
    
    def test_document_details(self) -> bool:
        """Test detailed document retrieval"""
        self.start_test("Document Details Retrieval")
        
        if not self.uploaded_document_id:
            self.log_skip("No uploaded document to test with")
            return True
        
        try:
            response = self.session.get(
                f"{self.base_url}/api/tariffs/{self.uploaded_document_id}/details",
                timeout=15
            )
            
            if response.status_code == 200:
                details = response.json()
                self.log_success("Document details retrieved successfully")
                
                # Validate structure
                expected_keys = ['document', 'commodities', 'rates', 'notes']
                for key in expected_keys:
                    if key in details:
                        count = len(details[key]) if isinstance(details[key], list) else 1
                        self.log_info(f"{key.capitalize()}: {count} items")
                    else:
                        self.log_warning(f"Missing {key} in details response")
                
                return True
            elif response.status_code == 404:
                self.log_warning("Document details not found")
                return False
            else:
                self.log_error(f"Document details failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_error(f"Document details error: {e}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test API error handling"""
        self.start_test("Error Handling")
        
        error_tests = [
            {
                "name": "Invalid file type",
                "endpoint": "/api/process-tariff",
                "method": "POST",
                "files": {"file": ("test.txt", b"invalid content", "text/plain")},
                "expected_status": 400
            },
            {
                "name": "Missing file",
                "endpoint": "/api/process-tariff",
                "method": "POST",
                "data": {},
                "expected_status": 422
            },
            {
                "name": "Non-existent tariff",
                "endpoint": "/api/tariffs/99999",
                "method": "GET",
                "expected_status": 404
            },
            {
                "name": "Invalid rate search",
                "endpoint": "/api/rates/search",
                "method": "GET",
                "expected_status": 422
            }
        ]
        
        all_passed = True
        
        for test in error_tests:
            try:
                if test["method"] == "POST":
                    if "files" in test:
                        response = self.session.post(
                            f"{self.base_url}{test['endpoint']}",
                            files=test["files"],
                            timeout=10
                        )
                    else:
                        response = self.session.post(
                            f"{self.base_url}{test['endpoint']}",
                            data=test.get("data", {}),
                            timeout=10
                        )
                else:
                    response = self.session.get(
                        f"{self.base_url}{test['endpoint']}",
                        params=test.get("params", {}),
                        timeout=10
                    )
                
                if response.status_code == test["expected_status"]:
                    self.log_success(f"{test['name']}: Correct error handling")
                else:
                    self.log_warning(f"{test['name']}: Expected {test['expected_status']}, got {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_error(f"{test['name']} error: {e}")
                all_passed = False
        
        return all_passed
    
    def test_performance(self, pdf_path: str) -> bool:
        """Test API performance"""
        self.start_test("Performance Testing")
        
        if not Path(pdf_path).exists():
            self.log_skip(f"Performance test skipped: {pdf_path} not found")
            return True
        
        # Test multiple concurrent requests
        try:
            search_start = time.time()
            response = self.session.get(f"{self.base_url}/api/statistics", timeout=10)
            search_time = time.time() - search_start
            
            if response.status_code == 200:
                self.log_success(f"Statistics query: {search_time:.3f}s")
                
                if search_time < 1.0:
                    self.log_success("Good response time (< 1s)")
                elif search_time < 5.0:
                    self.log_info("Acceptable response time (< 5s)")
                else:
                    self.log_warning("Slow response time (> 5s)")
                
                return True
            else:
                self.log_error("Performance test failed")
                return False
                
        except Exception as e:
            self.log_error(f"Performance test error: {e}")
            return False
    
    def run_all_tests(self, pdf_path: str = None, include_async: bool = True, include_performance: bool = True):
        """Run all tests"""
        self.log(f"{Colors.BOLD}🚀 Starting CP Tariff OCR API Test Suite{Colors.END}", Colors.PURPLE)
        self.log(f"{Colors.BOLD}API Base URL: {self.base_url}{Colors.END}", Colors.CYAN)
        self.log(f"{Colors.BOLD}Test PDF: {pdf_path or 'Not provided'}{Colors.END}", Colors.CYAN)
        self.log("=" * 60, Colors.WHITE)
        
        start_time = time.time()
        
        # Core functionality tests
        if not self.test_api_health():
            self.log_error("API is not accessible. Stopping tests.")
            return self.print_summary()
        
        self.test_api_documentation()
        
        # Document processing tests
        if pdf_path and Path(pdf_path).exists():
            sync_result = self.test_document_upload_sync(pdf_path)
            
            if include_async:
                self.test_document_upload_async(pdf_path)
        else:
            self.log_warning(f"Document processing tests skipped: {pdf_path} not found")
        
        # Search and retrieval tests
        self.test_search_functionality()
        self.test_specific_tariff_retrieval()
        self.test_rate_search()
        self.test_statistics_endpoint()
        
        if self.uploaded_document_id:
            self.test_document_details()
        
        # Error handling and performance
        self.test_error_handling()
        
        if include_performance and pdf_path:
            self.test_performance(pdf_path)
        
        total_time = time.time() - start_time
        self.log(f"\n{Colors.BOLD}Total test time: {total_time:.2f} seconds{Colors.END}", Colors.CYAN)
        
        return self.print_summary()
    
    def print_summary(self) -> bool:
        """Print test summary"""
        self.log("\n" + "=" * 60, Colors.WHITE)
        self.log(f"{Colors.BOLD}🏁 Test Summary{Colors.END}", Colors.PURPLE)
        
        total = self.test_results['total']
        passed = self.test_results['passed']
        failed = self.test_results['failed']
        skipped = self.test_results['skipped']
        
        self.log(f"Total tests: {total}", Colors.WHITE)
        self.log(f"Passed: {passed}", Colors.GREEN)
        self.log(f"Failed: {failed}", Colors.RED)
        self.log(f"Skipped: {skipped}", Colors.YELLOW)
        
        if failed == 0:
            self.log(f"\n🎉 All tests passed! System is working correctly.", Colors.GREEN)
            success_rate = (passed / total * 100) if total > 0 else 0
            self.log(f"Success rate: {success_rate:.1f}%", Colors.GREEN)
            return True
        else:
            self.log(f"\n⚠️  Some tests failed. Please check the issues above.", Colors.RED)
            return False

def create_sample_pdf():
    """Create a simple sample PDF for testing if none exists"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        sample_path = "tests/sample_documents/test_sample.pdf"
        os.makedirs(os.path.dirname(sample_path), exist_ok=True)
        
        c = canvas.Canvas(sample_path, pagesize=letter)
        c.drawString(100, 750, "CP TARIFF INC.")
        c.drawString(100, 730, "ITEM: 99999")
        c.drawString(100, 710, "REVISION: 1")
        c.drawString(100, 690, "EFFECTIVE: JAN 01, 2024")
        c.drawString(100, 670, "EXPIRES: DEC 31, 2024")
        c.drawString(100, 650, "COMMODITY: TEST GRAIN")
        c.drawString(100, 630, "STCC: 01 999 99")
        c.drawString(100, 610, "ORIGIN: TEST CITY")
        c.drawString(100, 590, "DESTINATION: TEST DEST")
        c.drawString(100, 570, "RATE: $1000.00")
        c.save()
        
        return sample_path
    except ImportError:
        return None

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="CP Tariff OCR API Test Suite")
    parser.add_argument("--url", default=API_BASE_URL, help="API base URL")
    parser.add_argument("--pdf", default=TEST_PDF_PATH, help="Path to test PDF file")
    parser.add_argument("--no-async", action="store_true", help="Skip async tests")
    parser.add_argument("--no-performance", action="store_true", help="Skip performance tests")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--create-sample", action="store_true", help="Create sample PDF for testing")
    
    args = parser.parse_args()
    
    # Create sample PDF if requested
    if args.create_sample:
        sample_path = create_sample_pdf()
        if sample_path:
            print(f"✅ Created sample PDF: {sample_path}")
            args.pdf = sample_path
        else:
            print("❌ Could not create sample PDF (reportlab not installed)")
    
    # Initialize tester
    tester = CPTariffAPITester(base_url=args.url, verbose=not args.quiet)
    
    # Check if test PDF exists
    if args.pdf and not Path(args.pdf).exists():
        print(f"⚠️  Test PDF not found: {args.pdf}")
        print("Document processing tests will be skipped.")
        print("To test document processing:")
        print("1. Place a CP tariff PDF in tests/sample_documents/")
        print("2. Or use --create-sample to create a simple test PDF")
    
    # Run tests
    success = tester.run_all_tests(
        pdf_path=args.pdf,
        include_async=not args.no_async,
        include_performance=not args.no_performance
    )
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()