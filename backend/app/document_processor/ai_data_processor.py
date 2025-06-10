"""
AI-Enhanced Data Processor for CP Tariff Documents
Uses ChatGPT API for intelligent data extraction and validation.
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# OpenAI integration
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

class AIDataProcessor:
    """AI-enhanced data processor using ChatGPT for intelligent extraction"""
    
    def __init__(self):
        """Initialize AI data processor"""
        self.openai_client = None
        self.ai_available = False
        
        # State/Province codes for validation
        self.state_province_codes = {
            # Canadian Provinces
            'AB': 'Alberta', 'BC': 'British Columbia', 'MB': 'Manitoba',
            'NB': 'New Brunswick', 'NL': 'Newfoundland and Labrador', 'NS': 'Nova Scotia',
            'NT': 'Northwest Territories', 'NU': 'Nunavut', 'ON': 'Ontario',
            'PE': 'Prince Edward Island', 'QC': 'Quebec', 'SK': 'Saskatchewan', 'YT': 'Yukon',
            
            # US States
            'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
            'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
            'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
            'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
            'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
            'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
            'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
            'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
            'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
            'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
            'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
            'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
            'WI': 'Wisconsin', 'WY': 'Wyoming'
        }
        
        self._setup_openai()
        logger.info(f"AI Data Processor initialized - OpenAI available: {self.ai_available}")
    
    def _setup_openai(self):
        """Setup OpenAI API client"""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI library not available")
            return
        
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key and api_key.strip() and not api_key.startswith('your_'):
                self.openai_client = OpenAI(api_key=api_key)
                self.ai_available = True
                logger.info("OpenAI API configured successfully")
            else:
                logger.warning("OPENAI_API_KEY not configured properly")
        except Exception as e:
            logger.error(f"Error setting up OpenAI: {e}")
    
    def process_tariff_data(self, raw_text: str, filename: str, file_size: int) -> Dict[str, Any]:
        """
        Process raw OCR text into structured tariff data using AI enhancement
        
        Args:
            raw_text: Raw text extracted from document
            filename: Original filename
            file_size: File size in bytes
            
        Returns:
            Structured tariff data
        """
        logger.info(f"Processing tariff data from {filename} with AI enhancement")
        
        if not raw_text or len(raw_text.strip()) < 10:
            logger.warning("Insufficient text for processing")
            return self._empty_result(filename, file_size)
        
        # Start with rule-based extraction
        rule_based_data = self._rule_based_extraction(raw_text)
        
        # Enhance with AI if available
        if self.ai_available and self.openai_client:
            try:
                ai_enhanced_data = self._ai_enhanced_extraction(raw_text)
                final_data = self._merge_extraction_results(rule_based_data, ai_enhanced_data)
                extraction_method = "AI_ENHANCED"
            except Exception as e:
                logger.warning(f"AI extraction failed: {e}, using rule-based only")
                final_data = rule_based_data
                extraction_method = "RULE_BASED_FALLBACK"
        else:
            final_data = rule_based_data
            extraction_method = "RULE_BASED_ONLY"
        
        # Add metadata
        final_data['pdf_name'] = filename
        final_data['metadata'] = self._create_metadata(raw_text, filename, file_size, extraction_method)
        
        logger.info(f"Extracted: {len(final_data.get('rates', []))} rates, "
                   f"{len(final_data.get('commodities', []))} commodities, "
                   f"{len(final_data.get('notes', []))} notes")
        
        return final_data
    
    def _ai_enhanced_extraction(self, text: str) -> Dict[str, Any]:
        """Use ChatGPT for intelligent data extraction"""
        
        # Truncate text if too long for API
        max_chars = 12000  # Leave room for prompt
        if len(text) > max_chars:
            text = text[:max_chars] + "... [truncated]"
        
        system_prompt = """You are an expert at extracting structured data from Canadian Pacific Railway tariff documents.

Extract the following information from the provided tariff document text and return it as valid JSON:

{
  "header": {
    "item_number": "tariff item number",
    "revision": "revision number as integer",
    "cprs_number": "CPRS reference number",
    "issue_date": "issue date in YYYY-MM-DD format",
    "effective_date": "effective date in YYYY-MM-DD format", 
    "expiration_date": "expiration date in YYYY-MM-DD format",
    "change_description": "description of changes"
  },
  "commodities": [
    {
      "name": "commodity name",
      "stcc_code": "STCC code without spaces",
      "description": "commodity description"
    }
  ],
  "rates": [
    {
      "origin": "origin city and province/state",
      "destination": "destination city and province/state",
      "origin_state": "two-letter province/state code",
      "destination_state": "two-letter province/state code", 
      "rate_amount": "rate amount as string",
      "currency": "USD or CAD",
      "train_type": "type of train service",
      "equipment_type": "type of rail equipment",
      "route_code": "route code if specified"
    }
  ],
  "notes": [
    {
      "type": "NUMBERED, ASTERISK, or PROVISION",
      "code": "note identifier",
      "text": "note text content"
    }
  ],
  "origin_info": "primary origin location", 
  "destination_info": "primary destination location",
  "currency": "primary currency used"
}

Important extraction rules:
- Extract ALL rates found in tables or text
- Include complete origin/destination information
- Standardize location names (e.g., "VANCOUVER BC", "CHICAGO IL")
- Extract STCC codes in format like "01137" (remove spaces)
- Parse dates into YYYY-MM-DD format (e.g., "JUL 22, 2024" becomes "2024-07-22")
- Identify different train types (SINGLE CAR, UNIT TRAIN, etc.)
- Extract equipment specifications (COVERED HOPPER, etc.)
- Capture all numbered notes and provisions

Return only valid JSON, no additional text."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract structured data from this CP tariff document:\n\n{text}"}
                ],
                max_tokens=2000,
                temperature=0.1,
                timeout=30
            )
            
            ai_result = response.choices[0].message.content
            
            # Parse JSON response
            try:
                parsed_result = json.loads(ai_result)
                logger.info("AI extraction successful")
                return parsed_result
            except json.JSONDecodeError as e:
                logger.error(f"AI returned invalid JSON: {e}")
                # Try to extract JSON from response
                json_match = re.search(r'\{.*\}', ai_result, re.DOTALL)
                if json_match:
                    try:
                        parsed_result = json.loads(json_match.group(0))
                        logger.info("AI extraction successful after JSON cleaning")
                        return parsed_result
                    except:
                        pass
                return {}
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise
    
    def _rule_based_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback rule-based extraction"""
        
        extracted_data = {
            'header': self._extract_header_data(text),
            'commodities': self._extract_commodities(text),
            'rates': self._extract_rates(text),
            'notes': self._extract_notes(text),
            'origin_info': '',
            'destination_info': '',
            'currency': self._determine_currency(text)
        }
        
        # Extract locations
        origin, destination = self._extract_locations(text)
        extracted_data['origin_info'] = origin
        extracted_data['destination_info'] = destination
        
        return extracted_data
    
    def _extract_header_data(self, text: str) -> Dict[str, Any]:
        """Extract header information using regex patterns"""
        header = {}
        
        # Item number
        item_match = re.search(r'ITEM\s*:?\s*(\d+)', text, re.IGNORECASE)
        if item_match:
            header['item_number'] = item_match.group(1)
        
        # Revision
        revision_match = re.search(r'REVISION\s*:?\s*(\d+)', text, re.IGNORECASE)
        if revision_match:
            header['revision'] = int(revision_match.group(1))
        
        # CPRS number
        cprs_match = re.search(r'CPRS\s*:?\s*(\d+-[A-Z])', text, re.IGNORECASE)
        if cprs_match:
            header['cprs_number'] = cprs_match.group(1)
        
        # Dates
        date_patterns = [
            (r'ISSUE\s*(?:DATE)?\s*:?\s*([A-Z]{3}\s+\d{1,2},?\s+\d{4})', 'issue_date'),
            (r'EFFECTIVE\s*(?:DATE)?\s*:?\s*([A-Z]{3}\s+\d{1,2},?\s+\d{4})', 'effective_date'),
            (r'EXPIR\w*\s*(?:DATE)?\s*:?\s*([A-Z]{3}\s+\d{1,2},?\s+\d{4})', 'expiration_date')
        ]
        
        for pattern, field_name in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                header[field_name] = self._standardize_date(match.group(1))
        
        return header
    
    def _extract_commodities(self, text: str) -> List[Dict[str, Any]]:
        """Extract commodity information"""
        commodities = []
        
        # STCC codes (format: XX XXX XX)
        stcc_pattern = r'(\d{2}\s+\d{3}\s+\d{2})'
        stcc_matches = re.finditer(stcc_pattern, text)
        
        for match in stcc_matches:
            stcc_code = match.group(1)
            
            # Find the line containing this STCC code
            lines = text.split('\n')
            for line in lines:
                if stcc_code in line:
                    name = line.replace(stcc_code, '').strip()
                    name = re.sub(r'^[^\w]+|[^\w]+$', '', name)
                    
                    if name and len(name) > 3:
                        commodities.append({
                            'name': name,
                            'stcc_code': stcc_code.replace(' ', ''),
                            'description': line.strip()
                        })
                    break
        
        # Common commodity keywords
        commodity_keywords = ['WHEAT', 'GRAIN', 'CORN', 'SOYBEAN', 'BARLEY', 'CANOLA']
        for keyword in commodity_keywords:
            if keyword in text.upper() and not any(keyword.lower() in c['name'].lower() for c in commodities):
                commodities.append({
                    'name': keyword.title(),
                    'stcc_code': '',
                    'description': f'{keyword.title()} commodity'
                })
        
        return commodities
    
    def _extract_rates(self, text: str) -> List[Dict[str, Any]]:
        """Extract rate information"""
        rates = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            if '$' in line or re.search(r'\d+\.\d{2}', line):
                rate_info = self._parse_rate_line(line)
                if rate_info:
                    rates.append(rate_info)
        
        return rates
    
    def _parse_rate_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single line for rate information"""
        # Extract rate amount
        rate_match = re.search(r'\$?(\d+\.\d{2})', line)
        if not rate_match:
            return None
        
        rate_amount = rate_match.group(1)
        
        # Extract locations
        origin, destination = self._extract_locations_from_line(line)
        if not (origin and destination):
            return None
        
        return {
            'origin': origin,
            'destination': destination,
            'origin_state': self._extract_state_from_location(origin),
            'destination_state': self._extract_state_from_location(destination),
            'rate_amount': rate_amount,
            'currency': 'USD',
            'rate_category': 'standard',
            'train_type': self._extract_train_type(line),
            'equipment_type': self._extract_equipment_type(line),
            'route_code': self._extract_route_code(line)
        }
    
    def _extract_locations_from_line(self, line: str) -> Tuple[str, str]:
        """Extract origin and destination from a line"""
        # Pattern: CITY ST to CITY ST
        to_pattern = r'([A-Z][A-Za-z\s]+[A-Z]{2})\s+(?:to|TO)\s+([A-Z][A-Za-z\s]+[A-Z]{2})'
        match = re.search(to_pattern, line)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        
        # Pattern: Multiple locations with state codes
        location_pattern = r'([A-Z][A-Za-z\s]+\s+[A-Z]{2})'
        locations = re.findall(location_pattern, line)
        
        if len(locations) >= 2:
            return locations[0].strip(), locations[1].strip()
        
        return '', ''
    
    def _extract_state_from_location(self, location: str) -> str:
        """Extract state/province code from location"""
        if not location:
            return ''
        
        words = location.upper().split()
        for word in words:
            if word in self.state_province_codes:
                return word
        
        return ''
    
    def _extract_train_type(self, line: str) -> str:
        """Extract train type from line"""
        train_types = ['SINGLE CAR', 'UNIT TRAIN', '25 CAR', '50 CAR', '100 CAR', 'LOW CAP', 'HIGH CAP']
        line_upper = line.upper()
        for train_type in train_types:
            if train_type in line_upper:
                return train_type
        return ''
    
    def _extract_equipment_type(self, line: str) -> str:
        """Extract equipment type from line"""
        equipment_types = ['COVERED HOPPER', 'GONDOLA', 'TANK CAR', 'BOXCAR']
        line_upper = line.upper()
        for equipment in equipment_types:
            if equipment in line_upper:
                return equipment
        return ''
    
    def _extract_route_code(self, line: str) -> str:
        """Extract route code from line"""
        route_patterns = [r'CP(\d{3,4})', r'ROUTE\s*:?\s*(\d{3,4})', r'\b(\d{4})\b']
        for pattern in route_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        return ''
    
    def _extract_notes(self, text: str) -> List[Dict[str, Any]]:
        """Extract notes and provisions"""
        notes = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            note_info = self._parse_note_line(line, line_num)
            if note_info:
                notes.append(note_info)
        
        return notes
    
    def _parse_note_line(self, line: str, line_num: int) -> Optional[Dict[str, Any]]:
        """Parse a line for note content"""
        # Numbered notes
        numbered_match = re.match(r'^(\d+)\.?\s*(.+)', line)
        if numbered_match:
            return {
                'type': 'NUMBERED',
                'code': numbered_match.group(1),
                'text': numbered_match.group(2)
            }
        
        # Asterisk notes
        if line.startswith('*'):
            return {
                'type': 'ASTERISK',
                'code': '*',
                'text': line[1:].strip()
            }
        
        # Provision keywords
        provision_keywords = ['SUBJECT TO', 'APPLIES', 'MINIMUM', 'MAXIMUM', 'EQUIPMENT']
        if any(keyword in line.upper() for keyword in provision_keywords):
            return {
                'type': 'PROVISION',
                'code': '',
                'text': line
            }
        
        return None
    
    def _extract_locations(self, text: str) -> Tuple[str, str]:
        """Extract primary origin and destination"""
        # FROM...TO pattern
        from_to_match = re.search(r'FROM\s+([^TO\n]+)\s+TO\s+([^\n]+)', text, re.IGNORECASE)
        if from_to_match:
            return from_to_match.group(1).strip(), from_to_match.group(2).strip()
        
        # Common locations
        canadian_cities = ['VANCOUVER BC', 'CALGARY AB', 'WINNIPEG MB', 'TORONTO ON']
        us_cities = ['CHICAGO IL', 'MINNEAPOLIS MN', 'KANSAS CITY MO']
        
        origin = destination = ''
        for city in canadian_cities:
            if city in text.upper():
                origin = city.title()
                break
        
        for city in us_cities:
            if city in text.upper():
                destination = city.title()
                break
        
        return origin, destination
    
    def _determine_currency(self, text: str) -> str:
        """Determine currency from document text"""
        if re.search(r'CAD|CANADIAN|C\$', text, re.IGNORECASE):
            return 'CAD'
        return 'USD'
    
    def _standardize_date(self, date_str: str) -> str:
        """Convert date string to YYYY-MM-DD format"""
        month_map = {
            'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
            'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
            'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
        }
        
        # Handle "JUL 22, 2024" format
        match = re.search(r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})', date_str.upper())
        if match:
            month = month_map.get(match.group(1), '01')
            day = match.group(2).zfill(2)
            year = match.group(3)
            return f"{year}-{month}-{day}"
        
        return date_str
    
    def _merge_extraction_results(self, rule_based: Dict, ai_enhanced: Dict) -> Dict[str, Any]:
        """Merge rule-based and AI extraction results intelligently"""
        
        # Start with rule-based as base
        merged = rule_based.copy()
        
        if not ai_enhanced:
            return merged
        
        # Merge headers (AI takes precedence for missing fields)
        if 'header' in ai_enhanced:
            for key, value in ai_enhanced['header'].items():
                if key not in merged['header'] or not merged['header'][key]:
                    merged['header'][key] = value
        
        # Use AI rates if they're more comprehensive
        if 'rates' in ai_enhanced and len(ai_enhanced['rates']) > len(merged['rates']):
            merged['rates'] = ai_enhanced['rates']
        
        # Combine notes (remove duplicates)
        if 'notes' in ai_enhanced:
            existing_notes = [note['text'] for note in merged['notes']]
            for note in ai_enhanced['notes']:
                if note['text'] not in existing_notes:
                    merged['notes'].append(note)
        
        # Use AI commodities if better
        if 'commodities' in ai_enhanced and len(ai_enhanced['commodities']) > len(merged['commodities']):
            merged['commodities'] = ai_enhanced['commodities']
        
        # Use AI location info if more specific
        if ai_enhanced.get('origin_info') and len(ai_enhanced['origin_info']) > len(merged['origin_info']):
            merged['origin_info'] = ai_enhanced['origin_info']
        
        if ai_enhanced.get('destination_info') and len(ai_enhanced['destination_info']) > len(merged['destination_info']):
            merged['destination_info'] = ai_enhanced['destination_info']
        
        return merged
    
    def _create_metadata(self, text: str, filename: str, file_size: int, extraction_method: str) -> Dict[str, Any]:
        """Create processing metadata"""
        lines = text.split('\n')
        
        return {
            'filename': filename,
            'file_size_bytes': file_size,
            'total_lines': len(lines),
            'non_empty_lines': len([line for line in lines if line.strip()]),
            'text_length': len(text),
            'processing_timestamp': datetime.now().isoformat(),
            'extraction_method': extraction_method,
            'ai_enhancement_used': self.ai_available,
            'tables_found': text.count('TABLE') + text.count('ORIGIN') + text.count('DESTINATION')
        }
    
    def _empty_result(self, filename: str, file_size: int) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            'header': {},
            'commodities': [],
            'rates': [],
            'notes': [],
            'origin_info': '',
            'destination_info': '',
            'currency': 'USD',
            'pdf_name': filename,
            'raw_text': '',
            'metadata': self._create_metadata('', filename, file_size, 'EMPTY_INPUT')
        }