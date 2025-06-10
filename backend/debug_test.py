import requests
import json
import os
import sys

def debug_enhanced_ocr_api():
    """Debug the enhanced OCR API to see what's happening"""
    
    # API endpoint
    url = "http://localhost:8000/api/process-tariff"
    
    # PDF file path
    pdf_path = r"C:/Users/DELL-NTS/Downloads/CP TARIFF INC_4445 Item 16024 (2).pdf"
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return
    
    print(f"📄 Testing with file: {pdf_path}")
    print(f"📊 File size: {os.path.getsize(pdf_path):,} bytes")
    
    try:
        # Prepare the file for upload
        with open(pdf_path, 'rb') as file:
            files = {
                'file': (os.path.basename(pdf_path), file, 'application/pdf')
            }
            
            params = {
                'extract_tables': True,
                'ocr_engine': 'tesseract'
            }
            
            print("🔄 Sending request to API...")
            
            # Make the request
            response = requests.post(url, files=files, params=params, timeout=300)
            
            print(f"📡 Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ API Response received successfully")
                
                # DEBUG: Show full response structure
                print("\n🔍 DEBUGGING - FULL RESPONSE STRUCTURE:")
                print("=" * 60)
                
                # Show top-level keys
                print("📋 Top-level response keys:")
                for key in result.keys():
                    print(f"   - {key}")
                
                # Check extracted data
                extracted_data = result.get('extracted_data', {})
                print(f"\n📊 Extracted data keys: {list(extracted_data.keys())}")
                
                # Show raw text (first 500 characters)
                raw_text = extracted_data.get('raw_text', '')
                print(f"\n📝 RAW TEXT EXTRACTED (first 500 chars):")
                print("-" * 50)
                if raw_text:
                    print(f"'{raw_text[:500]}...'")
                    print(f"\nTotal raw text length: {len(raw_text)} characters")
                else:
                    print("❌ NO RAW TEXT EXTRACTED!")
                
                # Check processing metadata
                metadata = result.get('processing_metadata', {})
                print(f"\n⚙️  PROCESSING METADATA:")
                for key, value in metadata.items():
                    print(f"   {key}: {value}")
                
                # Statistics
                stats = result.get('statistics', {})
                print(f"\n📈 STATISTICS:")
                for key, value in stats.items():
                    print(f"   {key}: {value}")
                
                # Database info
                document_id = result.get('document_id')
                database_error = result.get('database_error')
                print(f"\n💾 DATABASE:")
                print(f"   Document ID: {document_id}")
                print(f"   Database Error: {database_error}")
                
                # Check if we have any data at all
                header = extracted_data.get('header', {})
                rates = extracted_data.get('rates', [])
                notes = extracted_data.get('notes', [])
                commodities = extracted_data.get('commodities', [])
                
                total_data_points = len(header) + len(rates) + len(notes) + len(commodities)
                
                if total_data_points == 0:
                    print("\n❌ PROBLEM IDENTIFIED:")
                    print("   No data extracted from the PDF!")
                    print("   This could be because:")
                    print("   1. PDF has no text layer and OCR failed")
                    print("   2. Text was extracted but parsing failed")
                    print("   3. Enhanced OCR engine has issues")
                    
                    if len(raw_text) > 100:
                        print("\n✅ Raw text WAS extracted, so parsing is the issue")
                        print("💡 Let's analyze the raw text for patterns...")
                        analyze_raw_text(raw_text)
                    else:
                        print("\n❌ Very little raw text extracted - OCR issue")
                        print("💡 Checking OCR engine status...")
                        check_ocr_engines()
                else:
                    print(f"\n✅ Some data extracted: {total_data_points} total data points")
                
                return True
                
            else:
                print(f"❌ ERROR: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_raw_text(raw_text):
    """Analyze raw text to see what patterns we can find"""
    print("\n🔍 ANALYZING RAW TEXT FOR PATTERNS:")
    print("-" * 40)
    
    # Look for common tariff patterns
    patterns_to_check = [
        ("ITEM", r"ITEM\s*:?\s*\d+"),
        ("REVISION", r"REVISION\s*:?\s*\d+"),
        ("Rates with $", r"\$\d+\.\d{2}"),
        ("STCC codes", r"\d{2}\s+\d{3}\s+\d{2}"),
        ("Location patterns", r"[A-Z]+\s+[A-Z]{2}"),
        ("TABLE patterns", r"TABLE\s+\d+"),
        ("Origin/Destination", r"ORIGIN|DESTINATION"),
        ("Commodity", r"COMMODITY"),
        ("Notes", r"NOTE\s*\d+|^\d+\."),
    ]
    
    import re
    
    print("Pattern matches found:")
    for pattern_name, pattern in patterns_to_check:
        matches = re.findall(pattern, raw_text, re.IGNORECASE | re.MULTILINE)
        if matches:
            print(f"   ✅ {pattern_name}: {len(matches)} matches - {matches[:3]}")
        else:
            print(f"   ❌ {pattern_name}: No matches")
    
    # Show first few lines
    lines = raw_text.split('\n')[:10]
    print(f"\nFirst 10 lines of extracted text:")
    for i, line in enumerate(lines, 1):
        if line.strip():
            print(f"   {i:2d}: {line.strip()}")

def check_ocr_engines():
    """Check OCR engine status"""
    try:
        response = requests.get("http://localhost:8000/debug/info", timeout=10)
        if response.status_code == 200:
            debug_info = response.json()
            print("\n🔧 OCR ENGINE STATUS:")
            ocr_engines = debug_info.get('ocr_engines', {})
            for engine, status in ocr_engines.items():
                print(f"   {engine}: {status}")
        else:
            print("❌ Cannot get debug info")
    except Exception as e:
        print(f"❌ Error checking OCR engines: {e}")

def test_direct_pdf_extraction():
    """Test direct PDF text extraction locally"""
    print("\n🧪 TESTING DIRECT PDF EXTRACTION LOCALLY:")
    print("-" * 50)
    
    pdf_path = r"C:/Users/DELL-NTS/Downloads/CP TARIFF INC_4445 Item 16024 (2).pdf"
    
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(pdf_path)
        print(f"✅ PDF opened successfully")
        print(f"   Pages: {len(doc)}")
        
        for page_num in range(min(2, len(doc))):  # Check first 2 pages
            page = doc.load_page(page_num)
            text = page.get_text()
            
            print(f"\n📄 Page {page_num + 1}:")
            print(f"   Text length: {len(text)} characters")
            
            if text.strip():
                print(f"   First 200 chars: '{text[:200]}...'")
                
                # Look for tables
                tables = page.find_tables()
                print(f"   Tables found: {len(tables)}")
                
                if tables:
                    for i, table in enumerate(tables):
                        try:
                            table_data = table.extract()
                            print(f"     Table {i+1}: {len(table_data)} rows")
                        except:
                            print(f"     Table {i+1}: Error extracting")
            else:
                print("   ❌ No text found in page")
        
        doc.close()
        
    except ImportError:
        print("❌ PyMuPDF not available - install with: pip install PyMuPDF")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🔍 ENHANCED OCR DEBUG TEST")
    print("=" * 50)
    
    # Test the API
    debug_enhanced_ocr_api()
    
    # Test direct PDF extraction
    test_direct_pdf_extraction()
    
    print("\n💡 TROUBLESHOOTING SUGGESTIONS:")
    print("1. If raw text is extracted but no data found:")
    print("   - The parsing logic needs improvement")
    print("   - Pattern matching might be too strict")
    print("2. If no raw text extracted:")
    print("   - PDF has no text layer")
    print("   - OCR engine (Tesseract) might need configuration")
    print("3. If tables found but not processed:")
    print("   - Table extraction logic needs debugging")