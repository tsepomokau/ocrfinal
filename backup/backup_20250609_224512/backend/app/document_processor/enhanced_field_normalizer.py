import os
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Handle OpenAI import gracefully
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

logger = logging.getLogger(__name__)

class EnhancedFieldNormalizer:
    """Enhanced field normalizer with AI and rule-based extraction"""
    
    def __init__(self, ocr_text: str = "", pdf_name: str = ""):
        """
        Initialize the enhanced field normalizer
        Args:
            ocr_text: OCR extracted text (for backward compatibility)
            pdf_name: PDF filename (for backward compatibility)
        """
        self.ocr_text = ocr_text
        self.pdf_name = pdf_name
        self.openai_client = None
        self.ai_available = False
        self.setup_openai()
    
    def setup_openai(self):
        """Setup OpenAI client - FIXED VERSION"""
        if not OPENAI_AVAILABLE:
            logger.warning("⚠️ OpenAI library not available")
            return
            
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key and api_key.strip() and not api_key.startswith('your_'):
                # FIXED: Proper OpenAI client initialization for v1.0+
                self.openai_client = OpenAI(api_key=api_key)
                self.ai_available = True
                logger.info("✅ OpenAI API configured successfully")
            else:
                logger.warning("⚠️ OPENAI_API_KEY not configured, using rule-based extraction only")
                self.ai_available = False
        except Exception as e:
            logger.error(f"❌ Error setting up OpenAI: {e}")
            self.ai_available = False
    
    def normalize_tariff_data(self) -> Dict[str, Any]:
        """
        Main method for normalizing tariff data - for backward compatibility
        """
        if self.ocr_text:
            raw_data = {'raw_text': self.ocr_text}
            return self.enhance_extracted_data(raw_data)
        else:
            logger.warning("No OCR text provided for normalization")
            return self._get_empty_result()
    
    def enhance_extracted_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance extracted data using AI and rule-based methods"""
        
        # Always start with rule-based enhancement
        enhanced_data = self._rule_based_enhancement(raw_data)
        
        # Try AI enhancement if available
        if self.ai_available and self.openai_client:
            try:
                logger.info("🤖 Attempting AI-powered extraction...")
                ai_enhanced = self._ai_enhanced_extraction(raw_data)
                
                # Merge AI results with rule-based results
                enhanced_data = self._merge_extraction_results(enhanced_data, ai_enhanced)
                logger.info("✅ AI enhancement completed")
                
            except Exception as e:
                logger.warning(f"⚠️ AI extraction failed: {e}")
                logger.info("🔄 Falling back to rule-based extraction...")
        else:
            logger.info("🔄 Using rule-based extraction only (AI not available)")
        
        # Add metadata
        enhanced_data['pdf_name'] = self.pdf_name
        enhanced_data['processing_method'] = 'AI_ENHANCED' if self.ai_available else 'RULE_BASED'
        enhanced_data['processing_timestamp'] = datetime.now().isoformat()
        
        return enhanced_data
    
    def _ai_enhanced_extraction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Use OpenAI to enhance field extraction - FIXED VERSION"""
        if not self.openai_client:
            raise Exception("OpenAI client not available")
        
        raw_text = data.get('raw_text', '')
        if not raw_text.strip():
            raise Exception("No text available for AI processing")
        
        # FIXED: Updated to work with OpenAI >= 1.0.0 API
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a tariff document parser. Extract structured data from Canadian Pacific Railway tariff documents.
                        
Return a JSON object with these fields:
- header: {item_number, revision, cprs_number, issue_date, effective_date, expiration_date, change_description}
- rates: [{origin, destination, rate_value, commodity, equipment_type}]
- notes: [{type, description, applies_to}]
- commodities: [{name, code, classification}]

Only return valid JSON, no explanations."""
                    },
                    {
                        "role": "user", 
                        "content": f"Extract data from this tariff document:\n\n{raw_text[:3000]}"
                    }
                ],
                max_tokens=1500,
                temperature=0.1,
                timeout=30
            )
            
            # FIXED: Updated response handling for new API
            ai_result = response.choices[0].message.content
            
            # Parse JSON response
            try:
                parsed_result = json.loads(ai_result)
                logger.info("✅ AI extraction successful")
                return parsed_result
            except json.JSONDecodeError as e:
                logger.error(f"❌ AI returned invalid JSON: {e}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Error calling OpenAI API: {e}")
            raise
    
    def _rule_based_enhancement(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced rule-based extraction - WORKING VERSION"""
        logger.info("🔄 Using enhanced rule-based extraction...")
        
        raw_text = data.get('raw_text', '')
        enhanced_data = {
            'header': {},
            'commodities': [],
            'rates': [],
            'notes': [],
            'origin_info': '',
            'destination_info': '',
            'currency': 'USD',
            'route_info': '',
            'equipment_info': ''
        }
        
        if not raw_text:
            return enhanced_data
        
        # Enhanced header extraction
        enhanced_data['header'] = self._extract_header_fields(raw_text)
        
        # Enhanced rates extraction  
        enhanced_data['rates'] = self._extract_rates(raw_text)
        
        # Enhanced notes extraction
        enhanced_data['notes'] = self._extract_notes(raw_text)
        
        # Enhanced commodities extraction
        enhanced_data['commodities'] = self._extract_commodities(raw_text)
        
        # Extract origin/destination
        origin, destination = self._extract_origin_destination(raw_text)
        enhanced_data['origin_info'] = origin
        enhanced_data['destination_info'] = destination
        
        # Extract currency
        enhanced_data['currency'] = self._extract_currency(raw_text)
        
        logger.info(f"📊 Rule-based extraction complete:")
        logger.info(f"   - Header fields: {len(enhanced_data['header'])}")
        logger.info(f"   - Commodities: {len(enhanced_data['commodities'])}")
        logger.info(f"   - Rates: {len(enhanced_data['rates'])}")
        logger.info(f"   - Notes: {len(enhanced_data['notes'])}")
        
        return enhanced_data
    
    def _extract_header_fields(self, text: str) -> Dict[str, Any]:
        """Extract header fields using enhanced patterns"""
        header = {}
        
        patterns = {
            'item_number': [
                r'ITEM\s+(\d+)',
                r'Item\s+Number:?\s*(\d+)',
                r'(?:^|\s)(\d{5,6})(?:\s|$)'
            ],
            'revision': [
                r'REVISION\s+(\d+)',
                r'Rev\.?\s*(\d+)',
                r'Revision:?\s*(\d+)'
            ],
            'cprs_number': [
                r'CPRS\s+(\d+-[A-Z])',
                r'(\d{4}-[A-Z])',
                r'CPRS[:\s]+(\d+-[A-Z])'
            ],
            'issue_date': [
                r'ISSUE\s+DATE[:\s]+(\d{4}-\d{2}-\d{2})',
                r'Issued:?\s*(\d{4}-\d{2}-\d{2})',
                r'(\d{4}-\d{2}-\d{2})'
            ],
            'effective_date': [
                r'EFFECTIVE\s+DATE[:\s]+(\d{4}-\d{2}-\d{2})',
                r'Effective:?\s*(\d{4}-\d{2}-\d{2})'
            ],
            'expiration_date': [
                r'EXPIR(?:ATION|Y)\s+DATE[:\s]+(\d{4}-\d{2}-\d{2})',
                r'Expires?:?\s*(\d{4}-\d{2}-\d{2})'
            ],
            'change_description': [
                r'CHANGE\s+DESCRIPTION[:\s]+([A-Z\s]+)',
                r'(?:RENEWAL|AMENDMENT|NEW|CANCELLATION)'
            ]
        }
        
        for field, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip() if match.groups() else match.group(0).strip()
                    header[field] = value
                    logger.info(f"✅ Found {field}: {value}")
                    break
        
        return header
    
    def _extract_rates(self, text: str) -> List[Dict[str, Any]]:
        """Extract rate information"""
        rates = []
        
        # Look for rate patterns
        rate_patterns = [
            r'([A-Z\s]+)\s+-\s+\$(\d+\.?\d*)',
            r'TO\s+DESTINATION\s+([A-Z])\s+([A-Z])\s+([A-Z])\s+ROUTE\s+([^$]+)\$(\d+\.?\d*)',
            r'(\w+(?:\s+\w+)*)\s+\$(\d+(?:\.\d+)?)'
        ]
        
        for pattern in rate_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if len(match.groups()) >= 2:
                    rate = {
                        'origin': match.group(1).strip() if len(match.groups()) > 1 else '',
                        'destination': match.group(2).strip() if len(match.groups()) > 2 else '',
                        'rate_amount': match.group(-1).strip(),  # Last group is usually the rate
                        'currency': 'CAD',
                        'rate_category': 'standard',
                        'train_type': '',
                        'car_capacity_type': '',
                        'route_code': '',
                        'additional_provisions': ''
                    }
                    rates.append(rate)
                    logger.info(f"✅ Found rate: {rate}")
        
        return rates
    
    def _extract_notes(self, text: str) -> List[Dict[str, Any]]:
        """Extract notes and conditions"""
        notes = []
        
        # Look for equipment notes, conditions, etc.
        note_patterns = [
            r'(RAILWAY/SHIPPER OWNED/LEASED [^.]+)',
            r'(EQUIPMENT:[^.]+)',
            r'(NOTE:[^.]+)',
            r'(CONDITIONS?:[^.]+)'
        ]
        
        for i, pattern in enumerate(note_patterns):
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                note = {
                    'type': 'EQUIPMENT' if 'EQUIPMENT' in match.group(0).upper() else 'GENERAL',
                    'code': f'NOTE_{i+1}',
                    'text': match.group(1).strip(),
                    'sort_order': i
                }
                notes.append(note)
                logger.info(f"✅ Found note ({note['type']}): {note['text'][:50]}...")
        
        return notes
    
    def _extract_commodities(self, text: str) -> List[Dict[str, Any]]:
        """Extract commodity information"""
        commodities = []
        
        # Common commodity patterns
        commodity_patterns = [
            r'COMMODITY[:\s]+([^,\n]+)',
            r'([A-Z\s]+GRAIN[A-Z\s]*)',
            r'([A-Z\s]+WHEAT[A-Z\s]*)',
            r'([A-Z\s]+CORN[A-Z\s]*)'
        ]
        
        for pattern in commodity_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                commodity = {
                    'name': match.group(1).strip(),
                    'stcc_code': '',
                    'description': match.group(1).strip()
                }
                commodities.append(commodity)
        
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
        
        # Fallback patterns
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
    
    def _extract_currency(self, text: str) -> str:
        """Extract currency information"""
        if re.search(r'(CAD|CDN|CANADIAN)', text, re.IGNORECASE):
            return 'CAD'
        elif re.search(r'(USD|US\s+FUNDS|UNITED STATES)', text, re.IGNORECASE):
            return 'USD'
        return 'USD'  # Default
    
    def _merge_extraction_results(self, rule_based: Dict, ai_enhanced: Dict) -> Dict[str, Any]:
        """Merge rule-based and AI extraction results"""
        
        # Start with rule-based results
        merged = rule_based.copy()
        
        # Enhance with AI results where available and better
        if ai_enhanced:
            # Merge headers (AI takes precedence for missing fields)
            if 'header' in ai_enhanced:
                for key, value in ai_enhanced['header'].items():
                    if key not in merged['header'] or not merged['header'][key]:
                        merged['header'][key] = value
            
            # Add AI rates if rule-based found none
            if 'rates' in ai_enhanced and not merged['rates']:
                merged['rates'] = ai_enhanced['rates']
            
            # Add AI notes if rule-based found few
            if 'notes' in ai_enhanced and len(merged['notes']) < 3:
                merged['notes'].extend(ai_enhanced['notes'])
            
            # Add AI commodities if rule-based found none  
            if 'commodities' in ai_enhanced and not merged['commodities']:
                merged['commodities'] = ai_enhanced['commodities']
        
        return merged
    
    def _get_empty_result(self) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            'header': {},
            'commodities': [],
            'rates': [],
            'notes': [],
            'origin_info': '',
            'destination_info': '',
            'currency': 'USD',
            'route_info': '',
            'equipment_info': '',
            'pdf_name': self.pdf_name,
            'processing_method': 'EMPTY',
            'processing_timestamp': datetime.now().isoformat()
        }

    # Alias method for backward compatibility
    def normalize(self) -> Dict[str, Any]:
        """Alias for normalize_tariff_data method"""
        return self.normalize_tariff_data()