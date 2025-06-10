"""
Enhanced Data Processor with Database Fix and Improved Parsing
File: backend/app/document_processor/enhanced_data_processor.py
"""
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class EnhancedDataProcessor:
    """Enhanced data processor with improved parsing and database compatibility"""
    
    def __init__(self):
        self.processing_stats = {
            'rates_processed': 0,
            'notes_processed': 0,
            'commodities_processed': 0,
            'errors_encountered': 0
        }
    
    def process_extracted_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and clean extracted data for database compatibility"""
        print("🔄 Starting enhanced data processing...")
        
        processed_data = {
            'header': self._process_header(raw_data.get('header', {})),
            'commodities': self._process_commodities(raw_data.get('commodities', [])),
            'rates': self._process_rates(raw_data.get('rates', [])),
            'notes': self._process_notes(raw_data.get('notes', [])),
            'origin_info': self._clean_text(raw_data.get('origin_info', '')),
            'destination_info': self._clean_text(raw_data.get('destination_info', '')),
            'currency': self._determine_currency(raw_data),
            'pdf_name': raw_data.get('pdf_name', ''),
            'raw_text': raw_data.get('raw_text', ''),
            'processing_metadata': self._create_processing_metadata(raw_data)
        }
        
        print(f"✅ Enhanced processing complete:")
        print(f"   Rates: {len(processed_data['rates'])}")
        print(f"   Notes: {len(processed_data['notes'])}")
        print(f"   Commodities: {len(processed_data['commodities'])}")
        
        return processed_data
    
    def _process_header(self, header: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate header information"""
        processed_header = {}
        
        # Clean and validate each field
        if header.get('item_number'):
            processed_header['item_number'] = str(header['item_number']).strip()
        
        if header.get('revision'):
            try:
                processed_header['revision'] = int(str(header['revision']).strip())
            except (ValueError, TypeError):
                processed_header['revision'] = 0
        
        # Process dates
        date_fields = ['issue_date', 'effective_date', 'expiration_date']
        for field in date_fields:
            if header.get(field):
                processed_date = self._parse_date(header[field])
                if processed_date:
                    processed_header[field] = processed_date
        
        # Clean text fields
        text_fields = ['cprs_number', 'change_description']
        for field in text_fields:
            if header.get(field):
                processed_header[field] = self._clean_text(header[field])
        
        return processed_header
    
    def _process_commodities(self, commodities: List[Dict]) -> List[Dict[str, Any]]:
        """Process and clean commodity data"""
        processed_commodities = []
        
        for commodity in commodities:
            if not commodity or not isinstance(commodity, dict):
                continue
            
            processed_commodity = {}
            
            # Clean commodity name
            name = commodity.get('name', '').strip()
            if name and len(name) > 1:
                processed_commodity['name'] = self._clean_commodity_name(name)
                
                # Clean STCC code
                stcc = commodity.get('stcc_code', '').strip()
                processed_commodity['stcc_code'] = self._clean_stcc_code(stcc)
                
                # Add description
                description = commodity.get('description', '') or name
                processed_commodity['description'] = self._clean_text(description)
                
                processed_commodities.append(processed_commodity)
                self.processing_stats['commodities_processed'] += 1
        
        return processed_commodities
    
    def _process_rates(self, rates: List[Dict]) -> List[Dict[str, Any]]:
        """Process and clean rate data with improved parsing"""
        processed_rates = []
        
        for rate in rates:
            if not rate or not isinstance(rate, dict):
                continue
            
            try:
                processed_rate = self._parse_single_rate(rate)
                if processed_rate:
                    processed_rates.append(processed_rate)
                    self.processing_stats['rates_processed'] += 1
            except Exception as e:
                logger.warning(f"Error processing rate: {e}")
                self.processing_stats['errors_encountered'] += 1
        
        return processed_rates
    
    def _parse_single_rate(self, rate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single rate entry with improved logic"""
        
        # Get raw rate text for analysis
        raw_line = rate.get('raw_line', '') or rate.get('context', '')
        origin = rate.get('origin', '').strip()
        destination = rate.get('destination', '').strip()
        rate_amount = str(rate.get('rate_amount', '') or rate.get('rate', '')).strip()
        
        # If origin/destination look malformed, try to re-parse from raw line
        if self._is_malformed_location(origin) or self._is_malformed_location(destination):
            origin, destination = self._extract_locations_from_raw(raw_line)
        
        # Clean and validate rate amount
        cleaned_amount = self._clean_rate_amount(rate_amount)
        if not cleaned_amount:
            return None
        
        # Extract additional rate information
        train_type = self._extract_train_type(rate, raw_line)
        equipment_type = self._extract_equipment_type(rate, raw_line)
        route_code = self._extract_route_code(rate, raw_line)
        
        processed_rate = {
            'origin': self._clean_location(origin),
            'destination': self._clean_location(destination),
            'origin_state': self._extract_state_from_location(origin),
            'destination_state': self._extract_state_from_location(destination),
            'rate_amount': cleaned_amount,
            'currency': 'USD',  # Default, will be updated by parent process
            'rate_category': rate.get('rate_category', 'standard'),
            'train_type': train_type,
            'car_capacity_type': self._extract_capacity_type(rate, raw_line),
            'route_code': route_code,
            'additional_provisions': self._clean_text(rate.get('additional_provisions', ''))
        }
        
        # Only return if we have minimum required data
        if processed_rate['origin'] and processed_rate['destination'] and processed_rate['rate_amount']:
            return processed_rate
        
        return None
    
    def _is_malformed_location(self, location: str) -> bool:
        """Check if location data appears malformed"""
        if not location:
            return True
        
        # Check for common malformation patterns
        malformed_patterns = [
            r'RATE\s+ROUTE',
            r'LOW\s+CAP\s+HIGH\s+CAP',
            r'ADDITIONAL\s+PROVISIONS',
            r'^[^A-Z]*$',  # No uppercase letters
            len(location) > 100  # Extremely long
        ]
        
        for pattern in malformed_patterns:
            if re.search(pattern, location, re.IGNORECASE):
                return True
        
        return False
    
    def _extract_locations_from_raw(self, raw_line: str) -> Tuple[str, str]:
        """Extract origin and destination from raw line text"""
        if not raw_line:
            return '', ''
        
        # Look for common patterns
        patterns = [
            # Pattern: CITY ST to CITY ST
            r'([A-Z][A-Z\s]+[A-Z]{2})\s+(?:to|TO)\s+([A-Z][A-Z\s]+[A-Z]{2})',
            # Pattern: CITY, ST to CITY, ST  
            r'([A-Z][A-Z\s]+,\s*[A-Z]{2})\s+(?:to|TO)\s+([A-Z][A-Z\s]+,\s*[A-Z]{2})',
            # Pattern: Multiple words with state codes
            r'([A-Z][A-Z\s]*\s+[A-Z]{2})\s+([A-Z][A-Z\s]*\s+[A-Z]{2})',
            # Pattern: Simple two-word locations
            r'^([A-Z]+\s+[A-Z]+)\s+([A-Z]+\s+[A-Z]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, raw_line)
            if match:
                origin = match.group(1).strip()
                destination = match.group(2).strip()
                
                # Validate locations aren't too generic
                if (len(origin) > 3 and len(destination) > 3 and 
                    origin != destination and 
                    not any(word in origin.upper() for word in ['RATE', 'ROUTE', 'CAP'])):
                    return origin, destination
        
        return '', ''
    
    def _clean_rate_amount(self, amount: str) -> str:
        """Clean and validate rate amount"""
        if not amount:
            return ''
        
        # Remove currency symbols and extract numeric value
        cleaned = re.sub(r'[^\d.]', '', str(amount))
        
        # Validate it's a reasonable number
        try:
            value = float(cleaned)
            if 0.01 <= value <= 10000:  # Reasonable rate range
                return f"{value:.2f}"
        except (ValueError, TypeError):
            pass
        
        return ''
    
    def _extract_train_type(self, rate: Dict, raw_line: str) -> str:
        """Extract train type from rate data"""
        train_types = [
            'SINGLE CAR', 'UNIT TRAIN', '25 CAR', '50 CAR', '100 CAR',
            'LOW CAP', 'HIGH CAP', 'SPLIT TRAIN'
        ]
        
        # Check rate dict first
        existing_type = rate.get('train_type', '').strip()
        if existing_type and existing_type not in ['', 'standard']:
            return existing_type
        
        # Check raw line
        for train_type in train_types:
            if train_type in raw_line.upper():
                return train_type
        
        return 'SINGLE CAR'  # Default
    
    def _extract_equipment_type(self, rate: Dict, raw_line: str) -> str:
        """Extract equipment type information"""
        equipment_types = [
            'COVERED HOPPER', 'GONDOLA', 'TANK CAR', 'BOXCAR'
        ]
        
        # Check rate dict first
        existing_type = rate.get('equipment_type', '').strip()
        if existing_type:
            return existing_type
        
        # Check raw line
        for equip_type in equipment_types:
            if equip_type in raw_line.upper():
                return equip_type
        
        return ''
    
    def _extract_capacity_type(self, rate: Dict, raw_line: str) -> str:
        """Extract capacity type (LOW CAP/HIGH CAP)"""
        if 'HIGH CAP' in raw_line.upper():
            return 'HIGH CAP'
        elif 'LOW CAP' in raw_line.upper():
            return 'LOW CAP'
        
        return rate.get('car_capacity_type', '')
    
    def _extract_route_code(self, rate: Dict, raw_line: str) -> str:
        """Extract route code"""
        # Look for route codes in format like CP001, 1234, etc.
        route_patterns = [
            r'CP\d{3,4}',
            r'ROUTE[:\s]+(\d{3,4})',
            r'\b(\d{4})\b'
        ]
        
        for pattern in route_patterns:
            match = re.search(pattern, raw_line, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        return rate.get('route_code', '')
    
    def _clean_location(self, location: str) -> str:
        """Clean location name"""
        if not location:
            return ''
        
        # Remove common OCR artifacts
        cleaned = re.sub(r'[^\w\s,.-]', '', location)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Capitalize properly
        if cleaned:
            words = cleaned.split()
            cleaned = ' '.join(word.upper() if len(word) <= 2 else word.title() for word in words)
        
        return cleaned[:50]  # Limit length
    
    def _extract_state_from_location(self, location: str) -> str:
        """Extract state/province code from location"""
        if not location:
            return ''
        
        # Common state/province codes
        state_codes = [
            'AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT',
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 
            'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS',
            'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK',
            'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
        ]
        
        words = location.upper().split()
        for word in words:
            if word in state_codes:
                return word
        
        return ''
    
    def _process_notes(self, notes: List[Dict]) -> List[Dict[str, Any]]:
        """Process and clean notes data"""
        processed_notes = []
        
        for note in notes:
            if not note or not isinstance(note, dict):
                continue
            
            note_text = note.get('text', '').strip()
            if not note_text or len(note_text) < 3:
                continue
            
            processed_note = {
                'type': self._determine_note_type(note),
                'code': note.get('code', ''),
                'text': self._clean_text(note_text),
                'sort_order': note.get('sort_order', 0)
            }
            
            processed_notes.append(processed_note)
            self.processing_stats['notes_processed'] += 1
        
        return processed_notes
    
    def _determine_note_type(self, note: Dict) -> str:
        """Determine the type of note"""
        note_type = note.get('type', '').upper()
        note_text = note.get('text', '').upper()
        
        if note_type in ['ASTERISK', 'NUMBERED', 'PROVISION', 'EQUIPMENT', 'GENERAL']:
            return note_type
        
        # Determine from content
        if note_text.startswith('*'):
            return 'ASTERISK'
        elif re.match(r'^\d+\.', note_text):
            return 'NUMBERED'
        elif any(word in note_text for word in ['EQUIPMENT', 'CAR', 'HOPPER']):
            return 'EQUIPMENT'
        elif any(word in note_text for word in ['RATE', 'CHARGE', 'PROVISION']):
            return 'PROVISION'
        else:
            return 'GENERAL'
    
    def _clean_commodity_name(self, name: str) -> str:
        """Clean commodity name"""
        if not name:
            return ''
        
        # Remove STCC codes from name
        cleaned = re.sub(r'\d{2}\s+\d{3}\s+\d{2}', '', name)
        cleaned = re.sub(r'[^\w\s-]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned.title()[:100]  # Limit length
    
    def _clean_stcc_code(self, stcc: str) -> str:
        """Clean and validate STCC code"""
        if not stcc:
            return ''
        
        # Look for STCC pattern: XX XXX XX
        match = re.search(r'(\d{2})\s*(\d{3})\s*(\d{2})', stcc)
        if match:
            return f"{match.group(1)} {match.group(2)} {match.group(3)}"
        
        return ''
    
    def _clean_text(self, text: str) -> str:
        """Generic text cleaning"""
        if not text:
            return ''
        
        # Remove excessive whitespace and clean
        cleaned = re.sub(r'\s+', ' ', str(text)).strip()
        
        # Remove common OCR artifacts
        cleaned = re.sub(r'[^\w\s.,()-:;/]', '', cleaned)
        
        return cleaned[:500]  # Limit length
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to ISO format"""
        if not date_str:
            return None
        
        date_patterns = [
            r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})',  # JUL 22, 2024
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # 07/22/2024
            r'(\d{4})-(\d{1,2})-(\d{1,2})'  # 2024-07-22
        ]
        
        month_map = {
            'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
            'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
            'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
        }
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str.upper())
            if match:
                if pattern == date_patterns[0]:  # Month name format
                    month = month_map.get(match.group(1), '01')
                    day = match.group(2).zfill(2)
                    year = match.group(3)
                    return f"{year}-{month}-{day}"
                elif pattern == date_patterns[1]:  # MM/DD/YYYY
                    month = match.group(1).zfill(2)
                    day = match.group(2).zfill(2)
                    year = match.group(3)
                    return f"{year}-{month}-{day}"
                else:  # YYYY-MM-DD
                    return match.group(0)
        
        return None
    
    def _determine_currency(self, raw_data: Dict) -> str:
        """Determine document currency"""
        raw_text = raw_data.get('raw_text', '').upper()
        
        if any(term in raw_text for term in ['CAD', 'CANADIAN', 'C$']):
            return 'CAD'
        else:
            return 'USD'  # Default for CP Rail cross-border
    
    def _create_processing_metadata(self, raw_data: Dict) -> Dict[str, Any]:
        """Create processing metadata"""
        return {
            'processing_time_seconds': raw_data.get('processing_metadata', {}).get('processing_time_seconds', 0),
            'file_size_bytes': 0,  # Will be updated by caller
            'ocr_engine': 'Enhanced OCR with Data Processor',
            'ai_processing_used': True,
            'pages_processed': raw_data.get('processing_metadata', {}).get('pages_processed', 1),
            'tables_found': raw_data.get('processing_metadata', {}).get('tables_found', 0),
            'text_blocks_found': raw_data.get('processing_metadata', {}).get('text_blocks_found', 0),
            'extraction_success': True,
            'rates_processed': self.processing_stats['rates_processed'],
            'notes_processed': self.processing_stats['notes_processed'],
            'commodities_processed': self.processing_stats['commodities_processed'],
            'errors_encountered': self.processing_stats['errors_encountered']
        }