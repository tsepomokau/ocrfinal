import requests
import json
import os

def test_enhanced_ocr_api():
    """Test the enhanced OCR API"""
    
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
                print("✅ SUCCESS! Document processed successfully")
                
                # Display key results
                print("\n📊 EXTRACTION RESULTS:")
                print("=" * 50)
                
                # Header information
                header = result.get('extracted_data', {}).get('header', {})
                if header:
                    print("📋 HEADER:")
                    for key, value in header.items():
                        print(f"   {key}: {value}")
                
                # Statistics
                stats = result.get('statistics', {})
                print(f"\n📈 STATISTICS:")
                print(f"   Tables extracted: {stats.get('tables_extracted', 0)}")
                print(f"   Rates found: {stats.get('total_rates_found', 0)}")
                print(f"   Notes found: {stats.get('total_notes_found', 0)}")
                print(f"   Commodities found: {stats.get('total_commodities_found', 0)}")
                
                # Processing info
                processing_time = result.get('processing_time', 0)
                print(f"   Processing time: {processing_time} seconds")
                
                # Sample rates
                rates = result.get('extracted_data', {}).get('rates', [])
                if rates:
                    print(f"\n💰 SAMPLE RATES (showing first 3):")
                    for i, rate in enumerate(rates[:3]):
                        print(f"   {i+1}. {rate.get('origin', '')} → {rate.get('destination', '')} = ${rate.get('rate_amount', '')}")
                
                # Sample notes
                notes = result.get('extracted_data', {}).get('notes', [])
                if notes:
                    print(f"\n📝 SAMPLE NOTES (showing first 3):")
                    for i, note in enumerate(notes[:3]):
                        print(f"   {i+1}. [{note.get('type', '')}] {note.get('text', '')[:100]}...")
                
                # Database status
                document_id = result.get('document_id')
                if document_id:
                    print(f"\n💾 SAVED TO DATABASE with ID: {document_id}")
                else:
                    print(f"\n⚠️  Database save issue: {result.get('database_error', 'Unknown error')}")
                
                return True
                
            else:
                print(f"❌ ERROR: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except requests.exceptions.Timeout:
        print("❌ Request timed out - document processing took too long")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the API server running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_api_health():
    """Test API health first"""
    try:
        response = requests.get("http://localhost:8000/health", timeout=10)
        if response.status_code == 200:
            health = response.json()
            print("✅ API is healthy")
            
            # Check OCR engines
            ocr_info = health.get('checks', {}).get('ocr_engines', {})
            if isinstance(ocr_info, dict):
                print(f"   Tesseract: {'✅' if ocr_info.get('tesseract_available') else '❌'}")
                print(f"   PaddleOCR: {'✅' if ocr_info.get('paddle_available') else '❌'}")
            
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Enhanced OCR API Test")
    print("=" * 40)
    
    # Test health first
    if test_api_health():
        print("\n🧪 Testing document processing...")
        test_enhanced_ocr_api()
    else:
        print("❌ API is not available. Make sure the server is running:")
        print("   cd backend")
        print("   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")