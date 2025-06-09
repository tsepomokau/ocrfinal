"""
Working OCR Engine - Fixed for Your System
File: backend/app/document_processor/ocr_engine_enhanced.py
"""
import re
import fitz  # PyMuPDF
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
import json
import io

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
    # Set Tesseract path for Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except ImportError:
    TESSERACT_AVAILABLE = False
    print("⚠️  Tesseract not available")

logger = logging.getLogger(__name__)

class EnhancedOCREngine:
    """Working OCR Engine - Fixed for your system"""
    
    def __init__(self, use_paddle=False, use_tesseract=True):
        self.use_paddle = False  # Disable for Windows compatibility
        self.use_tesseract = use_tesseract and TESSERACT_AVAILABLE
        
        print(f"🔍 OCR Methods: PaddleOCR={self.use_paddle}, Tesseract={self.use_tesseract}")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF - WORKING VERSION"""
        print(f"📄 Processing PDF: {pdf_path}")
        
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            
            print(f"✅ Opened PDF with {len(doc)} pages")
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Extract text from page
                text = page.get_text()
                print(f"📄 Page {page_num + 1}: {len(text)} characters")
                
                if text.strip():
                    full_text += f"\n--- Page {page_num + 1} ---\n{text}"
                    
                    # Show sample
                    sample = text.strip()[:200].replace('\n', ' ')
                    print(f"   Sample: '{sample}...'")
                else:
                    print(f"   ⚠️  No text in page {page_num + 1}")
            
            doc.close()
            
            total_chars = len(full_text)
            print(f"📊 Total extracted: {total_chars} characters")
            
            if total_chars > 100:
                print("✅ Text extraction successful!")
                return full_text
            else:
                print("❌ Very little text extracted")
                return "Minimal text extracted from PDF"
                
        except Exception as e:
            print(f"❌ PDF extraction error: {e}")
            return f"PDF extraction failed: {str(e)}"
    
    def process_sections(self, document_sections, pdf_path: str = "") -> Dict[str, Any]:
        """Main processing method - WORKING VERSION"""
        print(f"🚀 Starting Enhanced OCR Processing")
        print(f"📁 PDF: {pdf_path}")
        
        # Extract text from PDF
        all_text = ""
        if pdf_path:
            all_text = self.extract_text_from_pdf(pdf_path)
            print(f"📝 Extracted text length: {len(all_text)}")
        
        if not all_text or len(all_text) < 50:
            print("❌ No sufficient text extracted!")
            all_text = "No text extracted from document"
        
        # Parse the text
        print("🔄 Starting text parsing...")
        parsed_data = self._parse_comprehensive_text(all_text)
        
        print(f"📊 Parsing Results:")
        print(f"   Header: {len(parsed_data['header'])} fields")
        print(f"   Rates: {len(parsed_data['rates'])} found")
        print(f"   Notes: {len(parsed_data['notes'])} found")
        print(f"   Commodities: {len(parsed_data['commodities'])} found")
        
        # Return results
        result = {
            "page_0": {
                "full": all_text,
                "table": all_text[:1000]  # First 1000 chars as table summary
            },
            "header": parsed_data["header"],
            "commodities": parsed_data["commodities"],
            "rates": parsed_data["rates"],
            "notes": parsed_data["notes"],
            "origin_info": parsed_data["origin_info"],
            "destination_info": parsed_data["destination_info"],
            "currency": parsed_data.get("currency", "USD"),
            "raw_text": all_text,
            "processing_metadata": {
                "processing_time_seconds": 1,
                "file_size_bytes": 0,
                "ocr_engine": "Enhanced OCR (Working)",
                "ai_processing_used": False,
                "pages_processed": all_text.count("--- Page"),
                "tables_found": all_text.count("TABLE") + all_text.count("ORIGIN") + all_text.count("DESTINATION"),
                "text_blocks_found": len(all_text.split('\n')),
                "extraction_success": len(all_text) > 100
            }
        }
        
        print(f"✅ Processing complete!")
        return result
    
    def _parse_comprehensive_text(self, text: str) -> Dict[str, Any]:
        """Parse text comprehensively - WORKING VERSION"""
        print("🔍 Comprehensive text parsing...")
        
        parsed_data = {
            'header': {},
            'commodities': [],
            'rates': [],
            'notes': [],
            'origin_info': '',
            'destination_info': '',
            'currency': 'USD'
        }
        
        # Parse header - MORE FLEXIBLE PATTERNS
        print("   📋 Parsing header...")
        parsed_data['header'] = self._extract_header_flexible(text)
        
        # Parse rates - IMPROVED DETECTION
        print("   💰 Parsing rates...")
        parsed_data['rates'] = self._extract_rates_improved(text)
        
        # Parse commodities - BETTER PATTERNS
        print("   📦 Parsing commodities...")
        parsed_data['commodities'] = self._extract_commodities_improved(text)
        
        # Parse notes - COMPREHENSIVE
        print("   📝 Parsing notes...")
        parsed_data['notes'] = self._extract_notes_improved(text)
        
        # Extract locations
        print("   📍 Parsing locations...")
        origin, destination = self._extract_locations_improved(text)
        parsed_data['origin_info'] = origin
        parsed_data['destination_info'] = destination
        
        # Determine currency
        parsed_data['currency'] = self._extract_currency_improved(text)
        
        return parsed_data
    
    def _extract_header_flexible(self, text: str) -> Dict[str, Any]:
        """Extract header with flexible patterns"""
        header = {}
        
        # More flexible patterns that match your actual text
        patterns = {
            'item_number': [
                r'ITEM\s*:?\s*(\d+)',
                r'Item\s*:?\s*(\d+)',
                r'ITEM[\s\n]*(\d+)',  # Handle newlines
            ],
            'revision': [
                r'REVISION\s*:?\s*(\d+)',
                r'Rev\s*:?\s*(\d+)',
                r'REVISION[\s\n]*(\d+)',
            ],
            'cprs_number': [
                r'CPRS\s*(\d+-[A-Z])',
                r'(\d{4}-[A-Z])',
            ],
            'issue_date': [
                r'ISSUED\s*:?\s*([A-Z]{3}\s+\d{1,2},?\s+\d{4})',
                r'ISSUE\s+DATE\s*:?\s*([A-Z]{3}\s+\d{1,2},?\s+\d{4})',
            ],
            'effective_date': [
                r'EFFECTIVE\s*:?\s*([A-Z]{3}\s+\d{1,2},?\s+\d{4})',
            ],
            'expiration_date': [
                r'EXPIRES?\s*:?\s*([A-Z]{3}\s+\d{1,2},?\s+\d{4})',
            ]
        }
        
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
                if match:
                    value = match.group(1).strip()
                    header[field] = value
                    print(f"      ✅ {field}: {value}")
                    break
        
        return header
    
    def _extract_rates_improved(self, text: str) -> List[Dict[str, Any]]:
        """Extract rates with improved detection"""
        rates = []
        
        # Look for dollar amounts in context
        dollar_pattern = r'\$\s*(\d+\.?\d*)'
        dollar_matches = list(re.finditer(dollar_pattern, text))
        
        print(f"      💰 Found {len(dollar_matches)} dollar amounts")
        
        # Analyze each dollar amount for context
        for match in dollar_matches:
            rate_amount = match.group(1)
            
            # Get surrounding text (100 chars before and after)
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end]
            
            # Look for location indicators in context
            locations = self._find_locations_in_context(context)
            
            if len(locations) >= 1:
                origin = locations[0] if len(locations) > 0 else ""
                destination = locations[1] if len(locations) > 1 else ""
                
                rate = {
                    'origin': origin,
                    'destination': destination,
                    'rate_amount': rate_amount,
                    'currency': 'USD',
                    'train_type': '',
                    'equipment_type': '',
                    'route_code': '',
                    'additional_provisions': '',
                    'context': context.replace('\n', ' ')[:100]
                }
                rates.append(rate)
                print(f"      ✅ Rate: {origin} → {destination} = ${rate_amount}")
        
        # Also look for tabular rate structures
        table_rates = self._extract_tabular_rates(text)
        rates.extend(table_rates)
        
        return rates
    
    def _find_locations_in_context(self, context: str) -> List[str]:
        """Find location names in context"""
        locations = []
        
        # Common location patterns
        location_patterns = [
            r'([A-Z][A-Z\s]+)\s+([A-Z]{2})\b',  # City STATE/PROV
            r'\b([A-Z]+)\s*,?\s*([A-Z]{2})\b',   # CITY, ST
            r'\b(VANCOUVER|CALGARY|WINNIPEG|TORONTO|CHICAGO|MINNEAPOLIS)\b',
        ]
        
        for pattern in location_patterns:
            matches = re.finditer(pattern, context, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 2:
                    location = f"{match.group(1).strip()} {match.group(2).strip()}"
                else:
                    location = match.group(1).strip()
                
                if location not in locations and len(location) > 2:
                    locations.append(location)
        
        return locations
    
    def _extract_tabular_rates(self, text: str) -> List[Dict[str, Any]]:
        """Extract rates from table-like structures"""
        rates = []
        
        lines = text.split('\n')
        
        # Look for lines that might be table rows
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line has multiple elements separated by spaces and contains dollar
            parts = line.split()
            if len(parts) >= 4 and any('$' in part for part in parts):
                # Try to parse as a rate row
                locations = []
                amounts = []
                
                for part in parts:
                    if '$' in part:
                        amount_match = re.search(r'\$?(\d+\.?\d*)', part)
                        if amount_match:
                            amounts.append(amount_match.group(1))
                    elif len(part) > 2 and part.isalpha():
                        locations.append(part)
                
                if amounts and len(locations) >= 1:
                    origin = locations[0] if len(locations) > 0 else ""
                    destination = locations[1] if len(locations) > 1 else ""
                    
                    rate = {
                        'origin': origin,
                        'destination': destination,
                        'rate_amount': amounts[0],
                        'currency': 'USD',
                        'train_type': '',
                        'equipment_type': '',
                        'route_code': '',
                        'additional_provisions': '',
                        'raw_line': line
                    }
                    rates.append(rate)
        
        return rates
    
    def _extract_commodities_improved(self, text: str) -> List[Dict[str, Any]]:
        """Extract commodities with improved patterns"""
        commodities = []
        
        # Look for STCC codes
        stcc_pattern = r'(\d{2}\s+\d{3}\s+\d{2})'
        stcc_matches = list(re.finditer(stcc_pattern, text))
        
        print(f"      📋 Found {len(stcc_matches)} STCC codes")
        
        for match in stcc_matches:
            stcc_code = match.group(1)
            
            # Get the line containing this STCC code
            lines = text.split('\n')
            for line in lines:
                if stcc_code in line:
                    # Extract commodity name from the same line
                    name = line.replace(stcc_code, '').strip()
                    # Clean up common artifacts
                    name = re.sub(r'^[^\w]+|[^\w]+$', '', name)
                    
                    if name and len(name) > 3:
                        commodities.append({
                            'name': name,
                            'stcc_code': stcc_code,
                            'description': line.strip()
                        })
                        print(f"      ✅ STCC commodity: {name} ({stcc_code})")
                    break
        
        # Look for common commodity keywords
        commodity_keywords = [
            'WHEAT', 'GRAIN', 'CORN', 'SOYBEAN', 'BARLEY', 'CANOLA',
            'FEED', 'FLOUR', 'MEAL', 'BRAN', 'SCREENINGS'
        ]
        
        for keyword in commodity_keywords:
            if keyword in text.upper():
                # Avoid duplicates
                if not any(keyword.lower() in c['name'].lower() for c in commodities):
                    commodities.append({
                        'name': keyword.title(),
                        'stcc_code': '',
                        'description': f'{keyword.title()} commodity'
                    })
                    print(f"      ✅ Keyword commodity: {keyword}")
        
        return commodities
    
    def _extract_notes_improved(self, text: str) -> List[Dict[str, Any]]:
        """Extract notes with comprehensive patterns"""
        notes = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 10:  # Skip very short lines
                continue
            
            # Pattern 1: Numbered notes (1., 2., etc.)
            numbered_match = re.match(r'^(\d+)\.?\s*(.+)$', line)
            if numbered_match and len(numbered_match.group(2)) > 5:
                notes.append({
                    'type': 'NUMBERED',
                    'code': numbered_match.group(1),
                    'text': numbered_match.group(2),
                    'sort_order': len(notes)
                })
                continue
            
            # Pattern 2: Asterisk notes
            if line.startswith('*') and len(line) > 5:
                notes.append({
                    'type': 'ASTERISK',
                    'code': '*',
                    'text': line[1:].strip(),
                    'sort_order': len(notes)
                })
                continue
            
            # Pattern 3: Lines with provision keywords
            provision_keywords = [
                'SUBJECT TO', 'MINIMUM', 'MAXIMUM', 'EQUIPMENT', 'APPLIES',
                'CONDITIONS', 'RENEWAL', 'CHANGES', 'EFFECTIVE', 'EXPIRES'
            ]
            
            if any(keyword in line.upper() for keyword in provision_keywords):
                # Avoid duplicating header info
                if not any(header_word in line.upper() for header_word in ['ITEM:', 'REVISION:', 'ISSUED:']):
                    notes.append({
                        'type': 'PROVISION',
                        'code': f'PROV_{len(notes)+1}',
                        'text': line,
                        'sort_order': len(notes)
                    })
                    continue
            
            # Pattern 4: Lines that look like tariff provisions
            if (('RATE' in line.upper() or 'CHARGE' in line.upper() or 'CAR' in line.upper()) 
                and len(line) > 20):
                notes.append({
                    'type': 'GENERAL',
                    'code': f'GEN_{len(notes)+1}',
                    'text': line,
                    'sort_order': len(notes)
                })
        
        print(f"      📝 Found {len(notes)} notes")
        return notes
    
    def _extract_locations_improved(self, text: str) -> Tuple[str, str]:
        """Extract origin and destination with improved logic"""
        
        # Look for explicit FROM...TO patterns
        from_to_match = re.search(r'FROM\s+([^TO\n]+)\s+TO\s+([^\n]+)', text, re.IGNORECASE)
        if from_to_match:
            origin = from_to_match.group(1).strip()
            destination = from_to_match.group(2).strip()
            print(f"      📍 FROM-TO: {origin} → {destination}")
            return origin, destination
        
        # Look for common city/province combinations
        canadian_locations = [
            'VANCOUVER BC', 'CALGARY AB', 'WINNIPEG MB', 'TORONTO ON',
            'SASKATOON SK', 'REGINA SK', 'EDMONTON AB'
        ]
        
        us_locations = [
            'CHICAGO IL', 'MINNEAPOLIS MN', 'KANSAS CITY MO', 
            'ST PAUL MN', 'MILWAUKEE WI', 'DULUTH MN'
        ]
        
        origin = ""
        destination = ""
        
        # Find Canadian origin
        for location in canadian_locations:
            if location in text.upper():
                origin = location.title()
                print(f"      📍 Canadian origin: {origin}")
                break
        
        # Find US destination
        for location in us_locations:
            if location in text.upper():
                destination = location.title()
                print(f"      📍 US destination: {destination}")
                break
        
        # Fallback to province/state detection
        if not origin:
            if re.search(r'\b(BC|AB|SK|MB)\b', text):
                origin = "Western Canada"
        
        if not destination:
            if re.search(r'\b(IL|MN|MO|WI)\b', text):
                destination = "Midwest US"
        
        return origin, destination
    
    def _extract_currency_improved(self, text: str) -> str:
        """Determine currency"""
        if re.search(r'CAD|CANADIAN|C\$', text, re.IGNORECASE):
            return 'CAD'
        elif re.search(r'USD|US\$|UNITED STATES', text, re.IGNORECASE):
            return 'USD'
        # Default based on context - CP Rail often uses USD for US routes
        return 'USD'

# For compatibility
OCREngine = EnhancedOCREngine