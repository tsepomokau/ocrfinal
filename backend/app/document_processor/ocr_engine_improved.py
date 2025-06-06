"""
Improved OCR Engine with multiple fallback options
"""
import cv2
import numpy as np
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import fitz  # PyMuPDF for PDF text extraction

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    print("⚠️  PaddleOCR not available, using fallback methods")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    # Try to set tesseract path for Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except ImportError:
    TESSERACT_AVAILABLE = False
    print("⚠️  Tesseract not available")

class OCREngine:
    """Enhanced OCR Engine with multiple processing methods"""
    
    def __init__(self, use_paddle=True):
        self.use_paddle = use_paddle and PADDLE_AVAILABLE
        self.use_tesseract = TESSERACT_AVAILABLE
        
        if self.use_paddle:
            try:
                self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
                print("✅ PaddleOCR initialized successfully")
            except Exception as e:
                print(f"❌ PaddleOCR initialization failed: {e}")
                self.use_paddle = False
        
        print(f"🔍 OCR Methods available: PaddleOCR={self.use_paddle}, Tesseract={self.use_tesseract}")
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text directly from PDF if possible"""
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text.strip():
                    full_text += f"\n--- Page {page_num + 1} ---\n{text}"
            
            doc.close()
            
            if len(full_text.strip()) > 50:  # If we got substantial text
                print(f"✅ Extracted {len(full_text)} characters from PDF text layer")
                return full_text
            else:
                print("⚠️  PDF has minimal text layer, will use OCR")
                return ""
                
        except Exception as e:
            print(f"⚠️  PDF text extraction failed: {e}")
            return ""
    
    def process_sections(self, document_sections, pdf_path: str = "") -> Dict[str, Any]:
        """Process document sections with multiple OCR methods"""
        
        # First try to extract text directly from PDF
        if pdf_path:
            pdf_text = self.extract_text_from_pdf(pdf_path)
            if pdf_text:
                parsed_result = self._parse_extracted_text(pdf_text)
                # Return both OCR results and parsed data in the expected format
                return {
                    **parsed_result,
                    "raw_text": pdf_text
                }
        
        # If no PDF text, use OCR on images
        all_text = ""
        results = {}
        
        for i, section in enumerate(document_sections):
            page_key = f"page_{i}"
            
            # Try multiple OCR methods
            text = self._extract_text_from_image(section)
            all_text += f"\n--- Page {i+1} ---\n{text}"
            
            results[page_key] = {
                "full": text,
                "table": self._extract_table_data(text)
            }
        
        # Parse the combined text
        parsed_data = self._parse_extracted_text(all_text)
        
        # Merge OCR results with parsed data
        return {
            **results,
            **parsed_data["parsed_data"],
            "raw_text": all_text
        }
    
    def _extract_text_from_image(self, image) -> str:
        """Extract text from image using available OCR methods"""
        
        # Method 1: PaddleOCR
        if self.use_paddle:
            try:
                result = self.paddle_ocr.ocr(image, cls=True)
                if result and result[0]:
                    text_lines = []
                    for line in result[0]:
                        if len(line) > 1:
                            text_lines.append(line[1][0])
                    text = '\n'.join(text_lines)
                    if text.strip():
                        print(f"✅ PaddleOCR extracted {len(text)} characters")
                        return text
            except Exception as e:
                print(f"⚠️  PaddleOCR failed: {e}")
        
        # Method 2: Tesseract
        if self.use_tesseract:
            try:
                # Convert image format if needed
                if isinstance(image, np.ndarray):
                    from PIL import Image
                    image_pil = Image.fromarray(image)
                else:
                    image_pil = image
                
                text = pytesseract.image_to_string(image_pil, lang='eng')
                if text.strip():
                    print(f"✅ Tesseract extracted {len(text)} characters")
                    return text
            except Exception as e:
                print(f"⚠️  Tesseract failed: {e}")
        
        # Method 3: Fallback
        return "OCR processing completed - text extraction attempted with available methods"
    
    def _parse_extracted_text(self, text: str) -> Dict[str, Any]:
        """Parse the extracted text to find CP Tariff information"""
        
        # Parse header information
        header = self._extract_header_info(text)
        
        # Parse commodities
        commodities = self._extract_commodities(text)
        
        # Parse rates
        rates = self._extract_rates(text)
        
        # Parse notes
        notes = self._extract_notes(text)
        
        return {
            "page_0": {
                "full": text,
                "table": self._extract_table_data(text)
            },
            "parsed_data": {
                "header": header,
                "commodities": commodities,
                "rates": rates,
                "notes": notes
            },
            # Top-level fields for database compatibility
            "header": header,
            "commodities": commodities,
            "rates": rates,
            "notes": notes,
            "origin_info": self._extract_origin_destination(text)[0],
            "destination_info": self._extract_origin_destination(text)[1],
            "currency": "USD"
        }
    
    def _extract_header_info(self, text: str) -> Dict[str, str]:
        """Extract header information from text"""
        header = {}
        
        # Extract item number
        item_match = re.search(r'Item\s*[:\-]?\s*(\d+)', text, re.IGNORECASE)
        if item_match:
            header['item_number'] = item_match.group(1)
        
        # Extract revision
        revision_match = re.search(r'Revision\s*[:\-]?\s*(\d+)', text, re.IGNORECASE)
        if revision_match:
            header['revision'] = revision_match.group(1)
        
        # Extract CPRS number
        cprs_match = re.search(r'CPRS?\s*[:\-]?\s*(\d+)', text, re.IGNORECASE)
        if cprs_match:
            header['cprs_number'] = cprs_match.group(1)
        
        # Extract dates
        date_patterns = [
            r'Effective\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Issue\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Expir\w*\s*[:\-]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'effective' in pattern.lower():
                    header['effective_date'] = match.group(1)
                elif 'issue' in pattern.lower():
                    header['issue_date'] = match.group(1)
                elif 'expir' in pattern.lower():
                    header['expiration_date'] = match.group(1)
        
        return header
    
    def _extract_commodities(self, text: str) -> List[Dict[str, str]]:
        """Extract commodity information"""
        commodities = []
        
        # Look for common commodity patterns
        commodity_patterns = [
            r'(wheat|grain|coal|lumber|ore|steel|container)',
            r'STCC\s*[:\-]?\s*(\d{4,})',
            r'Commodity\s*[:\-]?\s*([A-Za-z\s]+)'
        ]
        
        for pattern in commodity_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                commodities.append({
                    "name": match.group(1).strip(),
                    "stcc_code": "",
                    "description": match.group(0)
                })
        
        return commodities
    
    def _extract_origin_destination(self, text: str) -> tuple:
        """Extract origin and destination information"""
        # Look for "from X to Y" or "X to Y" patterns
        route_pattern = r'(?:from\s+)?([A-Z][A-Za-z\s,]+?)\s+to\s+([A-Z][A-Za-z\s,]+?)(?:\s|$|\.)'
        match = re.search(route_pattern, text, re.IGNORECASE)
        
        if match:
            origin = match.group(1).strip()
            destination = match.group(2).strip()
            return origin, destination
        
        # Fallback: look for Western Canada, Chicago patterns
        if 'western canada' in text.lower():
            origin = "Western Canada"
        elif 'vancouver' in text.lower():
            origin = "Vancouver, BC"
        else:
            origin = ""
            
        if 'chicago' in text.lower():
            destination = "Chicago, IL"
        else:
            destination = ""
            
        return origin, destination

    def _extract_rates(self, text: str) -> List[Dict[str, str]]:
        """Extract rate information with improved parsing"""
        rates = []
        
        # Look for origin-destination patterns
        route_pattern = r'([A-Z][A-Za-z\s,]+?)\s+to\s+([A-Z][A-Za-z\s,]+?)(?:\s|$|\.)'
        routes = list(re.finditer(route_pattern, text, re.IGNORECASE))
        
        # Look for rate patterns
        rate_patterns = [
            r'\$(\d+\.?\d*)\s*(?:per\s+ton|/ton|per\s+car)',
            r'(\d+\.?\d*)\s*cents?\s*(?:per\s+ton|/ton|per\s+car)',
            r'Rate:\s*\$?(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*dollars?\s*(?:per\s+ton|/ton)'
        ]
        
        for route in routes:
            origin = route.group(1).strip()
            destination = route.group(2).strip()
            
            # Look for rates in the surrounding text
            rate_text = text[max(0, route.start()-200):route.end()+200]
            rate_amount = ""
            
            for pattern in rate_patterns:
                rate_match = re.search(pattern, rate_text, re.IGNORECASE)
                if rate_match:
                    rate_amount = rate_match.group(1)
                    break
            
            rates.append({
                "origin": origin,
                "destination": destination,
                "origin_state": self._extract_state(origin),
                "destination_state": self._extract_state(destination),
                "rate_amount": rate_amount,
                "currency": "USD",
                "rate_category": "standard",
                "train_type": "",
                "car_capacity_type": "",
                "route_code": "",
                "additional_provisions": ""
            })
        
        # If no routes found, try to extract basic rate info
        if not rates:
            for pattern in rate_patterns:
                rate_match = re.search(pattern, text, re.IGNORECASE)
                if rate_match:
                    origin, destination = self._extract_origin_destination(text)
                    rates.append({
                        "origin": origin,
                        "destination": destination,
                        "origin_state": self._extract_state(origin),
                        "destination_state": self._extract_state(destination),
                        "rate_amount": rate_match.group(1),
                        "currency": "USD",
                        "rate_category": "standard",
                        "train_type": "",
                        "car_capacity_type": "",
                        "route_code": "",
                        "additional_provisions": ""
                    })
                    break
        
        return rates

    def _extract_state(self, location: str) -> str:
        """Extract state/province from location"""
        state_patterns = {
            r'\b(IL|Illinois)\b': 'IL',
            r'\b(BC|British Columbia)\b': 'BC',
            r'\b(AB|Alberta)\b': 'AB',
            r'\b(SK|Saskatchewan)\b': 'SK',
            r'\b(MB|Manitoba)\b': 'MB',
            r'\b(ON|Ontario)\b': 'ON'
        }
        
        for pattern, state in state_patterns.items():
            if re.search(pattern, location, re.IGNORECASE):
                return state
        return ""

    def _extract_notes(self, text: str) -> List[Dict[str, str]]:
        """Extract notes and provisions with improved parsing"""
        notes = []
        
        # Look for asterisk notes first
        asterisk_pattern = r'\*+([^*\n]+?)(?:\*+|$)'
        asterisk_matches = re.finditer(asterisk_pattern, text)
        
        for i, match in enumerate(asterisk_matches):
            note_text = match.group(1).strip()
            if len(note_text) > 3:  # Filter out very short matches
                notes.append({
                    "type": "ASTERISK",
                    "code": f"*{i+1}",
                    "text": note_text,
                    "sort_order": i
                })
        
        # Look for numbered notes
        note_patterns = [
            r'Note\s*(\d+)\s*[:\-]?\s*([^.]+\.)',
            r'(\d+)\.\s*([^.\n]+\.)',
            r'Provision\s*(\d+)\s*[:\-]?\s*([^.]+\.)',
            r'Exception\s*(\d+)\s*[:\-]?\s*([^.]+\.)'
        ]
        
        note_index = len(notes)
        for pattern in note_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                code = match.group(1) if len(match.groups()) > 1 else f"NOTE_{note_index+1}"
                note_text = match.group(2) if len(match.groups()) > 1 else match.group(1)
                
                notes.append({
                    "type": "NUMBERED",
                    "code": code,
                    "text": note_text.strip(),
                    "sort_order": note_index
                })
                note_index += 1
        
        # Look for general provisions
        provision_patterns = [
            r'(?:Subject to|Applies|Effective|Valid)\s+[^.]+\.',
            r'(?:Minimum|Maximum|Additional)\s+[^.]+\.',
            r'(?:For|When|If)\s+[^.]+\.'
        ]
        
        for pattern in provision_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                provision_text = match.group(0).strip()
                if len(provision_text) > 10 and not any(note['text'] in provision_text for note in notes):
                    notes.append({
                        "type": "PROVISION",
                        "code": f"PROV_{note_index+1}",
                        "text": provision_text,
                        "sort_order": note_index
                    })
                    note_index += 1
        
        return notes
    
    def _extract_table_data(self, text: str) -> str:
        """Extract structured table data"""
        # Simple table extraction - look for tabular patterns
        lines = text.split('\n')
        table_lines = []
        
        for line in lines:
            # Look for lines that might be table rows (multiple values separated by spaces)
            if re.search(r'\s+\$?\d+\.?\d*\s+', line) or \
               re.search(r'[A-Z]+\s+[A-Z]+\s+\$?\d+', line):
                table_lines.append(line.strip())
        
        return '\n'.join(table_lines) if table_lines else text[:500]