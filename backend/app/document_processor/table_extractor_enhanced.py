"""
Enhanced Table Extractor for Comprehensive Data Extraction

"""
import re
import cv2
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any, Union
import logging
from collections import defaultdict
import json

logger = logging.getLogger(__name__)

class EnhancedTableExtractor:
    """Enhanced table extractor with comprehensive parsing capabilities for CP Tariff documents"""
    
    def __init__(self, ocr_text: str = "", structured_data: Dict = None):
        """Initialize with OCR text and structured data"""
        self.ocr_text = ocr_text
        self.structured_data = structured_data or {}
        self.lines = ocr_text.split('\n') if ocr_text else []
        self.extracted_tables = []
        self.rate_tables = []
        self.commodity_tables = []
        self.note_tables = []
        
    def extract_all_tables(self) -> Dict[str, Any]:
        """Extract all types of tables from the document"""
        print("🔄 Starting comprehensive table extraction...")
        
        results = {
            'tables_found': 0,
            'rate_tables': [],
            'commodity_tables': [],
            'note_tables': [],
            'general_tables': [],
            'structured_data': {},
            'extraction_metadata': {}
        }
        
        # Method 1: Extract from structured OCR data
        if self.structured_data and 'tables' in self.structured_data:
            structured_tables = self._extract_from_structured_data()
            results['structured_data'] = structured_tables
            print(f"✅ Extracted {len(structured_tables)} tables from structured data")
        
        # Method 2: Extract rate tables specifically
        rate_tables = self._extract_rate_tables()
        results['rate_tables'] = rate_tables
        print(f"✅ Extracted {len(rate_tables)} rate tables")
        
        # Method 3: Extract commodity tables
        commodity_tables = self._extract_commodity_tables()
        results['commodity_tables'] = commodity_tables
        print(f"✅ Extracted {len(commodity_tables)} commodity tables")
        
        # Method 4: Extract note/provision tables
        note_tables = self._extract_note_tables()
        results['note_tables'] = note_tables
        print(f"✅ Extracted {len(note_tables)} note tables")
        
        # Method 5: General table pattern extraction
        general_tables = self._extract_general_tables()
        results['general_tables'] = general_tables
        print(f"✅ Extracted {len(general_tables)} general tables")
        
        # Calculate totals
        total_tables = (len(structured_tables) + len(rate_tables) + 
                       len(commodity_tables) + len(note_tables) + len(general_tables))
        results['tables_found'] = total_tables
        
        # Add metadata
        results['extraction_metadata'] = {
            'total_lines_processed': len(self.lines),
            'structured_data_available': bool(self.structured_data),
            'extraction_methods_used': ['structured_data', 'rate_patterns', 'commodity_patterns', 'note_patterns', 'general_patterns']
        }
        
        print(f"🎉 Table extraction complete: {total_tables} tables found")
        return results
    
    def _extract_from_structured_data(self) -> List[Dict]:
        """Extract tables from structured OCR data"""
        tables = []
        
        if 'tables' not in self.structured_data:
            return tables
        
        for table_idx, table_data in enumerate(self.structured_data['tables']):
            if 'structured_data' in table_data:
                # Process structured table data
                processed_table = self._process_structured_table(
                    table_data['structured_data'], 
                    table_idx
                )
                if processed_table:
                    tables.append(processed_table)
        
        return tables
    
    def _process_structured_table(self, structured_data: List[Dict], table_idx: int) -> Optional[Dict]:
        """Process a single structured table"""
        if not structured_data:
            return None
        
        # Extract headers and data
        headers = []
        data_rows = []
        
        # Try to identify header row
        header_row_idx = self._identify_header_row(structured_data)
        
        if header_row_idx is not None:
            headers = structured_data[header_row_idx].get('cells', [])
            data_rows = structured_data[header_row_idx + 1:]
        else:
            # No clear header, treat first row as header
            if structured_data:
                headers = structured_data[0].get('cells', [])
                data_rows = structured_data[1:]
        
        # Clean and process data
        processed_rows = []
        for row in data_rows:
            cells = row.get('cells', [])
            if cells and any(str(cell).strip() for cell in cells):
                processed_rows.append([str(cell).strip() for cell in cells])
        
        if not processed_rows:
            return None
        
        # Determine table type
        table_type = self._classify_table_type(headers, processed_rows)
        
        return {
            'table_index': table_idx,
            'table_type': table_type,
            'headers': [str(h).strip() for h in headers],
            'data': processed_rows,
            'row_count': len(processed_rows),
            'column_count': len(headers),
            'confidence_score': self._calculate_table_confidence(headers, processed_rows)
        }
    
    def _identify_header_row(self, structured_data: List[Dict]) -> Optional[int]:
        """Identify which row contains headers"""
        for idx, row in enumerate(structured_data):
            cells = row.get('cells', [])
            cell_text = ' '.join(str(cell).upper() for cell in cells)
            
            # Look for header indicators
            header_keywords = [
                'ORIGIN', 'DESTINATION', 'RATE', 'CHARGE', 'COMMODITY', 
                'STCC', 'EQUIPMENT', 'TRAIN', 'ROUTE', 'PROVISION'
            ]
            
            if any(keyword in cell_text for keyword in header_keywords):
                return idx
        
        return None
    
    def _classify_table_type(self, headers: List[str], data: List[List[str]]) -> str:
        """Classify the type of table based on headers and content"""
        header_text = ' '.join(str(h).upper() for h in headers)
        
        # Rate table indicators
        if any(term in header_text for term in ['RATE', 'CHARGE', 'PRICE', 'ORIGIN', 'DESTINATION']):
            return 'rate_table'
        
        # Commodity table indicators
        if any(term in header_text for term in ['COMMODITY', 'STCC', 'PRODUCT']):
            return 'commodity_table'
        
        # Equipment/provision table indicators
        if any(term in header_text for term in ['EQUIPMENT', 'PROVISION', 'NOTE', 'CONDITION']):
            return 'provision_table'
        
        # Check data content for classification
        data_text = ' '.join(' '.join(row) for row in data[:3]).upper()  # First 3 rows
        
        if any(term in data_text for term in ['$', 'USD', 'CAD', 'DOLLAR']):
            return 'rate_table'
        
        if re.search(r'\d{2}\s+\d{3}\s+\d{2}', data_text):  # STCC pattern
            return 'commodity_table'
        
        return 'general_table'
    
    def _calculate_table_confidence(self, headers: List[str], data: List[List[str]]) -> float:
        """Calculate confidence score for table extraction quality"""
        score = 0.0
        total_checks = 0
        
        # Check 1: Headers are meaningful
        total_checks += 1
        if headers and any(len(str(h).strip()) > 2 for h in headers):
            score += 1.0
        
        # Check 2: Data consistency
        total_checks += 1
        if data:
            expected_cols = len(headers) if headers else len(data[0])
            consistent_rows = sum(1 for row in data if len(row) == expected_cols)
            if consistent_rows / len(data) > 0.8:  # 80% consistency
                score += 1.0
        
        # Check 3: Data quality (non-empty cells)
        total_checks += 1
        if data:
            non_empty_cells = sum(1 for row in data for cell in row if str(cell).strip())
            total_cells = sum(len(row) for row in data)
            if total_cells > 0 and non_empty_cells / total_cells > 0.5:  # 50% non-empty
                score += 1.0
        
        return score / total_checks if total_checks > 0 else 0.0
    
    def _extract_rate_tables(self) -> List[Dict]:
        """Extract rate tables using pattern matching"""
        rate_tables = []
        
        # Pattern 1: Origin-Destination-Rate format
        rate_pattern1 = self._extract_origin_destination_rates()
        if rate_pattern1:
            rate_tables.extend(rate_pattern1)
        
        # Pattern 2: Rate category tables (A, B, C columns)
        rate_pattern2 = self._extract_rate_category_tables()
        if rate_pattern2:
            rate_tables.extend(rate_pattern2)
        
        # Pattern 3: Train type rate tables
        rate_pattern3 = self._extract_train_type_rates()
        if rate_pattern3:
            rate_tables.extend(rate_pattern3)
        
        return rate_tables
    
    def _extract_origin_destination_rates(self) -> List[Dict]:
        """Extract origin-destination rate tables"""
        tables = []
        current_table = None
        
        # Look for table headers
        for line_idx, line in enumerate(self.lines):
            line_upper = line.upper().strip()
            
            # Detect rate table header
            if any(pattern in line_upper for pattern in [
                'ORIGIN.*DESTINATION.*RATE',
                'FROM.*TO.*CHARGE',
                'ORIGIN.*DESTINATION.*PRICE'
            ]):
                # Start new table
                if current_table:
                    tables.append(current_table)
                
                current_table = {
                    'table_type': 'origin_destination_rate',
                    'start_line': line_idx,
                    'headers': self._parse_header_line(line),
                    'data': [],
                    'confidence_score': 0.0
                }
                continue
            
            # If we're in a table, try to extract data
            if current_table:
                rate_data = self._parse_rate_line(line)
                if rate_data:
                    current_table['data'].append(rate_data)
                elif line.strip() == '' or '---' in line:
                    # End of table
                    if current_table['data']:
                        current_table['end_line'] = line_idx
                        current_table['row_count'] = len(current_table['data'])
                        current_table['confidence_score'] = self._calculate_rate_table_confidence(current_table)
                        tables.append(current_table)
                    current_table = None
        
        # Add final table if exists
        if current_table and current_table['data']:
            current_table['end_line'] = len(self.lines)
            current_table['row_count'] = len(current_table['data'])
            current_table['confidence_score'] = self._calculate_rate_table_confidence(current_table)
            tables.append(current_table)
        
        return tables
    
    def _parse_header_line(self, line: str) -> List[str]:
        """Parse header line to extract column names"""
        # Split by multiple spaces or common separators
        headers = re.split(r'\s{2,}|\t|\|', line.strip())
        return [h.strip() for h in headers if h.strip()]
    
    def _parse_rate_line(self, line: str) -> Optional[Dict]:
        """Parse a line to extract rate information"""
        line = line.strip()
        if not line or len(line) < 10:
            return None
        
        # Pattern for origin-destination-rate
        patterns = [
            # Full pattern: ORIGIN DESTINATION RATE
            r'([A-Z][A-Za-z\s,]+?)\s+([A-Z][A-Za-z\s,]+?)\s+\$?(\d+(?:\.\d{2})?)',
            # Pattern with state codes: CITY ST CITY ST RATE
            r'([A-Z\s]+[A-Z]{2})\s+([A-Z\s]+[A-Z]{2})\s+\$?(\d+(?:\.\d{2})?)',
            # Simple pattern: TEXT TEXT RATE
            r'(\w+(?:\s+\w+)*)\s+(\w+(?:\s+\w+)*)\s+\$?(\d+(?:\.\d{2})?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return {
                    'origin': match.group(1).strip(),
                    'destination': match.group(2).strip(),
                    'rate': match.group(3),
                    'raw_line': line
                }
        
        # Check if line contains rate information even if pattern doesn't match exactly
        if re.search(r'\$?\d+\.\d{2}|\$\d+', line):
            parts = re.split(r'\s{2,}|\t', line)
            if len(parts) >= 2:
                return {
                    'origin': parts[0].strip() if len(parts) > 0 else '',
                    'destination': parts[1].strip() if len(parts) > 1 else '',
                    'rate': self._extract_rate_value(line),
                    'raw_line': line,
                    'additional_data': parts[2:] if len(parts) > 2 else []
                }
        
        return None
    
    def _extract_rate_value(self, text: str) -> str:
        """Extract rate value from text"""
        rate_match = re.search(r'\$?(\d+(?:\.\d{2})?)', text)
        return rate_match.group(1) if rate_match else ''
    
    def _calculate_rate_table_confidence(self, table: Dict) -> float:
        """Calculate confidence score for rate table"""
        if not table.get('data'):
            return 0.0
        
        score = 0.0
        checks = 0
        
        # Check 1: All rows have rate values
        checks += 1
        rows_with_rates = sum(1 for row in table['data'] if row.get('rate'))
        if rows_with_rates / len(table['data']) > 0.8:
            score += 1.0
        
        # Check 2: Origin/destination fields are populated
        checks += 1
        rows_with_locations = sum(1 for row in table['data'] 
                                 if row.get('origin') and row.get('destination'))
        if rows_with_locations / len(table['data']) > 0.6:
            score += 1.0
        
        # Check 3: Rate values are reasonable (numeric)
        checks += 1
        numeric_rates = sum(1 for row in table['data'] 
                           if row.get('rate') and re.match(r'^\d+(\.\d{2})?$', str(row.get('rate'))))
        if numeric_rates / len(table['data']) > 0.8:
            score += 1.0
        
        return score / checks if checks > 0 else 0.0
    
    def _extract_rate_category_tables(self) -> List[Dict]:
        """Extract rate tables with category columns (A, B, C, etc.)"""
        tables = []
        
        # Look for category-based rate tables
        for line_idx, line in enumerate(self.lines):
            if re.search(r'\b[A-E]\s+[A-E]\s+[A-E]\b', line) or 'COLUMN A' in line.upper():
                # Found category table header
                table = {
                    'table_type': 'rate_category',
                    'start_line': line_idx,
                    'headers': self._parse_header_line(line),
                    'data': [],
                    'categories': self._extract_rate_categories(line)
                }
                
                # Extract data rows
                for data_line_idx in range(line_idx + 1, min(line_idx + 20, len(self.lines))):
                    data_line = self.lines[data_line_idx]
                    if not data_line.strip() or '---' in data_line:
                        break
                    
                    category_data = self._parse_category_rate_line(data_line, table['categories'])
                    if category_data:
                        table['data'].append(category_data)
                
                if table['data']:
                    table['row_count'] = len(table['data'])
                    table['confidence_score'] = self._calculate_rate_table_confidence(table)
                    tables.append(table)
        
        return tables
    
    def _extract_rate_categories(self, line: str) -> List[str]:
        """Extract rate category identifiers from header line"""
        categories = []
        
        # Look for single letter categories
        matches = re.findall(r'\b([A-E])\b', line.upper())
        if matches:
            categories.extend(matches)
        
        # Look for column designations
        column_matches = re.findall(r'COLUMN\s+([A-E])', line.upper())
        if column_matches:
            categories.extend(column_matches)
        
        return categories
    
    def _parse_category_rate_line(self, line: str, categories: List[str]) -> Optional[Dict]:
        """Parse a line with category-based rates"""
        if not line.strip():
            return None
        
        # Split line into components
        parts = re.split(r'\s{2,}|\t', line.strip())
        
        if len(parts) < 3:  # Need at least origin, destination, and one rate
            return None
        
        result = {
            'origin': parts[0].strip(),
            'destination': parts[1].strip() if len(parts) > 1 else '',
            'rates': {},
            'raw_line': line
        }
        
        # Map remaining parts to categories
        rate_parts = parts[2:]
        for i, rate_part in enumerate(rate_parts):
            if i < len(categories):
                rate_value = self._extract_rate_value(rate_part)
                if rate_value:
                    result['rates'][categories[i]] = rate_value
        
        return result if result['rates'] else None
    
    def _extract_train_type_rates(self) -> List[Dict]:
        """Extract rates organized by train type"""
        tables = []
        
        train_types = [
            'SINGLE CAR', 'UNIT TRAIN', 'SPLIT TRAIN', 
            '25 CAR', '50 CAR', '100 CAR', '134 CAR',
            'LOW CAP', 'HIGH CAP'
        ]
        
        for line_idx, line in enumerate(self.lines):
            line_upper = line.upper()
            
            # Check if line contains train type indicators
            found_types = [tt for tt in train_types if tt in line_upper]
            
            if found_types and ('RATE' in line_upper or '$' in line):
                table = {
                    'table_type': 'train_type_rate',
                    'start_line': line_idx,
                    'train_types': found_types,
                    'data': [],
                    'headers': self._parse_header_line(line)
                }
                
                # Extract associated rate data
                for data_idx in range(line_idx, min(line_idx + 10, len(self.lines))):
                    data_line = self.lines[data_idx]
                    rate_info = self._parse_train_type_rate_line(data_line, found_types)
                    if rate_info:
                        table['data'].append(rate_info)
                
                if table['data']:
                    table['row_count'] = len(table['data'])
                    table['confidence_score'] = self._calculate_rate_table_confidence(table)
                    tables.append(table)
        
        return tables
    
    def _parse_train_type_rate_line(self, line: str, train_types: List[str]) -> Optional[Dict]:
        """Parse line containing train type and rate information"""
        if not line.strip():
            return None
        
        rate_value = self._extract_rate_value(line)
        if not rate_value:
            return None
        
        # Determine which train type this rate applies to
        line_upper = line.upper()
        applicable_types = [tt for tt in train_types if tt in line_upper]
        
        return {
            'train_types': applicable_types,
            'rate': rate_value,
            'raw_line': line.strip(),
            'description': line.strip()
        }
    
    def _extract_commodity_tables(self) -> List[Dict]:
        """Extract commodity and STCC code tables"""
        tables = []
        
        # Look for commodity sections
        for line_idx, line in enumerate(self.lines):
            line_upper = line.upper()
            
            if any(keyword in line_upper for keyword in ['COMMODITY', 'STCC', 'PRODUCT']):
                table = {
                    'table_type': 'commodity',
                    'start_line': line_idx,
                    'data': [],
                    'headers': self._parse_header_line(line) if any(h in line_upper for h in ['NAME', 'CODE', 'DESCRIPTION']) else []
                }
                
                # Extract commodity data from following lines
                for data_idx in range(line_idx + 1, min(line_idx + 15, len(self.lines))):
                    data_line = self.lines[data_idx]
                    commodity_info = self._parse_commodity_line(data_line)
                    if commodity_info:
                        table['data'].append(commodity_info)
                    elif not data_line.strip():
                        break
                
                if table['data']:
                    table['row_count'] = len(table['data'])
                    table['confidence_score'] = self._calculate_commodity_confidence(table)
                    tables.append(table)
        
        return tables
    
    def _parse_commodity_line(self, line: str) -> Optional[Dict]:
        """Parse line to extract commodity information"""
        if not line.strip() or len(line.strip()) < 5:
            return None
        
        # Look for STCC codes (format: XX XXX XX)
        stcc_match = re.search(r'(\d{2}\s+\d{3}\s+\d{2})', line)
        
        if stcc_match:
            stcc_code = stcc_match.group(1)
            # Extract commodity name (text before or after STCC)
            name_part = line.replace(stcc_code, '').strip()
            
            return {
                'name': name_part,
                'stcc_code': stcc_code,
                'raw_line': line.strip()
            }
        
        # Check for commodity names without STCC codes
        commodity_keywords = [
            'WHEAT', 'GRAIN', 'CORN', 'SOYBEAN', 'BARLEY', 'FEED',
            'FLOUR', 'MEAL', 'BRAN', 'SHORTS', 'SCREENINGS'
        ]
        
        line_upper = line.upper()
        if any(keyword in line_upper for keyword in commodity_keywords):
            return {
                'name': line.strip(),
                'stcc_code': '',
                'raw_line': line.strip()
            }
        
        return None
    
    def _calculate_commodity_confidence(self, table: Dict) -> float:
        """Calculate confidence for commodity table"""
        if not table.get('data'):
            return 0.0
        
        score = 0.0
        checks = 0
        
        # Check 1: Items have names
        checks += 1
        named_items = sum(1 for item in table['data'] if item.get('name'))
        if named_items / len(table['data']) > 0.8:
            score += 1.0
        
        # Check 2: Some items have STCC codes
        checks += 1
        items_with_stcc = sum(1 for item in table['data'] if item.get('stcc_code'))
        if items_with_stcc > 0:
            score += 1.0
        
        return score / checks if checks > 0 else 0.0
    
    def _extract_note_tables(self) -> List[Dict]:
        """Extract notes, provisions, and conditions tables"""
        tables = []
        
        # Look for notes sections
        note_indicators = ['NOTE', 'PROVISION', 'CONDITION', 'EQUIPMENT', 'ASTERISK']
        
        for line_idx, line in enumerate(self.lines):
            line_upper = line.upper()
            
            if any(indicator in line_upper for indicator in note_indicators):
                table = {
                    'table_type': 'notes_provisions',
                    'start_line': line_idx,
                    'data': [],
                    'note_type': self._determine_note_type(line)
                }
                
                # Extract note data
                for data_idx in range(line_idx, min(line_idx + 20, len(self.lines))):
                    data_line = self.lines[data_idx]
                    note_info = self._parse_note_line(data_line)
                    if note_info:
                        table['data'].append(note_info)
                
                if table['data']:
                    table['row_count'] = len(table['data'])
                    table['confidence_score'] = len(table['data']) / 20  # Simple confidence
                    tables.append(table)
        
        return tables
    
    def _determine_note_type(self, line: str) -> str:
        """Determine the type of note section"""
        line_upper = line.upper()
        
        if 'EQUIPMENT' in line_upper:
            return 'equipment'
        elif 'PROVISION' in line_upper:
            return 'provision'
        elif 'CONDITION' in line_upper:
            return 'condition'
        elif '*' in line:
            return 'asterisk'
        else:
            return 'general'
    
    def _parse_note_line(self, line: str) -> Optional[Dict]:
        """Parse line to extract note information"""
        line = line.strip()
        if not line or len(line) < 5:
            return None
        
        # Look for numbered notes
        numbered_match = re.match(r'^(\d+)\.?\s*(.+)', line)
        if numbered_match:
            return {
                'code': numbered_match.group(1),
                'text': numbered_match.group(2),
                'type': 'numbered',
                'raw_line': line
            }
        
        # Look for asterisk notes
        asterisk_match = re.match(r'^\*+\s*(.+)', line)
        if asterisk_match:
            return {
                'code': '*',
                'text': asterisk_match.group(1),
                'type': 'asterisk',
                'raw_line': line
            }
        
        # General notes
        if any(keyword in line.upper() for keyword in ['SUBJECT TO', 'APPLIES', 'MINIMUM', 'MAXIMUM']):
            return {
                'code': '',
                'text': line,
                'type': 'general',
                'raw_line': line
            }
        
        return None
    
    def _extract_general_tables(self) -> List[Dict]:
        """Extract other table-like structures"""
        tables = []
        
        # Look for lines that might be table headers
        for line_idx, line in enumerate(self.lines):
            # Skip if we've already processed this area
            if any(table.get('start_line', -1) <= line_idx <= table.get('end_line', -1) 
                  for table_list in [self.rate_tables, self.commodity_tables, self.note_tables] 
                  for table in table_list):
                continue
            
            # Look for table-like patterns
            if self._looks_like_table_header(line):
                table = {
                    'table_type': 'general',
                    'start_line': line_idx,
                    'headers': self._parse_header_line(line),
                    'data': []
                }
                
                # Extract following rows
                for data_idx in range(line_idx + 1, min(line_idx + 10, len(self.lines))):
                    data_line = self.lines[data_idx]
                    if not data_line.strip() or '---' in data_line:
                        break
                    
                    if self._looks_like_table_row(data_line, len(table['headers'])):
                        row_data = self._parse_general_table_row(data_line)
                        if row_data:
                            table['data'].append(row_data)
                
                if len(table['data']) >= 2:  # At least 2 data rows
                    table['end_line'] = line_idx + len(table['data']) + 1
                    table['row_count'] = len(table['data'])
                    table['confidence_score'] = 0.5  # Medium confidence for general tables
                    tables.append(table)
        
        return tables
    
    def _looks_like_table_header(self, line: str) -> bool:
        """Check if line looks like a table header"""
        line = line.strip().upper()
        
        # Must have multiple words
        words = line.split()
        if len(words) < 2:
            return False
        
        # Common table header indicators
        header_indicators = [
            'ITEM', 'TYPE', 'CODE', 'DESCRIPTION', 'VALUE', 'AMOUNT',
            'FROM', 'TO', 'RATE', 'CHARGE', 'EQUIPMENT', 'ROUTE'
        ]
        
        return any(indicator in line for indicator in header_indicators)
    
    def _looks_like_table_row(self, line: str, expected_columns: int) -> bool:
        """Check if line looks like a table data row"""
        parts = re.split(r'\s{2,}|\t', line.strip())
        
        # Should have reasonable number of parts
        return 2 <= len(parts) <= max(expected_columns + 2, 6)
    
    def _parse_general_table_row(self, line: str) -> Optional[List[str]]:
        """Parse general table row"""
        if not line.strip():
            return None
        
        parts = re.split(r'\s{2,}|\t', line.strip())
        return [part.strip() for part in parts if part.strip()]
    
    def extract_summary(self) -> Dict[str, Any]:
        """Extract a summary of all table extraction results"""
        all_results = self.extract_all_tables()
        
        summary = {
            'total_tables': all_results['tables_found'],
            'table_types': {
                'rate_tables': len(all_results['rate_tables']),
                'commodity_tables': len(all_results['commodity_tables']),
                'note_tables': len(all_results['note_tables']),
                'general_tables': len(all_results['general_tables']),
                'structured_tables': len(all_results.get('structured_data', []))
            },
            'extraction_quality': {
                'high_confidence_tables': 0,
                'medium_confidence_tables': 0,
                'low_confidence_tables': 0
            },
            'data_extracted': {
                'total_rates': 0,
                'total_commodities': 0,
                'total_notes': 0
            }
        }
        
        # Calculate confidence distribution and data counts
        all_tables = (all_results['rate_tables'] + all_results['commodity_tables'] + 
                     all_results['note_tables'] + all_results['general_tables'])
        
        for table in all_tables:
            confidence = table.get('confidence_score', 0.0)
            if confidence >= 0.8:
                summary['extraction_quality']['high_confidence_tables'] += 1
            elif confidence >= 0.5:
                summary['extraction_quality']['medium_confidence_tables'] += 1
            else:
                summary['extraction_quality']['low_confidence_tables'] += 1
            
            # Count data items
            if table.get('table_type') == 'rate_table' or 'rate' in table.get('table_type', ''):
                summary['data_extracted']['total_rates'] += len(table.get('data', []))
            elif table.get('table_type') == 'commodity':
                summary['data_extracted']['total_commodities'] += len(table.get('data', []))
            elif 'note' in table.get('table_type', ''):
                summary['data_extracted']['total_notes'] += len(table.get('data', []))
        
        return summary

def create_enhanced_table_extractor(ocr_text: str = "", structured_data: Dict = None) -> EnhancedTableExtractor:
    """Factory function to create enhanced table extractor"""
    return EnhancedTableExtractor(ocr_text, structured_data)

# Example usage and testing
if __name__ == "__main__":
    # Test with sample text
    sample_text = """
    CP TARIFF INC.
    ITEM: 70001  REVISION: 5
    
    ORIGIN          DESTINATION     RATE A  RATE B  ROUTE
    VANCOUVER BC    CHICAGO IL      $45.50  $52.75  CP001
    CALGARY AB      MINNEAPOLIS MN  $42.00  $48.25  CP002
    WINNIPEG MB     KANSAS CITY MO  $38.75  $44.50  CP003
    
    COMMODITY: WHEAT
    STCC: 01 137 00
    
    NOTES:
    1. Rates subject to fuel surcharge
    2. Minimum weight 80,000 lbs
    * Equipment owned or leased by railway
    """
    
    extractor = EnhancedTableExtractor(sample_text)
    results = extractor.extract_all_tables()
    summary = extractor.extract_summary()
    
    print("Table Extraction Results:")
    print(f"Total tables found: {results['tables_found']}")
    print(f"Rate tables: {len(results['rate_tables'])}")
    print(f"Commodity tables: {len(results['commodity_tables'])}")
    print(f"Note tables: {len(results['note_tables'])}")
    print("\nSummary:")
    print(json.dumps(summary, indent=2))