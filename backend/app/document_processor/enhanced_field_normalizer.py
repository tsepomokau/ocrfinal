"""
Enhanced Field Normalizer for CP Tariff Documents

"""
import re
import json
import os
from typing import Dict, List, Any, Optional
import openai
from datetime import datetime

class EnhancedFieldNormalizer:
    """Production-ready class for normalizing CP Tariff fields and extracting structured data with AI enhancement."""
    
    def __init__(self, ocr_text: str, pdf_name: str = ""):
        """Initialize with OCR text and PDF name."""
        self.ocr_text = ocr_text
        self.pdf_name = pdf_name
        
        # FIXED: Get OpenAI API key with proper error handling
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key or self.openai_api_key.startswith('your_'):
            print("⚠️  OPENAI_API_KEY not found or not configured - AI features disabled")
            self.ai_available = False
        else:
            try:
                openai.api_key = self.openai_api_key
                self.ai_available = True
                print("✅ OpenAI API configured successfully")
            except Exception as e:
                print(f"⚠️  OpenAI configuration failed: {e}")
                self.ai_available = False
    
    def normalize_tariff_data(self) -> Dict[str, Any]:
        """Extract and normalize all tariff data using AI if available, with fallback to rule-based extraction."""
        
        # Primary attempt: Use AI extraction if available
        if self.ai_available:
            try:
                print("🤖 Attempting AI-powered extraction...")
                return self._extract_with_openai_api()
            except Exception as e:
                print(f"⚠️  AI extraction failed: {e}")
                print("🔄 Falling back to rule-based extraction...")
        else:
            print("🔄 Using rule-based extraction (AI not available)")
        
        # Fallback: Enhanced rule-based extraction
        return self._extract_with_rules_enhanced()
    
    def _extract_with_openai_api(self) -> Dict[str, Any]:
        """Extract structured data using OpenAI GPT-4 API"""
        # Construct the comprehensive prompt
        prompt = self._create_comprehensive_prompt()
        
        # Call OpenAI API with proper error handling
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert in processing Canadian Pacific Railway tariff documents. Extract comprehensive structured data from OCR text of CP Tariff documents with high accuracy. Always return valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
                max_tokens=4000,
                timeout=30
            )
            
            # Parse and validate the response
            if response.choices and response.choices[0].message.content:
                result = json.loads(response.choices[0].message.content)
                
                # Post-process the result for consistency
                processed_result = self._post_process_ai_result(result)
                print("✅ AI extraction completed successfully")
                return processed_result
            else:
                raise ValueError("Empty response from OpenAI API")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error from AI response: {e}")
            raise e
        except Exception as e:
            print(f"❌ Error calling OpenAI API: {e}")
            raise e
    
    def _create_comprehensive_prompt(self) -> str:
        """Create a comprehensive prompt for OpenAI API with explicit instructions."""
        # Truncate text if too long to avoid token limits
        max_text_length = 8000  # Conservative limit for GPT-4
        ocr_text = self.ocr_text[:max_text_length] if len(self.ocr_text) > max_text_length else self.ocr_text
        
        return f"""
Extract comprehensive data from this CP Tariff OCR text. The document contains railway shipping rates and terms.

REQUIRED FIELDS TO EXTRACT:

1. HEADER INFORMATION:
   - Item Number (look for "ITEM:" followed by number)
   - Revision Number (look for "REVISION:" followed by number)
   - CPRS Number (look for "CPRS" followed by alphanumeric code)
   - Issue Date (look for "ISSUED:" followed by date)
   - Effective Date (look for "EFFECTIVE:" followed by date)
   - Expiration Date (look for "EXPIRES:" followed by date)
   - Change Description (look for "CHANGE:" followed by description)

2. COMMODITY INFORMATION:
   - Commodity Names and descriptions
   - STCC Codes (Standard Transportation Commodity Codes in format XX XXX XX)
   - Commodity descriptions

3. ORIGIN AND DESTINATION:
   - Origin locations (cities, states/provinces)
   - Destination locations (cities, states/provinces)

4. RATE DATA:
   - All rate tables with origins, destinations, and rates
   - Rate categories (A, B, C, D columns)
   - Train types (Single Cars, 25 Cars, Unit Train, etc.)
   - Car capacity types (Low Cap, High Cap)
   - Route codes and descriptions
   - Rate amounts in dollars

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

IMPORTANT PARSING RULES:
- Extract ALL numerical rate values with their corresponding origins and destinations
- Preserve the relationship between rates and their applicable conditions
- Identify and categorize different types of notes correctly
- Parse dates in various formats (JAN 01, 2024 or 01/01/2024)
- Clean and standardize location names
- Extract STCC codes in the standard format

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
            "name": "string",
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
            "additional_provisions": "string"
        }}
    ],
    "notes": [
        {{
            "type": "string",
            "code": "string",
            "text": "string"
        }}
    ],
    "route_info": "string",
    "equipment_info": "string"
}}

OCR TEXT TO PROCESS:
{ocr_text}
"""
    
    def _post_process_ai_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process AI result to clean and validate data for production use."""
        
        # Ensure required keys exist
        required_sections = ['header', 'commodities', 'rates', 'notes']
        for section in required_sections:
            if section not in result:
                result[section] = {} if section == 'header' else []
        
        # Clean and validate header dates
        if 'header' in result and result['header']:
            header = result['header']
            date_fields = ['issue_date', 'effective_date', 'expiration_date']
            for date_field in date_fields:
                if date_field in header and header[date_field]:
                    header[date_field] = self._standardize_date_format(header[date_field])
        
        # Clean and validate rate amounts
        if 'rates' in result and result['rates']:
            for rate in result['rates']:
                if 'rate_amount' in rate and rate['rate_amount']:
                    rate['rate_amount'] = self._clean_rate_amount(rate['rate_amount'])
        
        # Standardize commodity structure
        if 'commodities' in result and result['commodities']:
            for commodity in result['commodities']:
                # Ensure consistent key names
                if 'commodity_name' in commodity and 'name' not in commodity:
                    commodity['name'] = commodity.pop('commodity_name')
        
        # Standardize note structure  
        if 'notes' in result and result['notes']:
            for note in result['notes']:
                # Ensure consistent key names
                if 'note_type' in note and 'type' not in note:
                    note['type'] = note.pop('note_type')
                if 'note_code' in note and 'code' not in note:
                    note['code'] = note.pop('note_code')
                if 'note_text' in note and 'text' not in note:
                    note['text'] = note.pop('note_text')
                    
                # Standardize note types
                if 'type' in note:
                    note['type'] = self._standardize_note_type(note['type'])
        
        # Add PDF name and processing metadata
        result['pdf_name'] = self.pdf_name
        result['processing_method'] = 'AI_ENHANCED'
        result['processing_timestamp'] = datetime.now().isoformat()
        
        return result
    
    def _clean_rate_amount(self, amount) -> Optional[float]:
        """Clean and convert rate amount to float"""
        if amount is None:
            return None
            
        try:
            # Convert to string and clean
            amount_str = str(amount).replace('$', '').replace(',', '').strip()
            return float(amount_str) if amount_str else None
        except (ValueError, TypeError):
            return None
    
    def _standardize_note_type(self, note_type: str) -> str:
        """Standardize note type values"""
        if not note_type:
            return 'GENERAL'
            
        note_type = note_type.upper().strip()
        
        # Map variations to standard types
        type_mapping = {
            'EQUIPMENT': 'EQUIPMENT',
            'EQUIP': 'EQUIPMENT', 
            'A': 'EQUIPMENT',
            'B': 'EQUIPMENT',
            'C': 'EQUIPMENT',
            'PROVISION': 'PROVISION',
            'PROV': 'PROVISION',
            'NUMBERED': 'PROVISION',
            'ASTERISK': 'ASTERISK',
            'STAR': 'ASTERISK',
            '*': 'ASTERISK',
            'GENERAL': 'GENERAL',
            'NOTE': 'GENERAL'
        }
        
        return type_mapping.get(note_type, 'GENERAL')
    
    def _standardize_date_format(self, date_str: str) -> str:
        """Standardize date format for database consistency"""
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
    
    def _extract_with_rules_enhanced(self) -> Dict[str, Any]:
        """Enhanced rule-based extraction when AI is not available"""
        print("🔄 Using enhanced rule-based extraction...")
        
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
            "pdf_name": self.pdf_name,
            "processing_method": "RULE_BASED",
            "processing_timestamp": datetime.now().isoformat()
        }
        
        # Extract header information with improved patterns
        header_patterns = {
            'item_number': r'ITEM[:\s]*(\d+)',
            'revision': r'REVISION[:\s]*(\d+)',
            'cprs_number': r'CPRS\s+([A-Z0-9-]+)',
            'issue_date': r'ISSUED[:\s]*([A-Z]{3}\s+\d{1,2},?\s+\d{4})',
            'effective_date': r'EFFECTIVE[:\s]*([A-Z]{3}\s+\d{1,2},?\s+\d{4})',
            'expiration_date': r'EXPIRES[:\s]*([A-Z]{3}\s+\d{1,2},?\s+\d{4})',
            'change_description': r'CHANGE[:\s]*([^\n]+)'
        }
        
        for field, pattern in header_patterns.items():
            match = re.search(pattern, self.ocr_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if 'date' in field:
                    value = self._standardize_date_format(value)
                result['header'][field] = value
                print(f"✅ Found {field}: {value}")
        
        # Extract commodities and STCC codes with enhanced patterns
        commodity_patterns = [
            r'([A-Z\s,]+)\s+STCC[:\s]*(\d{2}\s+\d{3}\s+\d{2})',  # Standard format
            r'STCC[:\s]*(\d{2}\s+\d{3}\s+\d{2})[:\s]*([A-Z\s,]+)',  # Reversed format
        ]
        
        for pattern in commodity_patterns:
            matches = re.finditer(pattern, self.ocr_text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 2:
                    commodity = {
                        'name': match.group(1).strip(),
                        'stcc_code': match.group(2).replace(' ', ''),
                        'description': ''
                    }
                    result['commodities'].append(commodity)
                    print(f"✅ Found commodity: {commodity['name']} ({commodity['stcc_code']})")
        
        # Extract currency information
        currency_patterns = [
            r'(USD|US\s+FUNDS|UNITED STATES)',
            r'(CAD|CDN|CANADIAN)'
        ]
        
        for pattern in currency_patterns:
            if re.search(pattern, self.ocr_text, re.IGNORECASE):
                result['currency'] = 'USD' if 'US' in pattern else 'CAD'
                break
        
        # Extract origin and destination with multiple patterns
        location_patterns = [
            (r'ORIGIN[:\s]*([^\n_]+)', 'origin_info'),
            (r'FROM[:\s]*([^\n_]+)', 'origin_info'),
            (r'DESTINATION[:\s]*([^\n_]+)', 'destination_info'),
            (r'TO[:\s]*([^\n_]+)', 'destination_info')
        ]
        
        for pattern, field in location_patterns:
            match = re.search(pattern, self.ocr_text, re.IGNORECASE)
            if match and not result[field]:  # Only set if not already found
                result[field] = match.group(1).strip()
                print(f"✅ Found {field}: {result[field]}")
        
        # Extract rates with multiple pattern attempts
        rate_patterns = [
            r'([A-Z\s]+?)\s+([A-Z\s]+?)\s+\$(\d+\.?\d*)',  # Basic rate pattern
            r'([A-Z\s]+?)\s+to\s+([A-Z\s]+?)\s+\$(\d+\.?\d*)',  # "to" pattern
            r'(\w+)\s+(\w+)\s+(\d+\.\d{2})',  # Simplified pattern
        ]
        
        for pattern in rate_patterns:
            matches = re.finditer(pattern, self.ocr_text, re.IGNORECASE)
            for match in matches:
                try:
                    rate = {
                        'origin': match.group(1).strip(),
                        'destination': match.group(2).strip(),
                        'rate_amount': float(match.group(3).replace('$', '')),
                        'currency': result['currency'],
                        'origin_state': '',
                        'destination_state': '',
                        'rate_category': 'standard',
                        'train_type': '',
                        'car_capacity_type': '',
                        'route_code': '',
                        'additional_provisions': ''
                    }
                    result['rates'].append(rate)
                    print(f"✅ Found rate: {rate['origin']} to {rate['destination']} - ${rate['rate_amount']}")
                except (ValueError, IndexError):
                    continue
        
        # Extract notes with comprehensive patterns
        note_patterns = [
            (r'^([A-Z])\s*-\s*([^\n]+)', 'EQUIPMENT'),
            (r'^(\d+)\s*-\s*([^\n]+)', 'PROVISION'),
            (r'^(\*)\s*-?\s*([^\n]+)', 'ASTERISK'),
            (r'NOTE[:\s]*([^\n]+)', 'GENERAL'),
            (r'([A-Z])\s+-\s+([^\n]+)', 'EQUIPMENT'),  # Alternative format
        ]
        
        for pattern, note_type in note_patterns:
            matches = re.finditer(pattern, self.ocr_text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                note = {
                    'type': note_type,
                    'code': match.group(1) if len(match.groups()) > 1 else '',
                    'text': match.group(2) if len(match.groups()) > 1 else match.group(1)
                }
                result['notes'].append(note)
                print(f"✅ Found note ({note_type}): {note['text'][:50]}...")
        
        print(f"📊 Rule-based extraction complete:")
        print(f"   - Header fields: {len(result['header'])}")
        print(f"   - Commodities: {len(result['commodities'])}")
        print(f"   - Rates: {len(result['rates'])}")
        print(f"   - Notes: {len(result['notes'])}")
        
        return result

    # Alias method for backward compatibility
    def normalize(self) -> Dict[str, Any]:
        """Alias for normalize_tariff_data method"""
        return self.normalize_tariff_data()