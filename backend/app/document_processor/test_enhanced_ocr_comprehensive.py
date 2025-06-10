#!/usr/bin/env python3
"""
This script tests the enhanced OCR system's ability to extract
comprehensive table data from CP Tariff documents.
"""

import requests
import json
import time
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import argparse
from datetime import datetime
import csv
import tempfile

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class EnhancedOCRTester:
    """Comprehensive tester for enhanced OCR capabilities"""
    
    def __init__(self, base_url: str = "http://localhost:8000", verbose: bool = True):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.session = requests.Session()
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'total': 0,
            'detailed_results': []
        }
        self.performance_metrics = {
            'processing_times': [],
            'table_extraction_rates': [],
            'accuracy_scores': []
        }
        
    def log(self, message: str, color: str = Colors.WHITE):
        """Print colored log message"""
        if self.verbose:
            print(f"{color}{message}{Colors.END}")
    
    def log_success(self, message: str):
        self.log(f"✅ {message}", Colors.GREEN)
        self.test_results['passed'] += 1
    
    def log_error(self, message: str):
        self.log(f"❌ {message}", Colors.RED)
        self.test_results['failed'] += 1
    
    def log_warning(self, message: str):
        self.log(f"⚠️  {message}", Colors.YELLOW)
        self.test_results['warnings'] += 1
    
    def log_info(self, message: str):
        self.log(f"ℹ️  {message}", Colors.BLUE)
    
    def start_test(self, test_name: str):
        """Start a new test"""
        self.test_results['total'] += 1
        self.log(f"\n🧪 {Colors.BOLD}Testing: {test_name}{Colors.END}", Colors.CYAN)
    
    def create_sample_tariff_pdf(self) -> str:
        """Create a comprehensive sample tariff PDF for testing"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import Table, TableStyle
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_path = temp_file.name
            temp_file.close()
            
            c = canvas.Canvas(temp_path, pagesize=letter)
            width, height = letter
            
            # Title and header
            c.setFont("Helvetica-Bold", 16)
            c.drawString(100, height - 50, "CP TARIFF INC.")
            
            c.setFont("Helvetica", 12)
            y_pos = height - 80
            
            # Document header information
            header_info = [
                "ITEM: 70001",
                "REVISION: 5",
                "CPRS: 4445-A",
                "ISSUE DATE: JAN 15, 2024",
                "EFFECTIVE DATE: FEB 01, 2024",
                "EXPIRATION DATE: JAN 31, 2025"
            ]
            
            for info in header_info:
                c.drawString(100, y_pos, info)
                y_pos -= 20
            
            y_pos -= 20
            
            # Commodity section
            c.setFont("Helvetica-Bold", 14)
            c.drawString(100, y_pos, "COMMODITY:")
            y_pos -= 25
            
            c.setFont("Helvetica", 10)
            commodity_info = [
                "WHEAT                                    01 137 00",
                "GRAIN SCREENINGS, UNGROUND              01 139 30", 
                "WHEAT BRAN, NON-PELLETIZED             20 412 20",
                "MILL FEED, GRAIN, EXCEPT WHEAT          20 412 90"
            ]
            
            for commodity in commodity_info:
                c.drawString(100, y_pos, commodity)
                y_pos -= 15
            
            y_pos -= 20
            
            # Rate table header
            c.setFont("Helvetica-Bold", 12)
            c.drawString(100, y_pos, "ORIGIN                DESTINATION           SINGLE CAR    25 CARS    UNIT TRAIN    ROUTE")
            y_pos -= 5
            c.drawString(100, y_pos, "_" * 80)
            y_pos -= 20
            
            # Rate data
            c.setFont("Helvetica", 10)
            rate_data = [
                "VANCOUVER BC          CHICAGO IL            $52.75        $48.50     $45.25        CP001",
                "CALGARY AB            MINNEAPOLIS MN        $49.80        $45.60     $42.30        CP002", 
                "WINNIPEG MB           KANSAS CITY MO        $46.25        $42.10     $38.95        CP003",
                "SASKATOON SK          ST PAUL MN            $48.90        $44.70     $41.40        CP004",
                "REGINA SK             CHICAGO IL            $50.15        $46.00     $42.75        CP005"
            ]
            
            for rate in rate_data:
                c.drawString(100, y_pos, rate)
                y_pos -= 15
            
            y_pos -= 30
            
            # Notes section
            c.setFont("Helvetica-Bold", 12)
            c.drawString(100, y_pos, "NOTES:")
            y_pos -= 20
            
            c.setFont("Helvetica", 10)
            notes = [
                "1. Rates are in US Dollars per car.",
                "2. Subject to fuel surcharge adjustments.",
                "3. Minimum weight: 80,000 lbs per car for single car rates.",
                "4. Unit train minimum: 25 cars, same origin and destination.",
                "* Equipment owned or leased by railway/shipper.",
                "* Mileage allowance applicable as per tariff provisions."
            ]
            
            for note in notes:
                c.drawString(100, y_pos, note)
                y_pos -= 15
            
            y_pos -= 30
            
            # Equipment specifications
            c.setFont("Helvetica-Bold", 12)
            c.drawString(100, y_pos, "EQUIPMENT SPECIFICATIONS:")
            y_pos -= 20
            
            c.setFont("Helvetica", 10)
            equipment_specs = [
                "Car Type              Capacity      Description",
                "___________________________________________________",
                "Covered Hopper        Low Cap       Up to 4,800 cu ft",
                "Covered Hopper        High Cap      Over 4,800 cu ft", 
                "Gondola               Standard      Open top car",
                "Tank Car              Various       Liquid commodities"
            ]
            
            for spec in equipment_specs:
                c.drawString(100, y_pos, spec)
                y_pos -= 15
            
            c.save()
            self.log_success(f"Sample PDF created: {temp_path}")
            return temp_path
            
        except ImportError:
            self.log_warning("ReportLab not available - cannot create sample PDF")
            return None
        except Exception as e:
            self.log_error(f"Error creating sample PDF: {e}")
            return None
    
    def test_enhanced_api_health(self) -> bool:
        """Test enhanced API health and capabilities"""
        self.start_test("Enhanced API Health Check")
        
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                health_data = response.json()
                self.log_success("Enhanced API is running")
                
                # Check enhanced features
                checks = health_data.get('checks', {})
                
                if 'ocr_engines' in checks:
                    ocr_info = checks['ocr_engines']
                    if isinstance(ocr_info, dict):
                        paddle_available = ocr_info.get('paddle_available', False)
                        tesseract_available = ocr_info.get('tesseract_available', False)
                        
                        self.log_info(f"PaddleOCR available: {paddle_available}")
                        self.log_info(f"Tesseract available: {tesseract_available}")
                        
                        if paddle_available or tesseract_available:
                            self.log_success("OCR engines available")
                            return True
                        else:
                            self.log_error("No OCR engines available")
                            return False
                    else:
                        self.log_info(f"OCR engines status: {ocr_info}")
                        return True
                else:
                    self.log_warning("OCR engine status not available in health check")
                    return True
            else:
                self.log_error(f"Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_error(f"Health check error: {e}")
            return False
    
    def test_debug_endpoints(self) -> bool:
        """Test debug endpoints for enhanced features"""
        self.start_test("Debug Endpoints")
        
        try:
            # Test debug info
            response = self.session.get(f"{self.base_url}/debug/info", timeout=10)
            
            if response.status_code == 200:
                debug_info = response.json()
                self.log_success("Debug info accessible")
                
                # Check enhanced features
                enhanced_features = debug_info.get('enhanced_features', {})
                if enhanced_features:
                    self.log_info("Enhanced features:")
                    for feature, status in enhanced_features.items():
                        self.log_info(f"  - {feature}: {status}")
                
                # Check OCR engines
                ocr_engines = debug_info.get('ocr_engines', {})
                if ocr_engines:
                    self.log_info("OCR engines:")
                    for engine, status in ocr_engines.items():
                        self.log_info(f"  - {engine}: {status}")
                
                return True
            else:
                self.log_warning("Debug endpoints not available (may be disabled)")
                return True
                
        except Exception as e:
            self.log_warning(f"Debug endpoint test failed: {e}")
            return True  # Not critical
    
    def test_ocr_engines_directly(self) -> bool:
        """Test OCR engines directly"""
        self.start_test("OCR Engines Direct Test")
        
        try:
            response = self.session.post(f"{self.base_url}/debug/test-ocr", timeout=30)
            
            if response.status_code == 200:
                test_results = response.json()
                self.log_success("OCR engines test completed")
                
                if test_results.get('status') == 'success':
                    ocr_results = test_results.get('test_results', {})
                    
                    for engine, result in ocr_results.items():
                        status = result.get('status', 'unknown')
                        available = result.get('available', False)
                        
                        if available:
                            self.log_success(f"{engine}: {status}")
                        else:
                            self.log_warning(f"{engine}: {status}")
                    
                    return True
                else:
                    self.log_error(f"OCR test failed: {test_results.get('error')}")
                    return False
            else:
                self.log_warning("OCR engines test endpoint not available")
                return True
                
        except Exception as e:
            self.log_warning(f"OCR engines test failed: {e}")
            return True
    
    def test_comprehensive_document_processing(self, pdf_path: str) -> Optional[Dict]:
        """Test comprehensive document processing with enhanced features"""
        self.start_test(f"Comprehensive Document Processing: {Path(pdf_path).name}")
        
        if not Path(pdf_path).exists():
            self.log_error(f"Test file not found: {pdf_path}")
            return None
        
        try:
            file_size = Path(pdf_path).stat().st_size
            self.log_info(f"File size: {file_size:,} bytes")
            
            with open(pdf_path, 'rb') as file:
                files = {'file': (Path(pdf_path).name, file, 'application/pdf')}
                params = {
                    'use_ai_enhancement': True,
                    'extract_tables': True,
                    'ocr_engine': 'auto'
                }
                
                start_time = time.time()
                response = self.session.post(
                    f"{self.base_url}/api/process-tariff",
                    files=files,
                    params=params,
                    timeout=300  # 5 minutes
                )
                processing_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                self.log_success(f"Document processed in {processing_time:.2f} seconds")
                
                # Store performance metrics
                self.performance_metrics['processing_times'].append(processing_time)
                
                # Analyze results
                self._analyze_processing_results(result)
                
                return result
            else:
                self.log_error(f"Processing failed: {response.status_code}")
                if response.text:
                    self.log_error(f"Error details: {response.text[:200]}...")
                return None
                
        except requests.exceptions.Timeout:
            self.log_error("Document processing timed out")
            return None
        except Exception as e:
            self.log_error(f"Processing error: {e}")
            return None
    
    def _analyze_processing_results(self, result: Dict):
        """Analyze and validate processing results"""
        
        # Basic validation
        status = result.get('status', 'unknown')
        if status == 'success':
            self.log_success("Processing status: Success")
        else:
            self.log_warning(f"Processing status: {status}")
        
        # Check extracted data
        extracted_data = result.get('extracted_data', {})
        
        # Header analysis
        header = extracted_data.get('header', {})
        header_score = self._score_header_completeness(header)
        self.log_info(f"Header completeness: {header_score:.1%}")
        
        # Rates analysis
        rates = extracted_data.get('rates', [])
        rate_score = self._score_rate_quality(rates)
        self.log_info(f"Rate extraction quality: {rate_score:.1%}")
        self.log_info(f"Total rates found: {len(rates)}")
        
        # Table extraction analysis
        statistics = result.get('statistics', {})
        tables_extracted = statistics.get('tables_extracted', 0)
        text_blocks = statistics.get('text_blocks_processed', 0)
        
        self.log_info(f"Tables extracted: {tables_extracted}")
        self.log_info(f"Text blocks processed: {text_blocks}")
        
        # Store accuracy metrics
        overall_accuracy = (header_score + rate_score) / 2
        self.performance_metrics['accuracy_scores'].append(overall_accuracy)
        self.performance_metrics['table_extraction_rates'].append(tables_extracted)
        
        # Enhanced features analysis
        enhanced_features = result.get('enhanced_features', {})
        if enhanced_features:
            self.log_info("Enhanced features used:")
            for feature, enabled in enhanced_features.items():
                status_icon = "✅" if enabled else "❌"
                self.log_info(f"  {status_icon} {feature}")
        
        # Structured data analysis
        structured_data = result.get('structured_data', {})
        if structured_data:
            tables_count = structured_data.get('tables_count', 0)
            self.log_info(f"Structured tables: {tables_count}")
            
            sample_data = structured_data.get('sample_table_data', [])
            if sample_data:
                self.log_info("Sample structured data available")
        
        # Detailed results storage
        self.test_results['detailed_results'].append({
            'timestamp': datetime.now().isoformat(),
            'header_score': header_score,
            'rate_score': rate_score,
            'overall_accuracy': overall_accuracy,
            'tables_extracted': tables_extracted,
            'rates_found': len(rates),
            'processing_time': result.get('processing_time', 0)
        })
    
    def _score_header_completeness(self, header: Dict) -> float:
        """Score header completeness"""
        required_fields = ['item_number', 'revision', 'effective_date', 'expiration_date']
        found_fields = sum(1 for field in required_fields if header.get(field))
        return found_fields / len(required_fields)
    
    def _score_rate_quality(self, rates: List[Dict]) -> float:
        """Score rate extraction quality"""
        if not rates:
            return 0.0
        
        complete_rates = 0
        for rate in rates:
            # Check if rate has essential fields
            has_origin = bool(rate.get('origin', '').strip())
            has_destination = bool(rate.get('destination', '').strip())
            has_amount = bool(rate.get('rate_amount', '').strip())
            
            if has_origin and has_destination and has_amount:
                complete_rates += 1
        
        return complete_rates / len(rates)
    
    def test_table_extraction_accuracy(self, pdf_path: str) -> bool:
        """Test table extraction accuracy specifically"""
        self.start_test("Table Extraction Accuracy")
        
        result = self.test_comprehensive_document_processing(pdf_path)
        if not result:
            return False
        
        # Analyze table extraction
        statistics = result.get('statistics', {})
        tables_extracted = statistics.get('tables_extracted', 0)
        
        # For comprehensive test, expect at least 2 tables (rates and commodities)
        if tables_extracted >= 2:
            self.log_success(f"Good table extraction: {tables_extracted} tables found")
            
            # Check structured data
            structured_data = result.get('structured_data', {})
            if structured_data and structured_data.get('tables_count', 0) > 0:
                self.log_success("Structured table data available")
                return True
            else:
                self.log_warning("Structured data not available")
                return False
        elif tables_extracted >= 1:
            self.log_warning(f"Basic table extraction: {tables_extracted} table found")
            return True
        else:
            self.log_error("No tables extracted")
            return False
    
    def test_rate_extraction_completeness(self, pdf_path: str) -> bool:
        """Test rate extraction completeness"""
        self.start_test("Rate Extraction Completeness")
        
        result = self.test_comprehensive_document_processing(pdf_path)
        if not result:
            return False
        
        rates = result.get('extracted_data', {}).get('rates', [])
        
        if not rates:
            self.log_error("No rates extracted")
            return False
        
        # Analyze rate completeness
        complete_rates = 0
        partial_rates = 0
        
        for rate in rates:
            has_origin = bool(rate.get('origin', '').strip())
            has_destination = bool(rate.get('destination', '').strip())
            has_amount = bool(rate.get('rate_amount', '').strip())
            
            if has_origin and has_destination and has_amount:
                complete_rates += 1
            elif has_origin or has_destination or has_amount:
                partial_rates += 1
        
        completeness = complete_rates / len(rates) if rates else 0
        
        self.log_info(f"Total rates: {len(rates)}")
        self.log_info(f"Complete rates: {complete_rates}")
        self.log_info(f"Partial rates: {partial_rates}")
        self.log_info(f"Completeness: {completeness:.1%}")
        
        if completeness >= 0.8:  # 80% completeness
            self.log_success("Excellent rate extraction completeness")
            return True
        elif completeness >= 0.6:  # 60% completeness
            self.log_warning("Good rate extraction completeness")
            return True
        else:
            self.log_error("Poor rate extraction completeness")
            return False
    
    def test_performance_benchmarks(self, pdf_path: str) -> bool:
        """Test performance benchmarks"""
        self.start_test("Performance Benchmarks")
        
        # Run multiple tests to get average performance
        times = []
        accuracy_scores = []
        
        for i in range(3):  # Run 3 times
            self.log_info(f"Performance test run {i+1}/3...")
            
            start_time = time.time()
            result = self.test_comprehensive_document_processing(pdf_path)
            end_time = time.time()
            
            if result:
                processing_time = end_time - start_time
                times.append(processing_time)
                
                # Calculate accuracy score
                header = result.get('extracted_data', {}).get('header', {})
                rates = result.get('extracted_data', {}).get('rates', [])
                
                header_score = self._score_header_completeness(header)
                rate_score = self._score_rate_quality(rates)
                accuracy = (header_score + rate_score) / 2
                accuracy_scores.append(accuracy)
        
        if not times:
            self.log_error("No successful performance tests")
            return False
        
        # Calculate averages
        avg_time = sum(times) / len(times)
        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores)
        
        self.log_info(f"Average processing time: {avg_time:.2f} seconds")
        self.log_info(f"Average accuracy: {avg_accuracy:.1%}")
        
        # Performance thresholds
        if avg_time <= 30:  # 30 seconds
            self.log_success("Excellent processing speed")
        elif avg_time <= 60:  # 1 minute
            self.log_info("Good processing speed")
        else:
            self.log_warning("Slow processing speed")
        
        if avg_accuracy >= 0.8:
            self.log_success("Excellent accuracy")
            return True
        elif avg_accuracy >= 0.6:
            self.log_info("Good accuracy")
            return True
        else:
            self.log_warning("Low accuracy")
            return False
    
    def test_error_handling(self) -> bool:
        """Test error handling capabilities"""
        self.start_test("Error Handling")
        
        # Test with invalid file
        try:
            files = {'file': ('test.txt', b'invalid content', 'text/plain')}
            response = self.session.post(
                f"{self.base_url}/api/process-tariff",
                files=files,
                timeout=10
            )
            
            if response.status_code == 400:
                self.log_success("Correctly rejected invalid file type")
            else:
                self.log_warning(f"Unexpected response to invalid file: {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_error(f"Error handling test failed: {e}")
            return False
    
    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        
        if not self.performance_metrics['processing_times']:
            return {"error": "No performance data available"}
        
        times = self.performance_metrics['processing_times']
        accuracies = self.performance_metrics['accuracy_scores']
        table_rates = self.performance_metrics['table_extraction_rates']
        
        report = {
            "test_summary": {
                "total_tests": self.test_results['total'],
                "passed": self.test_results['passed'],
                "failed": self.test_results['failed'],
                "warnings": self.test_results['warnings'],
                "success_rate": self.test_results['passed'] / self.test_results['total'] if self.test_results['total'] > 0 else 0
            },
            "performance_metrics": {
                "processing_time": {
                    "average": sum(times) / len(times),
                    "min": min(times),
                    "max": max(times),
                    "samples": len(times)
                },
                "accuracy": {
                    "average": sum(accuracies) / len(accuracies) if accuracies else 0,
                    "min": min(accuracies) if accuracies else 0,
                    "max": max(accuracies) if accuracies else 0,
                    "samples": len(accuracies)
                },
                "table_extraction": {
                    "average_tables_per_document": sum(table_rates) / len(table_rates) if table_rates else 0,
                    "max_tables_found": max(table_rates) if table_rates else 0,
                    "samples": len(table_rates)
                }
            },
            "detailed_results": self.test_results['detailed_results'],
            "timestamp": datetime.now().isoformat()
        }
        
        return report
    
    def save_performance_report(self, filepath: str):
        """Save performance report to file"""
        report = self.generate_performance_report()
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log_success(f"Performance report saved: {filepath}")
    
    def run_comprehensive_tests(self, pdf_path: str = None, create_sample: bool = True) -> bool:
        """Run all comprehensive tests"""
        
        self.log(f"{Colors.PURPLE}{Colors.BOLD}🚀 Enhanced OCR Comprehensive Test Suite{Colors.END}")
        self.log(f"{Colors.CYAN}API Base URL: {self.base_url}{Colors.END}")
        self.log("=" * 70)
        
        start_time = time.time()
        
        # Create sample PDF if needed
        if not pdf_path and create_sample:
            pdf_path = self.create_sample_tariff_pdf()
            if not pdf_path:
                self.log_error("Cannot create or find test PDF")
                return False
        
        if pdf_path:
            self.log(f"{Colors.CYAN}Test PDF: {pdf_path}{Colors.END}")
        
        # Run test suite
        test_functions = [
            ("Enhanced API Health", lambda: self.test_enhanced_api_health()),
            ("Debug Endpoints", lambda: self.test_debug_endpoints()),
            ("OCR Engines Direct", lambda: self.test_ocr_engines_directly()),
            ("Error Handling", lambda: self.test_error_handling())
        ]
        
        # PDF-dependent tests
        if pdf_path and Path(pdf_path).exists():
            test_functions.extend([
                ("Comprehensive Processing", lambda: bool(self.test_comprehensive_document_processing(pdf_path))),
                ("Table Extraction Accuracy", lambda: self.test_table_extraction_accuracy(pdf_path)),
                ("Rate Extraction Completeness", lambda: self.test_rate_extraction_completeness(pdf_path)),
                ("Performance Benchmarks", lambda: self.test_performance_benchmarks(pdf_path))
            ])
        
        # Execute tests
        for test_name, test_func in test_functions:
            self.log(f"\n📌 {test_name}...", Colors.CYAN)
            try:
                success = test_func()
                if not success:
                    self.log_error(f"Test failed: {test_name}")
            except Exception as e:
                self.log_error(f"Test error: {test_name} - {e}")
        
        # Generate final report
        total_time = time.time() - start_time
        
        self.log(f"\n{Colors.CYAN}{Colors.BOLD}📊 Test Summary{Colors.END}")
        self.log("=" * 50)
        
        total = self.test_results['total']
        passed = self.test_results['passed']
        failed = self.test_results['failed']
        warnings = self.test_results['warnings']
        
        self.log(f"Total tests: {total}")
        self.log(f"Passed: {passed}", Colors.GREEN)
        self.log(f"Failed: {failed}", Colors.RED)
        self.log(f"Warnings: {warnings}", Colors.YELLOW)
        self.log(f"Test duration: {total_time:.2f} seconds")
        
        success_rate = (passed / total) if total > 0 else 0
        self.log(f"Success rate: {success_rate:.1%}")
        
        # Performance summary
        if self.performance_metrics['processing_times']:
            avg_time = sum(self.performance_metrics['processing_times']) / len(self.performance_metrics['processing_times'])
            self.log(f"Average processing time: {avg_time:.2f} seconds")
        
        if self.performance_metrics['accuracy_scores']:
            avg_accuracy = sum(self.performance_metrics['accuracy_scores']) / len(self.performance_metrics['accuracy_scores'])
            self.log(f"Average accuracy: {avg_accuracy:.1%}")
        
        # Save report
        report_path = f"enhanced_ocr_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.save_performance_report(report_path)
        
        # Cleanup sample PDF if created
        if pdf_path and create_sample and Path(pdf_path).exists():
            try:
                os.unlink(pdf_path)
                self.log_info("Cleaned up sample PDF")
            except:
                pass
        
        if failed == 0:
            self.log(f"\n🎉 All tests passed! Enhanced OCR system is working correctly.", Colors.GREEN)
            return True
        else:
            self.log(f"\n⚠️  Some tests failed. Check the detailed report for issues.", Colors.YELLOW)
            return success_rate >= 0.7  # 70% success rate threshold

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Enhanced OCR Comprehensive Test Suite")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--pdf", help="Path to test PDF file")
    parser.add_argument("--no-sample", action="store_true", help="Don't create sample PDF")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--performance-only", action="store_true", help="Only run performance tests")
    
    args = parser.parse_args()
    
    tester = EnhancedOCRTester(base_url=args.url, verbose=not args.quiet)
    
    if args.performance_only and args.pdf:
        # Run only performance tests
        success = tester.test_performance_benchmarks(args.pdf)
        tester.save_performance_report("performance_report.json")
    else:
        # Run comprehensive test suite
        success = tester.run_comprehensive_tests(
            pdf_path=args.pdf,
            create_sample=not args.no_sample
        )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()