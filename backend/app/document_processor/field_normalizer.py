import re
import json
from typing import Dict, List, Any, Optional
import openai

from config import OPENAI_API_KEY

class FieldNormalizer:
    """Class for normalizing field names and values from OCR text using ChatGPT."""
    
    def __init__(self, ocr_text: str):
        """Initialize with OCR text."""
        self.ocr_text = ocr_text
        openai.api_key = OPENAI_API_KEY
    
    def normalize(self) -> Dict[str, Any]:
        """Normalize fields and values using ChatGPT."""
        # Construct the prompt
        prompt = self._create_prompt()
        
        # Call OpenAI API
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert in processing rail tariff documents. Extract structured data from OCR text of CP Tariff documents."
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
            return result
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            # Fallback to simple extraction
            return self._extract_fields_simple()
    
    def _create_prompt(self) -> str:
        """Create a prompt for OpenAI API."""
        return f"""
Extract the following fields from this CP Tariff OCR text, handling inconsistent field names.
For each field, if you can't find it, just leave it empty or null.

Fields to extract:
1. Tariff Item Number (may appear as ITEM, ITEM NUMBER, etc.)
2. Revision Number (may appear as REVISION, REV, etc.)
3. Issue Date (may appear as ISSUED, ISSUE DATE, etc.)
4. Effective Date (may appear as EFFECTIVE, EFFECTIVE DATE, etc.)
5. Expiration Date (may appear as EXPIRES, EXPIRATION DATE, etc.)
6. Commodity Type(s) (may appear as COMMODITY, COMMODITIES, etc.)
7. STCC Codes for commodities
8. Origin(s) (may appear as ORIGIN, FROM, etc.)
9. Destination(s) (may appear as DESTINATION, TO, etc.)
10. Currency (identify if rates are in CAD or USD)
11. Route Information
12. Equipment Types (identify different types like covered hopper cars, etc.)
13. Special Provisions or Notes

Return ONLY valid JSON in this format:
{{
    "header": {{
        "item_number": "...",
        "revision": "...",
        "issue_date": "...",
        "effective_date": "...",
        "expiration_date": "..."
    }},
    "commodities": [
        {{
            "commodity_name": "...",
            "stcc_code": "..."
        }}
    ],
    "origin_info": "...",
    "destination_info": "...",
    "currency": "CAD or USD",
    "equipment_info": "...",
    "route_info": "...",
    "notes": [
        "..."
    ]
}}

OCR TEXT:
{self.ocr_text}
"""
    
    def _extract_fields_simple(self) -> Dict[str, Any]:
        """Simple field extraction as fallback."""
        result = {
            "header": {
                "item_number": "",
                "revision": "",
                "issue_date": "",
                "effective_date": "",
                "expiration_date": ""
            },
            "commodities": [],
            "origin_info": "",
            "destination_info": "",
            "currency": "",
            "equipment_info": "",
            "route_info": "",
            "notes": []
        }
        
        # Extract header info using regex
        item_match = re.search(r'ITEM:\s*(\d+)', self.ocr_text)
        if item_match:
            result["header"]["item_number"] = item_match.group(1)
        
        revision_match = re.search(r'REVISION:\s*(\d+)', self.ocr_text)
        if revision_match:
            result["header"]["revision"] = revision_match.group(1)
        
        issue_match = re.search(r'ISSUED:\s*([A-Z]{3}\s+\d{1,2},\s+\d{4})', self.ocr_text)
        if issue_match:
            result["header"]["issue_date"] = issue_match.group(1)
        
        effective_match = re.search(r'EFFECTIVE:\s*([A-Z]{3}\s+\d{1,2},\s+\d{4})', self.ocr_text)
        if effective_match:
            result["header"]["effective_date"] = effective_match.group(1)
        
        expire_match = re.search(r'EXPIRES:\s*([A-Z]{3}\s+\d{1,2},\s+\d{4})', self.ocr_text)
        if expire_match:
            result["header"]["expiration_date"] = expire_match.group(1)
        
        # Extract commodity info
        commodity_section = re.search(r'COMMODITY:(.+?)(?:_+|ORIGIN:)', self.ocr_text, re.DOTALL)
        if commodity_section:
            commodity_text = commodity_section.group(1)
            stcc_matches = re.findall(r'(\d{2}\s+\d{3}\s+\d{2})', commodity_text)
            
            # Extract commodity names
            lines = commodity_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and not re.match(r'^\d{2}\s+\d{3}\s+\d{2}$', line):
                    # Check if line has STCC code
                    stcc_match = re.search(r'(\d{2}\s+\d{3}\s+\d{2})', line)
                    if stcc_match:
                        commodity_name = line.replace(stcc_match.group(1), '').strip()
                        result["commodities"].append({
                            "commodity_name": commodity_name,
                            "stcc_code": stcc_match.group(1)
                        })
                    elif line:
                        # Just the commodity name
                        result["commodities"].append({
                            "commodity_name": line,
                            "stcc_code": ""
                        })
        
        # Try to determine currency
        if re.search(r'(CAD|CDN)\s+DOLLARS', self.ocr_text, re.IGNORECASE):
            result["currency"] = "CAD"
        elif re.search(r'(USD|U.S.|UNITED STATES)\s+FUNDS', self.ocr_text, re.IGNORECASE):
            result["currency"] = "USD"
        
        # Extract origin information
        origin_match = re.search(r'ORIGIN:\s*(.+?)(?:_+|DESTINATION)', self.ocr_text, re.IGNORECASE | re.DOTALL)
        if origin_match:
            result["origin_info"] = origin_match.group(1).strip()
        
        # Extract destination information
        dest_match = re.search(r'DESTINATION:\s*(.+?)(?:_+|CHARGES)', self.ocr_text, re.IGNORECASE | re.DOTALL)
        if dest_match:
            result["destination_info"] = dest_match.group(1).strip()
        
        # Extract route information
        route_match = re.search(r'ROUTE:\s*(.+?)(?:_+|$)', self.ocr_text, re.IGNORECASE | re.DOTALL)
        if route_match:
            result["route_info"] = route_match.group(1).strip()
        
        # Extract equipment information
        equipment_match = re.search(r'EQUIPMENT:\s*(.+?)(?:_+|$)', self.ocr_text, re.IGNORECASE | re.DOTALL)
        if equipment_match:
            result["equipment_info"] = equipment_match.group(1).strip()
        
        return result