"""
Production OCR Processor - Deployment Ready
File: backend/app/document_processor/production_ocr_processor.py

Production-grade OCR data processor with no sample data.
Extracts all real data from OCR text efficiently.
"""
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class ProductionOCRProcessor:
    """Production-grade OCR data processor"""
    
    def __init__(self):
        self.rate_patterns = self._compile_rate_patterns()
        self.location_patterns = self._compile_location_patterns()
        self.date_patterns = self._compile_date_patterns()
        
    def _compile_rate_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for rate extraction"""
        return [
            re.compile(r'\$\s*(\d+(?:\.\d{1,2})?)', re.IGNORECASE),
            re.compile(r'(\d+(?:\.\d{1,2})?)\s*(?:USD|CAD|DOLLARS?)', re.IGNORECASE),
            re.compile(r'RATE\s*:?\s*\$?\s*(\d+(?:\.\d{1,2})?)', re.IGNORECASE)
        ]
    
    def _compile_location_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for location extraction"""
        return [
            # Canadian cities with provinces
            re.compile(r'\b([A-Z][A-Za-z\s]+(?:VANCOUVER|CALGARY|WINNIPEG|TORONTO|MONTREAL|SASKATOON|REGINA|EDMONTON)[A-Za-z\s]*)\s+([A-Z]{2})\b'),
            # US cities with states
            re.compile(r'\b([A-Z][A-Za-z\s]+(?:CHICAGO|MINNEAPOLIS|KANSAS|MILWAUKEE|DULUTH|DETROIT)[A-Za-z\s]*)\s+([A-Z]{2})\b'),
            # General pattern: CITY ST
            re.compile(r'\b([A-Z][A-Za-z\s]{2,})\s+([A-Z]{2})\b'),
            # Origin-destination with TO keyword
            re.compile(r'([A-Z][A-Za-z\s]+[A-Z]{2})\s+(?:TO|to)\s+([A-Z][A-Za-z\s]+[A-Z]{2})')
        ]
    
    def _compile_date_patterns(self) -> List[re.Pattern]:
        """Compile regex patterns for date extraction"""
        return [
            re.compile(r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})'),  # JUL 22, 2024
            re.compile(r'(\d{4})-(\d{2})-(\d{2})'),          # 2024-07-22
            re.compile(r'(\d{1,2})/(\d{1,2})/(\d{4})'),      # 07/22/2024
        ]
    
    def process_document_data(self, raw_ocr_data: Dict[str, Any], pdf_name: str, file_size_bytes: int) -> Dict[str, Any]:
        """Process OCR data into structured format - production version"""
        
        logger.info("Starting production OCR data processing")
        
        raw_text = raw_ocr_data.get('raw_text', '')
        
        if not raw_text:
            logger.warning("No raw text found in OCR data")
            return self._empty_result(pdf_name, file_size_bytes)
        
        logger.info(f"Processing {len(raw_text):,} characters of OCR text")
        
        # Extract all components
        header = self._extract_header_data(raw_text)
        rates = self._extract_all_rates(raw_text)
        notes = self._extract_all_notes(raw_text)
        commodities = self._extract_commodities(raw_text)
        
        # Extract location info
        origin_info = self._extract_primary_origin(raw_text)
        destination_info = self._extract_primary_destination(raw_text)
        
        # Build result
        result = {
            'header': header,
            'commodities': commodities,
            'rates': rates,
            'notes': notes,
            'origin_info': origin_info,
            'destination_info': destination_info,
            'currency': self._determine_currency(raw_text),
            'pdf_name': pdf_name,
            'raw_text': raw_text,
            'processing_metadata': {
                'processing_time_seconds': 0,  # Will be set by caller
                'file_size_bytes': file_size_bytes,
                'ocr_engine': 'Production OCR Processor',
                'pages_processed': 1,
                'tables_found': self._count_tables(raw_text),
                'extraction_success': True,
                'rates_found': len(rates),
                'notes_found': len(notes),
                'commodities_found': len(commodities)
            }
        }
        
        logger.info(f"Extraction completed: {len(rates)} rates, {len(notes)} notes, {len(commodities)} commodities")
        
        return result
    
    def _extract_header_data(self, text: str) -> Dict[str, Any]:
        """Extract header information from OCR text"""
        
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
        header.update(self._extract_dates(text))
        
        return header
    
    def _extract_dates(self, text: str) -> Dict[str, str]:
        """Extract all dates from text"""
        
        dates = {}
        
        # Date type patterns
        date_types = [
            ('issue_date', r'ISSUE\s*(?:DATE)?\s*:?\s*'),
            ('effective_date', r'EFFECTIVE\s*(?:DATE)?\s*:?\s*'),
            ('expiration_date', r'EXPIR\w*\s*(?:DATE)?\s*:?\s*')
        ]
        
        for date_type, prefix_pattern in date_types:
            # Look for date after the prefix
            pattern = prefix_pattern + r'(\w{3}\s+\d{1,2},?\s+\d{4})'
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                date_str = match.group(1)
                dates[date_type] = self._standardize_date(date_str)
        
        return dates
    
    def _standardize_date(self, date_str: str) -> str:
        """Convert date string to standard format"""
        
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
    
    def _extract_all_rates(self, text: str) -> List[Dict[str, Any]]:
        """Extract all rate data from OCR text"""
        
        rates = []
        lines = text.split('\n')
        
        # Process each line for rates
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Find all dollar amounts in this line
            for pattern in self.rate_patterns:
                for match in pattern.finditer(line):
                    rate_amount = match.group(1)
                    
                    # Get context around this rate
                    context = self._get_line_context(lines, line_num, 3)
                    
                    # Extract origin and destination
                    origin, destination = self._extract_locations_from_context(context)
                    
                    # Skip if locations are invalid
                    if not self._validate_locations(origin, destination):
                        continue
                    
                    rate_entry = {
                        'origin': origin,
                        'destination': destination,
                        'rate_amount': rate_amount,
                        'currency': 'USD',
                        'line_number': line_num,
                        'raw_line': line,
                        'equipment_type': self._extract_equipment_type(context),
                        'service_type': self._extract_service_type(context)
                    }
                    
                    # Avoid duplicates
                    if not self._is_duplicate_rate(rates, rate_entry):
                        rates.append(rate_entry)
        
        # Also extract from table structures
        table_rates = self._extract_rates_from_tables(text)
        
        # Merge and deduplicate
        all_rates = rates + table_rates
        deduplicated_rates = self._deduplicate_rates(all_rates)
        
        logger.info(f"Extracted {len(deduplicated_rates)} unique rates from OCR")
        
        return deduplicated_rates
    
    def _get_line_context(self, lines: List[str], center: int, window: int) -> str:
        """Get context lines around a center line"""
        start = max(0, center - window)
        end = min(len(lines), center + window + 1)
        return '\n'.join(lines[start:end])
    
    def _extract_locations_from_context(self, context: str) -> Tuple[str, str]:
        """Extract origin and destination from context text"""
        
        # Try each location pattern
        for pattern in self.location_patterns:
            matches = list(pattern.finditer(context))
            
            if len(matches) >= 2:
                # First match is likely origin, second is destination
                origin_match = matches[0]
                dest_match = matches[1]
                
                origin = f"{origin_match.group(1).strip()} {origin_match.group(2)}"
                destination = f"{dest_match.group(1).strip()} {dest_match.group(2)}"
                
                return origin, destination
        
        # Try TO pattern
        to_pattern = re.search(r'([A-Z][A-Za-z\s]+[A-Z]{2})\s+(?:TO|to)\s+([A-Z][A-Za-z\s]+[A-Z]{2})', context)
        if to_pattern:
            return to_pattern.group(1).strip(), to_pattern.group(2).strip()
        
        return '', ''
    
    def _validate_locations(self, origin: str, destination: str) -> bool:
        """Validate that locations are real city names"""
        
        if not origin or not destination:
            return False
        
        # Remove common non-location words
        invalid_words = [
            'RATE', 'CHARGE', 'ADDITIONAL', 'PROVISIONS', 'LOW', 'HIGH', 
            'CAP', 'TRAIN', 'CAR', 'EQUIPMENT', 'SERVICE'
        ]
        
        for word in invalid_words:
            if word in origin.upper() or word in destination.upper():
                return False
        
        # Must contain letters
        if not re.search(r'[A-Za-z]', origin) or not re.search(r'[A-Za-z]', destination):
            return False
        
        # Reasonable length
        if len(origin) < 4 or len(destination) < 4:
            return False
        
        return True
    
    def _extract_equipment_type(self, context: str) -> str:
        """Extract equipment type from context"""
        equipment_types = ['COVERED HOPPER', 'GONDOLA', 'TANK CAR', 'BOXCAR', 'SINGLE CAR', 'UNIT TRAIN']
        
        context_upper = context.upper()
        for equipment in equipment_types:
            if equipment in context_upper:
                return equipment
        
        return ''
    
    def _extract_service_type(self, context: str) -> str:
        """Extract service type from context"""
        service_types = ['LOW CAP', 'HIGH CAP', '25 CAR', 'SPLIT TRAIN']
        
        context_upper = context.upper()
        for service in service_types:
            if service in context_upper:
                return service
        
        return ''
    
    def _is_duplicate_rate(self, existing_rates: List[Dict], new_rate: Dict) -> bool:
        """Check if rate is duplicate"""
        for existing in existing_rates:
            if (existing.get('origin') == new_rate.get('origin') and
                existing.get('destination') == new_rate.get('destination') and
                existing.get('rate_amount') == new_rate.get('rate_amount')):
                return True
        return False
    
    def _extract_rates_from_tables(self, text: str) -> List[Dict[str, Any]]:
        """Extract rates from table structures"""
        
        table_rates = []
        lines = text.split('\n')
        
        # Find table headers
        for i, line in enumerate(lines):
            if self._is_table_header(line):
                # Process following lines as table data
                for j in range(i + 1, min(i + 20, len(lines))):
                    table_line = lines[j].strip()
                    if not table_line or len(table_line) < 10:
                        continue
                    
                    rate_data = self._parse_table_line(table_line)
                    if rate_data:
                        table_rates.append(rate_data)
        
        return table_rates
    
    def _is_table_header(self, line: str) -> bool:
        """Check if line is a table header"""
        header_indicators = ['ORIGIN', 'DESTINATION', 'RATE', 'CHARGE']
        line_upper = line.upper()
        
        indicator_count = sum(1 for indicator in header_indicators if indicator in line_upper)
        return indicator_count >= 2
    
    def _parse_table_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a table line for rate data"""
        
        # Split by multiple spaces (common in tables)
        parts = re.split(r'\s{2,}', line)
        
        if len(parts) < 3:
            return None
        
        # Look for rate amount
        rate_amount = None
        for part in parts:
            rate_match = re.search(r'(\d+(?:\.\d{2})?)', part)
            if rate_match:
                rate_amount = rate_match.group(1)
                break
        
        if not rate_amount:
            return None
        
        # First two parts are likely origin and destination
        origin = parts[0].strip()
        destination = parts[1].strip()
        
        if self._validate_locations(origin, destination):
            return {
                'origin': origin,
                'destination': destination,
                'rate_amount': rate_amount,
                'currency': 'USD',
                'raw_line': line,
                'extraction_method': 'table'
            }
        
        return None
    
    def _deduplicate_rates(self, rates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate rates"""
        
        seen = set()
        unique_rates = []
        
        for rate in rates:
            key = (rate.get('origin', ''), rate.get('destination', ''), rate.get('rate_amount', ''))
            if key not in seen:
                seen.add(key)
                unique_rates.append(rate)
        
        return unique_rates
    
    def _extract_all_notes(self, text: str) -> List[Dict[str, Any]]:
        """Extract all notes from OCR text"""
        
        notes = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 3:
                continue
            
            note_data = self._parse_line_for_note(line, line_num)
            if note_data:
                notes.append(note_data)
        
        logger.info(f"Extracted {len(notes)} notes from OCR")
        
        return notes
    
    def _parse_line_for_note(self, line: str, line_num: int) -> Optional[Dict[str, Any]]:
        """Parse line for note content"""
        
        # Numbered notes
        numbered_match = re.match(r'^(\d+)\.?\s*(.+)', line)
        if numbered_match:
            return {
                'type': 'NUMBERED',
                'code': numbered_match.group(1),
                'text': numbered_match.group(2),
                'line_number': line_num,
                'raw_line': line
            }
        
        # Asterisk notes
        if line.startswith('*'):
            return {
                'type': 'ASTERISK',
                'code': '*',
                'text': line[1:].strip(),
                'line_number': line_num,
                'raw_line': line
            }
        
        # Provision keywords
        provision_keywords = ['NOTE', 'PROVISION', 'CONDITION', 'EQUIPMENT', 'SUBJECT TO', 'APPLIES']
        if any(keyword in line.upper() for keyword in provision_keywords):
            return {
                'type': 'PROVISION',
                'code': '',
                'text': line,
                'line_number': line_num,
                'raw_line': line
            }
        
        return None
    
    def _extract_commodities(self, text: str) -> List[Dict[str, Any]]:
        """Extract commodities from OCR text"""
        
        commodities = []
        
        # STCC code pattern
        stcc_pattern = re.compile(r'(\d{2}\s+\d{3}\s+\d{2})')
        
        for stcc_match in stcc_pattern.finditer(text):
            stcc_code = stcc_match.group(1)
            
            # Find the line with this STCC code
            lines = text.split('\n')
            for line in lines:
                if stcc_code in line:
                    commodity_name = line.replace(stcc_code, '').strip()
                    commodity_name = re.sub(r'^[^\w]+|[^\w]+$', '', commodity_name)
                    
                    if commodity_name and len(commodity_name) > 2:
                        commodities.append({
                            'name': commodity_name,
                            'stcc_code': stcc_code.replace(' ', ''),
                            'description': line.strip()
                        })
                    break
        
        # Common commodity names
        commodity_names = ['WHEAT', 'GRAIN', 'CORN', 'SOYBEAN', 'BARLEY', 'FEED', 'FLOUR']
        for name in commodity_names:
            if name in text.upper():
                if not any(c['name'].upper() == name for c in commodities):
                    commodities.append({
                        'name': name.title(),
                        'stcc_code': '',
                        'description': f'{name.title()} commodity'
                    })
        
        logger.info(f"Extracted {len(commodities)} commodities from OCR")
        
        return commodities
    
    def _extract_primary_origin(self, text: str) -> str:
        """Extract primary origin location"""
        canadian_cities = ['VANCOUVER BC', 'CALGARY AB', 'WINNIPEG MB', 'TORONTO ON', 'MONTREAL QC']
        
        for city in canadian_cities:
            if city in text.upper():
                return city.title()
        
        return ''
    
    def _extract_primary_destination(self, text: str) -> str:
        """Extract primary destination location"""
        us_cities = ['CHICAGO IL', 'MINNEAPOLIS MN', 'KANSAS CITY MO', 'ST PAUL MN', 'MILWAUKEE WI']
        
        for city in us_cities:
            if city in text.upper():
                return city.title()
        
        return ''
    
    def _determine_currency(self, text: str) -> str:
        """Determine currency from text"""
        if re.search(r'CAD|CANADIAN|C\$', text, re.IGNORECASE):
            return 'CAD'
        return 'USD'
    
    def _count_tables(self, text: str) -> int:
        """Count number of tables in text"""
        table_count = 0
        lines = text.split('\n')
        
        for line in lines:
            if self._is_table_header(line):
                table_count += 1
        
        return table_count
    
    def _empty_result(self, pdf_name: str, file_size_bytes: int) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            'header': {},
            'commodities': [],
            'rates': [],
            'notes': [],
            'origin_info': '',
            'destination_info': '',
            'currency': 'USD',
            'pdf_name': pdf_name,
            'raw_text': '',
            'processing_metadata': {
                'processing_time_seconds': 0,
                'file_size_bytes': file_size_bytes,
                'ocr_engine': 'Production OCR Processor',
                'pages_processed': 0,
                'tables_found': 0,
                'extraction_success': False,
                'rates_found': 0,
                'notes_found': 0,
                'commodities_found': 0
            }
        }