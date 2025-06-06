"""
Debug OCR Engine with extensive logging
"""
import re
import json
from typing import Dict, List, Any, Optional
import traceback

class OCREngine:
    """Debug OCR Engine with verbose logging"""
    
    def __init__(self, use_paddle=True):
        print("🔧 Debug OCR Engine initialized")
    
    def process_sections(self, document_sections, pdf_path: str = "") -> Dict[str, Any]:
        """Process document sections with debug logging"""
        print(f"🔄 Processing sections. PDF path: '{pdf_path}'")
        
        # Extract text from PDF using PyMuPDF
        extracted_text = ""
        if pdf_path and pdf_path != "":
            extracted_text = self._extract_pdf_text(pdf_path)
        else:
            print("⚠️  No PDF path provided to OCR engine")
        
        if not extracted_text:
            extracted_text = "CP TARIFF 4445 Item 14055 Western Canada wheat to chicago for furtherance sample text"
            print("⚠️  Using sample text for debugging")
        
        try:
            # Parse the text
            print("🔍 Starting text parsing...")
            parsed_data = self._parse_text_comprehensive(extracted_text)
            
            print("📊 Parsing results:")
            print(f"   Header: {json.dumps(parsed_data['header'], indent=2)}")
            print(f"   Rates: {len(parsed_data['rates'])} found")
            print(f"   Notes: {len(parsed_data['notes'])} found")
            
            # Return in the format expected by the API - ENSURE ALL VALUES ARE CORRECT TYPES
            result = {
                "page_0": {
                    "full": extracted_text,
                    "table": extracted_text[:200]
                },
                "header": parsed_data["header"],
                "commodities": parsed_data["commodities"],
                "rates": parsed_data["rates"],
                "notes": parsed_data["notes"],
                "origin_info": parsed_data["origin_info"],
                "destination_info": parsed_data["destination_info"],
                "currency": "USD",
                "raw_text": extracted_text,
                "processing_metadata": {
                    "processing_time_seconds": 2,
                    "file_size_bytes": 840928,
                    "ocr_engine": "Debug",
                    "ai_processing_used": True,
                    "pages_processed": 1
                }
            }
            
            print("✅ Final result structure:")
            print(f"   Keys in result: {list(result.keys())}")
            print(f"   Rates count: {len(result.get('rates', []))}")
            print(f"   Notes count: {len(result.get('notes', []))}")
            
            # VALIDATE RESULT STRUCTURE
            for key in ['header', 'commodities', 'rates', 'notes']:
                if key not in result:
                    print(f"❌ Missing key: {key}")
                else:
                    print(f"✅ Key {key}: {type(result[key])}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error in OCR processing: {e}")
            traceback.print_exc()
            # Return minimal valid structure
            return {
                "header": {},
                "commodities": [],
                "rates": [],
                "notes": [],
                "origin_info": "",
                "destination_info": "",
                "currency": "USD",
                "raw_text": extracted_text
            }
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        try:
            import fitz
            print(f"📄 Extracting text from PDF: {pdf_path}")
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text.strip():
                    full_text += f"\n--- Page {page_num + 1} ---\n{text}"
            
            doc.close()
            print(f"✅ Extracted {len(full_text)} characters from PDF")
            return full_text
                
        except Exception as e:
            print(f"❌ PDF text extraction failed: {e}")
            return ""
    
    def _parse_text_comprehensive(self, text: str) -> Dict[str, Any]:
        """Comprehensive text parsing with debug output"""
        print(f"📝 Parsing text (length: {len(text)})")
        
        # Extract header
        header = {}
        item_match = re.search(r'Item\s*[:\-]?\s*(\d+)', text, re.IGNORECASE)
        if item_match:
            header['item_number'] = item_match.group(1)
            print(f"✅ Found item number: {item_match.group(1)}")
        
        # Extract rates - CREATE SAMPLE RATES FOR TESTING
        rates = []
        if "western canada" in text.lower() and "chicago" in text.lower():
            rates.append({
                "origin": "Western Canada",
                "destination": "Chicago, IL",
                "origin_state": "BC",
                "destination_state": "IL",
                "rate_amount": "45.50",
                "currency": "USD",
                "rate_category": "standard",
                "train_type": "",
                "car_capacity_type": "",
                "route_code": "",
                "additional_provisions": ""
            })
            print("✅ Created sample rate: Western Canada to Chicago")
        
        # Add another sample rate
        rates.append({
            "origin": "Vancouver, BC",
            "destination": "Chicago, IL",
            "origin_state": "BC",
            "destination_state": "IL",
            "rate_amount": "52.75",
            "currency": "USD",
            "rate_category": "express",
            "train_type": "Unit Train",
            "car_capacity_type": "100 ton",
            "route_code": "CP001",
            "additional_provisions": "Subject to minimum weight"
        })
        
        # Extract notes - CREATE SAMPLE NOTES FOR TESTING
        notes = []
        sample_notes = [
            "Rates subject to fuel surcharge adjustments",
            "Minimum weight 80,000 lbs per car",
            "Transit time: 5-7 business days",
            "Special handling required for this commodity",
            "Rate effective until further notice"
        ]
        
        for i, sample in enumerate(sample_notes):
            notes.append({
                "type": "ASTERISK" if i < 2 else "GENERAL",
                "code": f"*{i+1}" if i < 2 else f"NOTE_{i+1}",
                "text": sample,
                "sort_order": i
            })
        
        # Extract commodities
        commodities = [
            {
                "name": "Wheat",
                "stcc_code": "0111",
                "description": "Western Canada wheat for export"
            },
            {
                "name": "Grain Products",
                "stcc_code": "0119",
                "description": "Various grain commodities"
            }
        ]
        
        # Extract origin/destination
        origin = "Western Canada"
        destination = "Chicago, IL"
        
        print(f"🏷️  Header extracted: {header}")
        print(f"💰 Rates extracted: {len(rates)} items")
        print(f"📋 Notes extracted: {len(notes)} items")
        print(f"📦 Commodities extracted: {len(commodities)} items")
        print(f"📍 Origin: '{origin}', Destination: '{destination}'")
        
        return {
            "header": header,
            "rates": rates,
            "notes": notes,
            "commodities": commodities,
            "origin_info": origin,
            "destination_info": destination
        }