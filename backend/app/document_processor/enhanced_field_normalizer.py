import re
import json
from typing import Dict, List, Any, Optional
import openai
from datetime import datetime

from config import OPENAI_API_KEY

class EnhancedFieldNormalizer:
    """Enhanced class for normalizing CP Tariff fields and extracting structured data."""
    
    def __init__(self, ocr_text: str, pdf_name: str = ""):
        """Initialize with OCR text and PDF name."""
        self.ocr_text = ocr_text
        self.pdf_name = pdf_name
        openai.api_key = OPENAI_API_KEY
    
    def normalize(self) -> Dict[str, Any]:
        """Extract and normalize all tariff data using GPT-4."""
        # Construct the enhanced prompt
        prompt = self._create_enhanced_prompt()
        
        # Call OpenAI API
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert in processing Canadian Pacific Railway tariff documents. Extract comprehensive structured data from OCR text of CP Tariff documents with high accuracy."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            
            # Post-process the result
            return self._post_process_result(result)
            
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            # Fallback to enhanced rule-based extraction
            return self._extract_fields_enhanced()
    
    def _create_enhanced_prompt(self) -> str:
        """Create an enhanced prompt for OpenAI API."""
        return f"""
Extract comprehensive data from this CP Tariff OCR text. The document contains railway shipping rates and terms.

REQUIRED FIELDS TO EXTRACT:

1. HEADER INFORMATION:
   - Item Number (ITEM: followed by number)
   - Revision Number (REVISION: followed by number)
   - CPRS Number (CPRS followed by alphanumeric)
   - Issue Date (ISSUED: followed by date)
   - Effective Date (EFFECTIVE: followed by date)
   - Expiration Date (EXPIRES: followed by date)
   - Change Description (CHANGE: followed by description)

2. COMMODITY INFORMATION:
   - Commodity Names and descriptions
   - STCC Codes (Standard Transportation Commodity Codes)

3. ORIGIN AND DESTINATION:
   - Origin locations (cities, states/provinces)
   - Destination locations (cities, states/provinces)

4. RATE DATA:
   - All rate tables with origins, destinations, and rates
   - Rate categories (A, B, C, D columns)
   - Train types (Single Cars, 25 Cars, Unit Train, etc.)
   - Car capacity types (Low Cap, High Cap)
   - Route codes and descriptions

5. NOTES AND PROVISIONS:
   - Equipment notes (A -, B -, C - descriptions)
   - Numbered provisions (1 -, 2 -, 3 - descriptions)
   - Asterisk notes (* - descriptions)
   - Route information
   - General notes and conditions

6. CURRENCY AND EQUIPMENT:
   - Currency type (USD, CAD)
   - Equipment specifications
   - Mileage allowance information

Return ONLY valid JSON in this exact format:
{{
    "header": {{
        "item_number": "string",
        "revision": "string",
        "cprs_number": "string",
        "issue_date": "string",
        "effective_date": "string",
        "expiration_date": "string",
        "change_description": "string"
    }},
    "commodities": [
        {{
            "commodity_name": "string",
            "stcc_code": "string",
            "description": "string"
        }}
    ],
    "origin_info": "string",
    "destination_info": "string",
    "currency": "string",
    "rates": [
        {{
            "origin": "string",
            "destination": "string",
            "origin_state": "string",
            "destination_state": "string",
            "rate_category": "string",
            "rate_amount": "number",
            "train_type": "string",
            "car_capacity_type": "string",
            "route_code": "string",
            "additional_provisions": "string",
            "provision_codes": ["string"]
        }}
    ],
    "notes": [
        {{
            "note_type": "string",
            "note_code": "string",
            "note_text": "string"
        }}
    ],
    "route_info": "string",
    "equipment_info": "string"
}}

OCR TEXT:
{self.ocr_text}
"""
    
    def _post_process_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process the AI result to clean and validate data."""
        # Clean and validate dates
        if 'header' in result:
            header = result['header']
            for date_field in ['issue_date', 'effective_date', 'expiration_date']:
                if date_field in header and header[date_field]:
                    header[date_field] = self._parse_date(header[date_field])
        
        # Clean rate amounts
        if 'rates' in result:
            for rate in result['rates']:
                if 'rate_amount' in rate and rate['rate_amount']:
                    # Clean currency symbols and commas
                    amount_str = str(rate['rate_amount']).replace('$', '').replace(',', '')
                    try:
                        rate['rate_amount'] = float(amount_str)
                    except ValueError:
                        rate['rate_amount'] = None
        
        # Add PDF name
        result['pdf_name'] = self.pdf_name
        
        return result
    
    def _parse_date(self, date_str: str) -> str:
        """Parse and standardize date formats."""
        if not date_str:
            return None
            
        # Common CP Tariff date formats
        date_patterns = [
            r'([A-Z]{3})\s+(\d{1,2}),?\s+(\d{4})',  # JAN 01, 2024
            r'(\d{1,2})/(\d{1,2})/(\d{4})',         # 01/01/2024
            r'(\d{4})-(\d{2})-(\d{2})',             # 2024-01-01
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str.upper())
            if match:
                try:
                    if len(match.groups()) == 3:
                        if match.group(1).isalpha():  # Month name format
                            month_names = {
                                'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
                                'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
                                'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
                            }
                            month = month_names.get(match.group(1), '01')
                            day = match.group(2).zfill(2)
                            year = match.group(3)
                            return f"{year}-{month}-{day}"
                        else:
                            # Numeric format
                            if '-' in date_str:  # YYYY-MM-DD
                                return date_str
                            else:  # MM/DD/YYYY
                                month = match.group(1).zfill(2)
                                day = match.group(2).zfill(2)
                                year = match.group(3)
                                return f"{year}-{month}-{day}"
                except:
                    pass
        
        return date_str  # Return original if parsing fails
    
    def _extract_fields_enhanced(self) -> Dict[str, Any]:
        """Enhanced fallback extraction method."""
        result = {
            "header": {},
            "commodities": [],
            "origin_info": "",
            "destination_info": "",
            "currency": "USD",
            "rates": [],
            "notes": [],
            "route_info": "",
            "equipment_info": "",
            "pdf_name": self.pdf_name
        }
        
        # Extract header information
        header_patterns = {
            'item_number': r'ITEM:\s*(\d+)',
            'revision': r'REVISION:\s*(\d+)',
            'cprs_number': r'CPRS\s+([A-Z0-9-]+)',
            'issue_date': r'ISSUED:\s*([A-Z]{3}\s+\d{1,2},?\s+\d{4})',
            'effective_date': r'EFFECTIVE:\s*([A-Z]{3}\s+\d{1,2},?\s+\d{4})',
            'expiration_date': r'EXPIRES:\s*([A-Z]{3}\s+\d{1,2},?\s+\d{4})',
            'change_description': r'CHANGE:\s*([^\n]+)'
        }
        
        for field, pattern in header_patterns.items():
            match = re.search(pattern, self.ocr_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if 'date' in field:
                    value = self._parse_date(value)
                result['header'][field] = value
        
        # Extract commodities and STCC codes
        commodity_matches = re.findall(r'([A-Z\s,]+)\s+STCC:\s*(\d{2}\s+\d{3}\s+\d{2})', self.ocr_text, re.IGNORECASE)
        for commodity_match in commodity_matches:
            result['commodities'].append({
                'commodity_name': commodity_match[0].strip(),
                'stcc_code': commodity_match[1],
                'description': ''
            })
        
        # Extract currency information
        if re.search(r'(USD|US\s+FUNDS|UNITED STATES)', self.ocr_text, re.IGNORECASE):
            result['currency'] = 'USD'
        elif re.search(r'(CAD|CDN|CANADIAN)', self.ocr_text, re.IGNORECASE):
            result['currency'] = 'CAD'
        
        # Extract origin and destination
        origin_match = re.search(r'ORIGIN:\s*([^\n_]+)', self.ocr_text, re.IGNORECASE)
        if origin_match:
            result['origin_info'] = origin_match.group(1).strip()
        
        dest_match = re.search(r'DESTINATION:\s*([^\n_]+)', self.ocr_text, re.IGNORECASE)
        if dest_match:
            result['destination_info'] = dest_match.group(1).strip()
        
        # Extract notes (A -, B -, 1 -, 2 -, * -)
        note_patterns = [
            (r'^([A-Z])\s*-\s*([^\n]+)', 'EQUIPMENT'),
            (r'^(\d+)\s*-\s*([^\n]+)', 'PROVISION'),
            (r'^(\*)\s*-?\s*([^\n]+)', 'ASTERISK'),
        ]
        
        for pattern, note_type in note_patterns:
            matches = re.findall(pattern, self.ocr_text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                result['notes'].append({
                    'note_type': note_type,
                    'note_code': match[0],
                    'note_text': match[1].strip()
                })
        
        return result