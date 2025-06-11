#!/usr/bin/env python3
"""
Debug and Test Script for CP Tariff OCR System
Run this to diagnose and fix common issues
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Auto-detect and add the backend directory to the path
def find_backend_path():
    """Auto-detect the correct backend path"""
    current_dir = Path(__file__).parent
    possible_paths = [
        current_dir / "ocr" / "backend",           # ocr/backend structure
        current_dir / "backend",                   # direct backend
        current_dir / "cp-tariff" / "backend",     # cp-tariff/backend
        current_dir / "cp_tariff" / "backend",     # cp_tariff/backend
    ]
    
    for path in possible_paths:
        if (path / "app" / "__init__.py").exists():
            return path
    return None

backend_path = find_backend_path()
if backend_path:
    sys.path.insert(0, str(backend_path))
    print(f"✅ Found backend at: {backend_path}")
else:
    print("❌ Could not locate backend directory")
    print("💡 Expected structure: project/ocr/backend/app/")
    sys.exit(1)

try:
    from app.database.cp_tariff_database import CPTariffDatabase
    from app.document_processor.ai_data_processor import AIDataProcessor
    from app.document_processor.ocr_engine import OCREngine
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Backend path used: {backend_path}")
    print("Make sure all required packages are installed")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CPTariffDebugger:
    """Debug and test utility for CP Tariff system"""
    
    def __init__(self):
        self.connection_string = os.getenv(
            "DB_CONNECTION_STRING",
            "DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-KL51D0H\\SQLEXPRESS;DATABASE=cp_tariff;Trusted_Connection=yes"
        )
        
    def run_all_tests(self):
        """Run comprehensive system tests"""
        print("=" * 60)
        print("CP TARIFF SYSTEM DIAGNOSTIC")
        print("=" * 60)
        print(f"Timestamp: {datetime.now()}")
        print()
        
        tests = [
            ("Environment Check", self.test_environment),
            ("Database Connection", self.test_database_connection),
            ("Database Schema", self.test_database_schema),
            ("OCR Engines", self.test_ocr_engines),
            ("AI Processor", self.test_ai_processor),
            ("Sample Data Processing", self.test_sample_data_processing),
            ("Database Operations", self.test_database_operations)
        ]
        
        results = {}
        for test_name, test_func in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = test_func()
                results[test_name] = result
                print(f"✅ {test_name}: {'PASSED' if result.get('success', False) else 'FAILED'}")
                if not result.get('success', False) and result.get('error'):
                    print(f"❌ Error: {result['error']}")
            except Exception as e:
                results[test_name] = {"success": False, "error": str(e)}
                print(f"❌ {test_name}: FAILED - {e}")
        
        self.print_summary(results)
        return results
    
    def test_environment(self):
        """Test environment setup"""
        print("Checking environment configuration...")
        
        issues = []
        
        # Check Python version
        if sys.version_info < (3, 8):
            issues.append(f"Python version {sys.version} may be too old")
        else:
            print(f"✓ Python version: {sys.version}")
        
        # Check required environment variables
        env_vars = {
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'DB_CONNECTION_STRING': os.getenv('DB_CONNECTION_STRING'),
            'DEBUG': os.getenv('DEBUG', 'False')
        }
        
        for var, value in env_vars.items():
            if value:
                print(f"✓ {var}: {'Set' if not var.startswith('OPENAI') else 'Set (hidden)'}")
            else:
                if var == 'OPENAI_API_KEY':
                    print(f"⚠ {var}: Not set (AI enhancement will be disabled)")
                else:
                    print(f"⚠ {var}: Not set (using defaults)")
        
        # Check required directories
        directories = ['./temp', './uploads', './logs']
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
            print(f"✓ Directory {directory}: Created/exists")
        
        return {
            "success": len(issues) == 0,
            "issues": issues,
            "env_vars": env_vars
        }
    
    def test_database_connection(self):
        """Test database connectivity"""
        print("Testing database connection...")
        
        try:
            db_manager = CPTariffDatabase(self.connection_string)
            test_result = db_manager.test_database_connection()
            
            print(f"Connection string valid: {test_result['connection_string_valid']}")
            print(f"Database connected: {test_result['connected']}")
            print(f"Tables exist: {test_result['tables_exist']}")
            print(f"Can write: {test_result['can_write']}")
            
            if test_result['error']:
                print(f"Error details: {test_result['error']}")
            
            return {
                "success": test_result['connected'] and test_result['tables_exist'],
                "details": test_result
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_database_schema(self):
        """Test database schema setup"""
        print("Checking database schema...")
        
        try:
            db_manager = CPTariffDatabase(self.connection_string)
            conn = db_manager.get_database_connection()
            
            if not conn:
                return {"success": False, "error": "No database connection"}
            
            cursor = conn.cursor()
            
            # Check each required table
            required_tables = ['tariff_documents', 'tariff_commodities', 'tariff_rates', 'tariff_notes']
            table_status = {}
            
            for table in required_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    table_status[table] = {"exists": True, "count": count}
                    print(f"✓ Table {table}: {count} records")
                except Exception as e:
                    table_status[table] = {"exists": False, "error": str(e)}
                    print(f"❌ Table {table}: Missing or inaccessible - {e}")
            
            conn.close()
            
            all_tables_exist = all(status["exists"] for status in table_status.values())
            
            return {
                "success": all_tables_exist,
                "table_status": table_status
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_ocr_engines(self):
        """Test OCR engine availability"""
        print("Testing OCR engines...")
        
        try:
            ocr_engine = OCREngine(use_paddle=True, use_tesseract=True)
            capabilities = ocr_engine.get_ocr_capabilities()
            
            print(f"PaddleOCR available: {capabilities['paddle_ocr']}")
            print(f"Tesseract available: {capabilities['tesseract']}")
            print(f"PDF text layer extraction: {capabilities['pdf_text_layer']}")
            print(f"Table extraction: {capabilities['table_extraction']}")
            
            engines_available = capabilities['paddle_ocr'] or capabilities['tesseract']
            
            return {
                "success": engines_available,
                "capabilities": capabilities
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_ai_processor(self):
        """Test AI processor setup"""
        print("Testing AI processor...")
        
        try:
            ai_processor = AIDataProcessor()
            
            print(f"AI enhancement available: {ai_processor.ai_available}")
            print(f"OpenAI client initialized: {ai_processor.openai_client is not None}")
            
            # Test with sample text
            sample_text = """
            CP TARIFF INC. ITEM: 16024
            REVISION: 51
            CPRS 4445-B EFFECTIVE: AUG 01, 2024
            COMMODITY: WHEAT STCC: 01 137 XX
            AB CALGARY $10,961 $11,947 0001
            """
            
            result = ai_processor.process_tariff_data(sample_text, "test.pdf", 1000)
            
            print(f"Sample processing result: {len(result)} fields extracted")
            
            return {
                "success": True,
                "ai_available": ai_processor.ai_available,
                "sample_result": result
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_sample_data_processing(self):
        """Test processing with sample data"""
        print("Testing with sample tariff data...")
        
        # Use the actual data from the JSON response
        sample_data = {
            "header": {
                "item_number": "16024",
                "revision": 51,
                "cprs_number": "4445-B",
                "effective_date": "2024-08-01",
                "expiration_date": "2025-07-31"
            },
            "commodities": [
                {
                    "name": "Wheat",
                    "stcc_code": "01137XX",
                    "description": "Wheat commodity"
                }
            ],
            "rates": [],
            "notes": [
                {
                    "type": "PROVISION",
                    "code": "",
                    "text": "EQUIPMENT: COVERED HOPPER CARS. PRIVATE EQUIPMENT IS NOT SUBJECT TO MILEAGE ALLOWANCE."
                }
            ],
            "origin_info": "Toronto On",
            "destination_info": "",
            "currency": "CAD",
            "pdf_name": "test_sample.pdf",
            "raw_text": "Sample text for testing"
        }
        
        try:
            # Validate data structure
            required_fields = ['header', 'commodities', 'rates', 'notes', 'origin_info', 'destination_info', 'currency']
            for field in required_fields:
                if field not in sample_data:
                    return {"success": False, "error": f"Missing required field: {field}"}
            
            print("✓ Sample data structure is valid")
            print(f"✓ Header: {sample_data['header']['item_number']}")
            print(f"✓ Commodities: {len(sample_data['commodities'])}")
            print(f"✓ Notes: {len(sample_data['notes'])}")
            
            return {
                "success": True,
                "sample_data": sample_data
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_database_operations(self):
        """Test database CRUD operations"""
        print("Testing database operations...")
        
        try:
            db_manager = CPTariffDatabase(self.connection_string)
            
            # Test data
            test_data = {
                "header": {
                    "item_number": f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "revision": 1,
                    "cprs_number": "TEST-001",
                    "effective_date": "2024-01-01",
                    "expiration_date": "2024-12-31"
                },
                "commodities": [
                    {
                        "name": "Test Commodity",
                        "stcc_code": "TEST123",
                        "description": "Test commodity for debugging"
                    }
                ],
                "rates": [
                    {
                        "origin": "Test Origin",
                        "destination": "Test Destination",
                        "rate_amount": "1000.00",
                        "currency": "USD"
                    }
                ],
                "notes": [
                    {
                        "type": "TEST",
                        "text": "This is a test note"
                    }
                ],
                "origin_info": "Test Origin City",
                "destination_info": "Test Destination City",
                "currency": "USD",
                "pdf_name": "debug_test.pdf",
                "raw_text": "Debug test raw text content"
            }
            
            print("Attempting to save test document...")
            doc_id = db_manager.save_document(test_data)
            
            if doc_id:
                print(f"✓ Document saved successfully with ID: {doc_id}")
                
                # Try to retrieve it
                retrieved_doc = db_manager.get_document_by_id(doc_id)
                if retrieved_doc:
                    print("✓ Document retrieved successfully")
                    return {
                        "success": True,
                        "document_id": doc_id,
                        "retrieved": True
                    }
                else:
                    return {
                        "success": False,
                        "error": "Document saved but could not be retrieved"
                    }
            else:
                return {
                    "success": False,
                    "error": "Document save returned no ID"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def print_summary(self, results):
        """Print test summary"""
        print("\n" + "="*60)
        print("DIAGNOSTIC SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in results.values() if r.get('success', False))
        total = len(results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed! Your system is ready.")
        else:
            print("\n❌ Issues found:")
            for test_name, result in results.items():
                if not result.get('success', False):
                    print(f"  • {test_name}: {result.get('error', 'Failed')}")
            
            print("\n💡 Recommended fixes:")
            if not results.get("Database Connection", {}).get("success", False):
                print("  1. Run the database setup script to create required tables")
                print("  2. Verify your SQL Server connection string")
                print("  3. Ensure SQL Server is running and accessible")
            
            if not results.get("OCR Engines", {}).get("success", False):
                print("  4. Install missing OCR dependencies:")
                print("     pip install paddleocr pytesseract pillow")
            
            if not results.get("AI Processor", {}).get("success", False):
                print("  5. Set up OpenAI API key in .env file")
        
        print("\n" + "="*60)

def main():
    """Main function"""
    debugger = CPTariffDebugger()
    
    print("Starting CP Tariff System Diagnostics...")
    print("This will test all system components and identify issues.\n")
    
    try:
        results = debugger.run_all_tests()
        
        # Save results to file
        results_file = f"debug_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nDetailed results saved to: {results_file}")
        
    except KeyboardInterrupt:
        print("\n\nDiagnostics interrupted by user.")
    except Exception as e:
        print(f"\n\nUnexpected error during diagnostics: {e}")

if __name__ == "__main__":
    main()