import re
import cv2
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any

class TableExtractor:
    """Class for extracting and structuring tables from OCR text of CP Tariff documents."""
    
    def __init__(self, ocr_text: str):
        """Initialize with OCR text containing the table."""
        self.ocr_text = ocr_text
        self.lines = ocr_text.split('\n')
        self.table_data = []
        self.headers = []
    
    def extract(self) -> Dict[str, Any]:
        """Extract the table structure from OCR text.
        
        Returns:
            Dictionary containing table headers and data
        """
        # First, try to identify the table type
        table_type = self._identify_table_type()
        
        if table_type == "origin_destination_rate":
            return self._extract_origin_destination_table()
        elif table_type == "rate_category":
            return self._extract_rate_category_table()
        else:
            # Generic table extraction as fallback
            return self._extract_generic_table()
    
    def _identify_table_type(self) -> str:
        """Try to identify what type of table this is."""
        # Look for common patterns in CP Tariff tables
        
        # Check for origin-destination pattern
        origin_dest_pattern = r"(ORIGIN|FROM).*?(DESTINATION|TO)|CHARGES.*(PER CAR)"
        if re.search(origin_dest_pattern, self.ocr_text, re.IGNORECASE):
            return "origin_destination_rate"
        
        # Check for rate category pattern (A B C D columns)
        rate_cat_pattern = r"(COLUMN A|COLUMN B|COLUMN C|CHARGES PER CAR)"
        if re.search(rate_cat_pattern, self.ocr_text, re.IGNORECASE):
            return "rate_category"
        
        # Default to generic table if no specific pattern is found
        return "generic"
    
    def _extract_origin_destination_table(self) -> Dict[str, Any]:
        """Extract an origin-destination table structure."""
        # Find header line(s)
        header_lines = []
        header_index = -1
        
        # Common header patterns for origin-destination tables
        header_patterns = [
            r"ORIGIN.*DESTINATION",
            r"ORIGIN.*RATE",
            r"FROM.*TO",
            r"ORIGIN.*PROV.*STATION"
        ]
        
        for i, line in enumerate(self.lines):
            for pattern in header_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    header_index = i
                    header_lines.append(line)
                    # Check if next line is also part of the header
                    if i+1 < len(self.lines) and re.search(r"(LOW CAP|HIGH CAP|ROUTE|ADDITIONAL|PROVISIONS)", self.lines[i+1], re.IGNORECASE):
                        header_lines.append(self.lines[i+1])
                    break
            if header_index >= 0:
                break
        
        # If we found headers, extract them
        if header_lines:
            # Process headers to extract column names
            header_text = " ".join(header_lines)
            
            # Special case for some common patterns
            if re.search(r"(LOW CAP|HIGH CAP)", header_text, re.IGNORECASE):
                self.headers = ["ORIGIN", "DESTINATION", "LOW CAP", "HIGH CAP", "ROUTE", "ADDITIONAL PROVISIONS"]
            elif re.search(r"COLUMN", header_text, re.IGNORECASE):
                self.headers = ["ORIGIN", "DESTINATION", "COLUMN A", "COLUMN B", "COLUMN C", "ROUTE", "ADDITIONAL PROVISIONS"]
            else:
                # Generic header extraction
                self.headers = re.split(r'\s{2,}', header_text.strip())
            
            # Extract data rows
            data_start_index = header_index + len(header_lines)
            data_end_index = len(self.lines)
            
            # Find where the table ends (usually marked by notes or a line of dashes)
            for i in range(data_start_index, len(self.lines)):
                if re.match(r'^[-_]{3,}$', self.lines[i].strip()) or re.match(r'ROUTE', self.lines[i]):
                    data_end_index = i
                    break
            
            # Process data rows
            for i in range(data_start_index, data_end_index):
                line = self.lines[i].strip()
                if not line or line.startswith('----'):
                    continue
                
                # Try to parse the line into columns
                row_data = self._parse_data_row(line)
                if row_data:
                    self.table_data.append(row_data)
        
        # Convert to structured format
        return {
            "headers": self.headers,
            "rows": [dict(zip(self.headers, row)) for row in self.table_data] if self.headers else [],
            "raw_data": self.table_data
        }
    
    def _extract_rate_category_table(self) -> Dict[str, Any]:
        """Extract a rate category table structure."""
        # These tables often have columns A, B, C, D for different equipment types
        
        # Find header line
        header_index = -1
        for i, line in enumerate(self.lines):
            if re.search(r"(A\s+B\s+C|CHARGES PER CAR)", line, re.IGNORECASE):
                header_index = i
                break
        
        if header_index >= 0:
            # Extract headers
            header_line = self.lines[header_index]
            
            # Determine if the header has letter columns (A, B, C) or named columns
            if re.search(r"\b[A-D]\b", header_line):
                # Letter columns
                self.headers = ["ORIGIN", "DESTINATION", "A", "B", "C", "ROUTE", "ADDITIONAL PROVISIONS"]
            else:
                # Try to split the header into columns
                self.headers = re.split(r'\s{2,}', header_line.strip())
            
            # Extract data rows
            data_start_index = header_index + 1
            data_end_index = len(self.lines)
            
            # Find where the table ends
            for i in range(data_start_index, len(self.lines)):
                if re.match(r'^[-_]{3,}$', self.lines[i].strip()) or re.match(r'ROUTE', self.lines[i]):
                    data_end_index = i
                    break
            
            # Process data rows
            for i in range(data_start_index, data_end_index):
                line = self.lines[i].strip()
                if not line or line.startswith('----'):
                    continue
                
                # Parse the data row
                row_data = self._parse_data_row(line)
                if row_data:
                    self.table_data.append(row_data)
        
        # Convert to structured format
        return {
            "headers": self.headers,
            "rows": [dict(zip(self.headers, row)) for row in self.table_data] if self.headers else [],
            "raw_data": self.table_data
        }
    
    def _extract_generic_table(self) -> Dict[str, Any]:
        """Extract a generic table structure as fallback."""
        # For unknown table formats, try a more generic approach
        
        # Find potential header lines (usually have all caps or multiple spaces)
        header_candidates = []
        for i, line in enumerate(self.lines):
            # Check if line is in all caps or has multiple spaces between words
            if line.isupper() or re.search(r'\s{2,}', line):
                header_candidates.append((i, line))
        
        # If we found potential headers, try to extract the table
        if header_candidates:
            # Start with the first candidate header
            header_index, header_line = header_candidates[0]
            
            # Extract headers
            self.headers = re.split(r'\s{2,}', header_line.strip())
            
            # Extract data rows
            data_start_index = header_index + 1
            
            # Process data rows
            for i in range(data_start_index, len(self.lines)):
                line = self.lines[i].strip()
                if not line or line.startswith('----'):
                    continue
                
                # Check if this might be a new section header
                if line.isupper() and i > data_start_index + 3:
                    break
                
                # Parse the data row
                row_data = self._parse_data_row(line)
                if row_data:
                    self.table_data.append(row_data)
        
        # Convert to structured format
        return {
            "headers": self.headers,
            "rows": [dict(zip(self.headers, row)) for row in self.table_data] if self.headers else [],
            "raw_data": self.table_data
        }
    
    def _parse_data_row(self, line: str) -> List[str]:
        """Parse a data row into separate columns."""
        # This is tricky because OCR can mess up spacing
        
        # Method 1: Try splitting by multiple spaces
        columns = re.split(r'\s{2,}', line.strip())
        
        # Check if this looks reasonable (should have at least 3 columns for CP Tariff tables)
        if len(columns) >= 3:
            return columns
        
        # Method 2: For tables with $ values, try to detect column boundaries by currency symbols
        dollar_matches = list(re.finditer(r'\$\d+', line))
        if dollar_matches and len(dollar_matches) >= 2:
            columns = []
            
            # Extract text before first dollar sign
            first_dollar_pos = dollar_matches[0].start()
            prefix = line[:first_dollar_pos].strip()
            
            # Split prefix into origin/destination if needed
            if len(prefix.split()) > 3:  # Likely contains both origin and destination
                # Try to split at common province codes
                province_match = re.search(r'\b(AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT|AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b', prefix)
                
                if province_match:
                    province_pos = province_match.start()
                    columns.append(prefix[:province_pos].strip())
                    columns.append(prefix[province_pos:].strip())
                else:
                    # Just split in half as a fallback
                    midpoint = len(prefix) // 2
                    columns.append(prefix[:midpoint].strip())
                    columns.append(prefix[midpoint:].strip())
            else:
                columns.append(prefix)
            
            # Extract dollar values and text between them
            for i in range(len(dollar_matches)):
                current_match = dollar_matches[i]
                
                # Find the end of the current number
                current_end = current_match.end()
                while current_end < len(line) and line[current_end].isdigit():
                    current_end += 1
                
                # Extract this value
                columns.append(line[current_match.start():current_end].strip())
                
                # Extract text between this value and the next one
                if i < len(dollar_matches) - 1:
                    next_match = dollar_matches[i + 1]
                    between_text = line[current_end:next_match.start()].strip()
                    if between_text:
                        columns.append(between_text)
            
            # Extract any text after the last dollar value
            if dollar_matches[-1].end() < len(line):
                columns.append(line[dollar_matches[-1].end():].strip())
            
            return columns
        
        # Method 3: Try to match the expected pattern for CP Tariff tables
        
        # Origin-destination pattern
        origin_dest_match = re.match(r'([A-Z ]+)\s+([A-Z]{2})\s+(\d+)\s+(\$[\d,\.]+)\s+(\$[\d,\.]+)\s+(\d+)', line)
        if origin_dest_match:
            return list(origin_dest_match.groups())
        
        # If all methods fail, just return the line as a single column
        return [line]