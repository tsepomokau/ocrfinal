import pyodbc
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class CPTariffDatabase:
    """Fixed database handler with correct column names"""
    
    def __init__(self, connection_string: str):
        """Initialize database connection"""
        self.connection_string = connection_string
        logger.info(f"🔗 Database configured: {connection_string}")
    
    def get_database_connection(self):
        """Get database connection"""
        try:
            conn = pyodbc.connect(self.connection_string)
            return conn
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return None
    
    def save_document(self, data: Dict[str, Any]) -> Optional[int]:
        """Save document data to database - FIXED COLUMN NAMES"""
        print("\n" + "="*50)
        print("💾 STARTING DATABASE SAVE WITH COLUMN FIX")
        print("="*50)
        
        conn = self.get_database_connection()
        if conn is None:
            print("❌ No database connection")
            return None
        
        try:
            cursor = conn.cursor()
            
            # Log input data structure
            header = data.get('header', {})
            
            print(f"📝 Document data:")
            print(f"   Item: {header.get('item_number', '')}")
            print(f"   Revision: {header.get('revision', 0)}")
            print(f"   CPRS: {header.get('cprs_number', '')}")
            print(f"   PDF: {data.get('pdf_name', '')}")
            
            # FIXED: Use correct column names that match your database schema
            insert_sql = """
            INSERT INTO tariff_documents (
                item_number, revision, cprs_number, issue_date, 
                effective_date, expiration_date, change_description,
                pdf_name, origin_info, destination_info,
                upload_timestamp, raw_ocr_text
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?)
            """
            
            # Prepare parameters with proper handling
            params = (
                str(header.get('item_number', '')),
                self._safe_int(header.get('revision', 0)),
                str(header.get('cprs_number', '')),
                self._parse_date(header.get('issue_date')),
                self._parse_date(header.get('effective_date')),
                self._parse_date(header.get('expiration_date')),
                str(header.get('change_description', '')),
                str(data.get('pdf_name', 'unknown.pdf')),
                str(data.get('origin_info', ''))[:500],  # Limit length
                str(data.get('destination_info', ''))[:500],  # Limit length
                str(data.get('raw_text', ''))[:4000]  # Limit length for raw_ocr_text
            )
            
            print(f"🔧 Using FIXED column names:")
            print(f"   origin_info (not origin_location)")
            print(f"   destination_info (not destination_location)")
            print(f"   raw_ocr_text (not raw_text)")
            
            # Execute insert
            cursor.execute(insert_sql, params)
            
            # Get the inserted ID
            cursor.execute("SELECT @@IDENTITY")
            result = cursor.fetchone()
            
            if result and result[0]:
                doc_id = int(result[0])
                print(f"✅ Document inserted with ID: {doc_id}")
                
                # Save related data
                print(f"🔄 Saving commodities...")
                commodities_saved = self._save_commodities(cursor, doc_id, data.get('commodities', []))
                print(f"✅ Saved {commodities_saved} commodities")
                
                print(f"🔄 Saving rates...")
                rates_saved = self._save_rates(cursor, doc_id, data.get('rates', []))
                print(f"✅ Saved {rates_saved} rates")
                
                print(f"🔄 Saving notes...")
                notes_saved = self._save_notes(cursor, doc_id, data.get('notes', []))
                print(f"✅ Saved {notes_saved} notes")
                
                # Commit all changes
                conn.commit()
                print(f"\n🎉 ALL DATA SAVED SUCCESSFULLY!")
                print(f"📊 Document ID: {doc_id}")
                print("="*50)
                
                return doc_id
            else:
                print(f"❌ Document insertion failed - no ID returned")
                return None
                
        except Exception as e:
            print(f"❌ Database save error: {e}")
            logger.error(f"Database save error: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()
    
    def _save_commodities(self, cursor, doc_id: int, commodities: List[Dict]) -> int:
        """Save commodity data - FIXED COLUMN NAMES"""
        saved_count = 0
        
        for commodity in commodities:
            try:
                # FIXED: Use correct column names for your schema
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
                logger.error(f"❌ Error saving commodity: {e}")
                continue
        
        return saved_count
    
    def _save_rates(self, cursor, doc_id: int, rates: List[Dict]) -> int:
        """Save rate data - FIXED COLUMN NAMES"""
        saved_count = 0
        
        for rate in rates:
            try:
                # FIXED: Use correct column names for your schema
                cursor.execute("""
                    INSERT INTO tariff_rates (
                        document_id, origin_location, destination_location,
                        rate_value, currency, commodity_type, equipment_type,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE())
                """, (
                    doc_id,
                    str(rate.get('origin', ''))[:255],
                    str(rate.get('destination', ''))[:255],
                    self._safe_decimal(rate.get('rate_amount', '0')),
                    str(rate.get('currency', 'USD'))[:10],
                    str(rate.get('commodity', ''))[:255],
                    str(rate.get('equipment_type', ''))[:100]
                ))
                saved_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error saving rate: {e}")
                continue
        
        return saved_count
    
    def _save_notes(self, cursor, doc_id: int, notes: List[Dict]) -> int:
        """Save notes data - FIXED COLUMN NAMES"""
        saved_count = 0
        
        for note in notes:
            try:
                # FIXED: Use correct column names for your schema
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
                logger.error(f"❌ Error saving note: {e}")
                continue
        
        return saved_count
    
    def _safe_int(self, value, default: int = 0) -> int:
        """Safely convert value to integer"""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
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
            return None
    
    def _parse_date(self, date_str) -> Optional[str]:
        """Parse date string to database format"""
        if not date_str:
            return None
        
        # If already in YYYY-MM-DD format, return as is
        if isinstance(date_str, str) and len(date_str) == 10 and date_str.count('-') == 2:
            return date_str
        
        return str(date_str)  # Return as string for now
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = self.get_database_connection()
        if conn is None:
            return {
                "total_documents": 0,
                "total_rates": 0,
                "database_status": "disconnected"
            }
        
        try:
            cursor = conn.cursor()
            
            # Get basic counts
            cursor.execute("SELECT COUNT(*) FROM tariff_documents")
            doc_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tariff_rates")
            rate_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tariff_commodities")
            commodity_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tariff_notes")
            note_count = cursor.fetchone()[0]
            
            return {
                "total_documents": doc_count,
                "total_rates": rate_count,
                "total_commodities": commodity_count,
                "total_notes": note_count,
                "database_status": "connected"
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting statistics: {e}")
            return {
                "total_documents": 0,
                "total_rates": 0,
                "database_status": "error",
                "error": str(e)
            }
        finally:
            if conn:
                conn.close()