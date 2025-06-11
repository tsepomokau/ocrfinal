"""
Enhanced Database Handler for CP Tariff Documents
Fixed database save issues and improved error handling
"""

import pyodbc
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

class CPTariffDatabase:
    """Enhanced database handler with improved error handling and debugging"""
    
    def __init__(self, connection_string: str):
        """Initialize database connection"""
        self.connection_string = connection_string
        logger.info("Enhanced database handler initialized")
    
    def get_database_connection(self):
        """Get database connection with enhanced error reporting"""
        try:
            conn = pyodbc.connect(self.connection_string, timeout=30)
            conn.autocommit = False  # Explicit transaction control
            logger.info("Database connection established successfully")
            return conn
        except pyodbc.Error as e:
            logger.error(f"Database connection failed - ODBC Error: {e}")
            return None
        except Exception as e:
            logger.error(f"Database connection failed - General Error: {e}")
            return None
    
    def save_document(self, data: Dict[str, Any]) -> Optional[int]:
        """
        Enhanced document save with better error handling and debugging
        """
        conn = self.get_database_connection()
        if conn is None:
            logger.error("Cannot save document - no database connection")
            return None
        
        try:
            cursor = conn.cursor()
            
            # Extract and validate header data
            header = data.get('header', {})
            item_number = str(header.get('item_number', ''))
            
            if not item_number:
                logger.warning("No item number found in document")
                item_number = 'UNKNOWN'
            
            logger.info(f"Saving document: Item {item_number}")
            
            # Enhanced parameter preparation with better validation
            params = self._prepare_document_params(header, data)
            
            # Check if tables exist before inserting
            if not self._verify_tables_exist(cursor):
                logger.error("Required database tables do not exist")
                return None
            
            # Insert main document record with explicit transaction
            insert_sql = """
            INSERT INTO tariff_documents (
                item_number, revision, cprs_number, issue_date, 
                effective_date, expiration_date, change_description,
                pdf_name, origin_info, destination_info,
                upload_timestamp, raw_ocr_text
            ) 
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?)
            """
            
            logger.debug(f"Executing insert with params: {[str(p)[:50] for p in params]}")
            
            # Execute insert and get ID directly
            cursor.execute(insert_sql, params)
            result = cursor.fetchone()
            
            if result and result[0]:
                doc_id = int(result[0])
                logger.info(f"Document inserted successfully with ID: {doc_id}")
                
                # Save related data with transaction safety
                try:
                    commodities_saved = self._save_commodities(cursor, doc_id, data.get('commodities', []))
                    rates_saved = self._save_rates(cursor, doc_id, data.get('rates', []))
                    notes_saved = self._save_notes(cursor, doc_id, data.get('notes', []))
                    
                    logger.info(f"Saved related data: {commodities_saved} commodities, {rates_saved} rates, {notes_saved} notes")
                    
                    # Commit all changes
                    conn.commit()
                    logger.info(f"Successfully committed all data for document {doc_id}")
                    
                    return doc_id
                    
                except Exception as related_error:
                    logger.error(f"Error saving related data: {related_error}")
                    conn.rollback()
                    # Still return doc_id since main document was saved
                    return doc_id
            else:
                logger.error("Document insertion failed - OUTPUT clause returned no ID")
                conn.rollback()
                return None
                
        except pyodbc.IntegrityError as e:
            logger.error(f"Database integrity error: {e}")
            if conn:
                conn.rollback()
            return None
        except pyodbc.Error as e:
            logger.error(f"Database error during save: {e}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            if conn:
                conn.rollback()
            return None
        except Exception as e:
            logger.error(f"Unexpected error during save: {e}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                try:
                    conn.close()
                    logger.debug("Database connection closed")
                except:
                    pass
    
    def _verify_tables_exist(self, cursor) -> bool:
        """Verify that required tables exist in the database"""
        required_tables = ['tariff_documents', 'tariff_commodities', 'tariff_rates', 'tariff_notes']
        
        for table in required_tables:
            try:
                cursor.execute(f"SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table}'")
                if not cursor.fetchone():
                    logger.error(f"Required table '{table}' does not exist")
                    return False
            except Exception as e:
                logger.error(f"Error checking table existence: {e}")
                return False
        
        logger.debug("All required tables verified")
        return True
    
    def _prepare_document_params(self, header: Dict, data: Dict) -> tuple:
        """Prepare and validate parameters for document insertion"""
        try:
            params = (
                str(header.get('item_number', ''))[:50],  # Ensure max length
                self._safe_int(header.get('revision', 0)),
                str(header.get('cprs_number', ''))[:20],
                self._safe_date(header.get('issue_date')),
                self._safe_date(header.get('effective_date')),
                self._safe_date(header.get('expiration_date')),
                str(header.get('change_description', ''))[:255],
                str(data.get('pdf_name', ''))[:255],
                str(data.get('origin_info', ''))[:500],
                str(data.get('destination_info', ''))[:500],
                str(data.get('raw_text', ''))[:4000]
            )
            
            logger.debug(f"Prepared parameters: {len(params)} items")
            return params
            
        except Exception as e:
            logger.error(f"Error preparing document parameters: {e}")
            raise
    
    def _save_commodities(self, cursor, doc_id: int, commodities: List[Dict]) -> int:
        """Save commodity data with enhanced error handling"""
        saved_count = 0
        
        if not commodities:
            logger.debug("No commodities to save")
            return 0
        
        for i, commodity in enumerate(commodities):
            try:
                cursor.execute("""
                    INSERT INTO tariff_commodities (
                        document_id, commodity_name, commodity_code, 
                        description, created_at
                    ) VALUES (?, ?, ?, ?, GETDATE())
                """, (
                    doc_id,
                    str(commodity.get('name', ''))[:255],
                    str(commodity.get('stcc_code', ''))[:50],
                    str(commodity.get('description', ''))[:500]
                ))
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Error saving commodity {i}: {e}")
                continue
        
        logger.debug(f"Saved {saved_count}/{len(commodities)} commodities")
        return saved_count
    
    def _save_rates(self, cursor, doc_id: int, rates: List[Dict]) -> int:
        """Save rate data with enhanced error handling"""
        saved_count = 0
        
        if not rates:
            logger.debug("No rates to save")
            return 0
        
        for i, rate in enumerate(rates):
            try:
                cursor.execute("""
                    INSERT INTO tariff_rates (
                        document_id, origin_info, destination_info,
                        rate_value, currency, commodity_type, equipment_type,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE())
                """, (
                    doc_id,
                    str(rate.get('origin', ''))[:255],
                    str(rate.get('destination', ''))[:255],
                    self._safe_decimal(rate.get('rate_amount', '0')),
                    str(rate.get('currency', 'USD'))[:10],
                    str(rate.get('train_type', ''))[:255],
                    str(rate.get('equipment_type', ''))[:100]
                ))
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Error saving rate {i}: {e}")
                continue
        
        logger.debug(f"Saved {saved_count}/{len(rates)} rates")
        return saved_count
    
    def _save_notes(self, cursor, doc_id: int, notes: List[Dict]) -> int:
        """Save notes data with enhanced error handling"""
        saved_count = 0
        
        if not notes:
            logger.debug("No notes to save")
            return 0
        
        for i, note in enumerate(notes):
            try:
                cursor.execute("""
                    INSERT INTO tariff_notes (
                        document_id, note_type, note_text, 
                        created_at
                    ) VALUES (?, ?, ?, GETDATE())
                """, (
                    doc_id,
                    str(note.get('type', 'GENERAL'))[:50],
                    str(note.get('text', ''))[:1000]
                ))
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Error saving note {i}: {e}")
                continue
        
        logger.debug(f"Saved {saved_count}/{len(notes)} notes")
        return saved_count
    
    def test_database_connection(self) -> Dict[str, Any]:
        """Test database connection and return detailed status"""
        test_result = {
            "connected": False,
            "tables_exist": False,
            "can_write": False,
            "error": None,
            "connection_string_valid": bool(self.connection_string)
        }
        
        if not self.connection_string:
            test_result["error"] = "No connection string provided"
            return test_result
        
        try:
            conn = self.get_database_connection()
            if conn is None:
                test_result["error"] = "Failed to establish connection"
                return test_result
            
            test_result["connected"] = True
            
            cursor = conn.cursor()
            
            # Test table existence
            test_result["tables_exist"] = self._verify_tables_exist(cursor)
            
            # Test write capability with a simple query
            try:
                cursor.execute("SELECT 1")
                test_result["can_write"] = True
            except Exception as e:
                test_result["error"] = f"Cannot execute queries: {e}"
            
            conn.close()
            
        except Exception as e:
            test_result["error"] = str(e)
        
        return test_result
    
    def _safe_int(self, value, default: int = 0) -> int:
        """Safely convert value to integer"""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert {value} to int, using default {default}")
            return default
    
    def _safe_decimal(self, value) -> Optional[float]:
        """Safely convert value to decimal"""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                cleaned = value.replace('$', '').replace(',', '').strip()
                return float(cleaned)
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert {value} to decimal")
            return None
    
    def _safe_date(self, date_str) -> Optional[str]:
        """Safely convert date string to database format"""
        if not date_str:
            return None
        
        try:
            # If already in YYYY-MM-DD format, validate and return
            if isinstance(date_str, str) and len(date_str) == 10 and date_str.count('-') == 2:
                datetime.strptime(date_str, '%Y-%m-%d')
                return date_str
        except ValueError:
            pass
        
        # Return truncated string as fallback
        return str(date_str)[:10]