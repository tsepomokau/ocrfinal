"""
Fixed Database Handler with Enhanced Error Handling
File: backend/app/database/cp_tariff_database_fixed.py
"""
import pyodbc
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import traceback

logger = logging.getLogger(__name__)

class CPTariffDatabaseFixed:
    """Enhanced database handler with improved error handling and validation"""
    
    def __init__(self, connection_string: str = None):
        """Initialize database connection"""
        if connection_string:
            self.connection_string = connection_string
        else:
            # Default connection for SQL Server Express
            self.connection_string = (
                "DRIVER={ODBC Driver 17 for SQL Server};"
                "SERVER=DESKTOP-KL51D0H\\SQLEXPRESS;"
                "DATABASE=cp_tariff;"
                "Trusted_Connection=yes;"
            )
        
        logger.info(f"🔗 Database configured: {self.connection_string}")
        self.last_error = None
    
    def get_database_connection(self):
        """Get database connection with retry logic"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"🔄 Attempting database connection (attempt {retry_count + 1}/{max_retries})")
                conn = pyodbc.connect(self.connection_string, timeout=30)
                print("✅ Database connection successful")
                return conn
            except Exception as e:
                retry_count += 1
                self.last_error = str(e)
                print(f"❌ Database connection attempt {retry_count} failed: {e}")
                if retry_count >= max_retries:
                    logger.error(f"❌ All database connection attempts failed: {e}")
                    return None
        
        return None
    
    def test_database_connection(self) -> bool:
        """Test database connection"""
        print("🧪 Testing database connection...")
        
        conn = self.get_database_connection()
        if conn is None:
            print("❌ Database connection test failed")
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 as test_value")
            result = cursor.fetchone()
            
            if result and result[0] == 1:
                print("✅ Database connection test passed")
                
                # Test if our tables exist
                cursor.execute("""
                    SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME IN ('tariff_documents', 'tariff_rates', 'tariff_commodities', 'tariff_notes')
                """)
                table_count = cursor.fetchone()[0]
                print(f"📊 Found {table_count}/4 required tables")
                
                if table_count < 4:
                    print("⚠️  Some tables are missing. You may need to run the schema setup.")
                
                return True
            else:
                print("❌ Database test query failed")
                return False
                
        except Exception as e:
            print(f"❌ Database test error: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def save_document(self, data: Dict[str, Any]) -> Optional[int]:
        """Save document data to database with enhanced error handling"""
        print("\n" + "="*60)
        print("💾 STARTING ENHANCED DATABASE SAVE PROCESS")
        print("="*60)
        
        # Validate input data first
        if not self._validate_input_data(data):
            print("❌ Input data validation failed")
            return None
        
        conn = self.get_database_connection()
        if conn is None:
            print("❌ No database connection available")
            return None
        
        document_id = None
        
        try:
            cursor = conn.cursor()
            
            print("🔄 STEP 1: Saving main document...")
            document_id = self._save_main_document(cursor, data)
            
            if document_id is None:
                print("❌ Failed to save main document")
                conn.rollback()
                return None
            
            print(f"✅ Document saved with ID: {document_id}")
            
            print("🔄 STEP 2: Saving commodities...")
            commodities_saved = self._save_commodities_enhanced(cursor, document_id, data.get('commodities', []))
            print(f"✅ Saved {commodities_saved} commodities")
            
            print("🔄 STEP 3: Saving rates...")
            rates_saved = self._save_rates_enhanced(cursor, document_id, data.get('rates', []))
            print(f"✅ Saved {rates_saved} rates")
            
            print("🔄 STEP 4: Saving notes...")
            notes_saved = self._save_notes_enhanced(cursor, document_id, data.get('notes', []))
            print(f"✅ Saved {notes_saved} notes")
            
            # Commit all changes
            conn.commit()
            print(f"\n🎉 ALL DATA SAVED SUCCESSFULLY!")
            print(f"📊 Summary:")
            print(f"   Document ID: {document_id}")
            print(f"   Commodities: {commodities_saved}")
            print(f"   Rates: {rates_saved}")
            print(f"   Notes: {notes_saved}")
            print("="*60)
            
            return document_id
            
        except Exception as e:
            print(f"❌ Database save error: {e}")
            print(f"📋 Full error details:")
            traceback.print_exc()
            
            if conn:
                try:
                    conn.rollback()
                    print("🔄 Database transaction rolled back")
                except:
                    pass
            
            self.last_error = str(e)
            return None
            
        finally:
            if conn:
                try:
                    conn.close()
                    print("🔌 Database connection closed")
                except:
                    pass
    
    def _validate_input_data(self, data: Dict[str, Any]) -> bool:
        """Validate input data structure"""
        print("🔍 Validating input data...")
        
        required_keys = ['header', 'commodities', 'rates', 'notes']
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            print(f"❌ Missing required keys: {missing_keys}")
            return False
        
        # Validate header has minimum required data
        header = data.get('header', {})
        if not header.get('item_number'):
            print("❌ Missing item_number in header")
            return False
        
        print("✅ Input data validation passed")
        return True
    
    def _save_main_document(self, cursor, data: Dict[str, Any]) -> Optional[int]:
        """Save main document with enhanced error handling"""
        
        try:
            header = data.get('header', {})
            
            # Prepare data with proper type conversion and defaults
            item_number = str(header.get('item_number', ''))
            revision = self._safe_int(header.get('revision'), 0)
            cprs_number = self._safe_string(header.get('cprs_number'), 50)
            
            # Handle dates safely
            issue_date = self._safe_date(header.get('issue_date'))
            effective_date = self._safe_date(header.get('effective_date'))
            expiration_date = self._safe_date(header.get('expiration_date'))
            
            change_description = self._safe_string(header.get('change_description'), 500)
            pdf_name = self._safe_string(data.get('pdf_name'), 255)
            origin_info = self._safe_string(data.get('origin_info'), 500)
            destination_info = self._safe_string(data.get('destination_info'), 500)
            raw_ocr_text = self._safe_string(data.get('raw_ocr_text'), 4000)  # Limit to prevent overflow
            
            print(f"📝 Document details:")
            print(f"   Item Number: {item_number}")
            print(f"   Revision: {revision}")
            print(f"   CPRS: {cprs_number}")
            print(f"   Issue Date: {issue_date}")
            print(f"   Effective Date: {effective_date}")
            print(f"   PDF Name: {pdf_name}")
            
            # Use a more reliable insert statement
            insert_sql = """
                INSERT INTO tariff_documents (
                    item_number, revision, cprs_number, issue_date, 
                    effective_date, expiration_date, change_description,
                    pdf_name, origin_info, destination_info,
                    upload_timestamp, raw_ocr_text
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?)
            """
            
            # Execute insert
            cursor.execute(insert_sql, (
                item_number, revision, cprs_number, issue_date,
                effective_date, expiration_date, change_description,
                pdf_name, origin_info, destination_info, raw_ocr_text
            ))
            
            # Get the inserted ID using a separate query
            cursor.execute("SELECT @@IDENTITY")
            result = cursor.fetchone()
            
            if result and result[0]:
                document_id = int(result[0])
                print(f"✅ Document inserted successfully with ID: {document_id}")
                return document_id
            else:
                print("❌ Document insert succeeded but no ID returned")
                return None
                
        except Exception as e:
            print(f"❌ Error saving main document: {e}")
            print(f"📋 SQL Error details: {str(e)}")
            raise
    
    def _save_commodities_enhanced(self, cursor, doc_id: int, commodities: List[Dict]) -> int:
        """Save commodities with enhanced error handling"""
        saved_count = 0
        
        if not commodities:
            print("ℹ️  No commodities to save")
            return 0
        
        for i, commodity in enumerate(commodities):
            try:
                name = self._safe_string(commodity.get('name'), 255)
                stcc_code = self._safe_string(commodity.get('stcc_code'), 20)
                description = self._safe_string(commodity.get('description'), 500)
                
                if not name:  # Skip if no name
                    continue
                
                print(f"   Saving commodity {i+1}: {name} ({stcc_code})")
                
                cursor.execute("""
                    INSERT INTO tariff_commodities (
                        document_id, commodity_name, commodity_code, 
                        classification, created_at
                    ) VALUES (?, ?, ?, ?, GETDATE())
                """, (doc_id, name, stcc_code, description))
                
                saved_count += 1
                
            except Exception as e:
                print(f"❌ Error saving commodity {i+1}: {e}")
                continue  # Continue with other commodities
        
        return saved_count
    
    def _save_rates_enhanced(self, cursor, doc_id: int, rates: List[Dict]) -> int:
        """Save rates with enhanced error handling"""
        saved_count = 0
        
        if not rates:
            print("ℹ️  No rates to save")
            return 0
        
        for i, rate in enumerate(rates):
            try:
                origin = self._safe_string(rate.get('origin'), 255)
                destination = self._safe_string(rate.get('destination'), 255)
                rate_amount = self._safe_decimal(rate.get('rate_amount'))
                currency = self._safe_string(rate.get('currency', 'USD'), 10)
                train_type = self._safe_string(rate.get('train_type'), 50)
                equipment_type = self._safe_string(rate.get('equipment_type'), 100)
                route_code = self._safe_string(rate.get('route_code'), 20)
                additional_provisions = self._safe_string(rate.get('additional_provisions'), 500)
                
                # Skip if essential data is missing
                if not (origin and destination and rate_amount):
                    print(f"⚠️  Skipping rate {i+1}: missing essential data")
                    continue
                
                print(f"   Saving rate {i+1}: {origin} → {destination} = ${rate_amount}")
                
                cursor.execute("""
                    INSERT INTO tariff_rates (
                        document_id, origin_info, destination_info,
                        rate_value, currency, commodity_type, equipment_type,
                        route_code, additional_provisions, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                """, (
                    doc_id, origin, destination, rate_amount, currency,
                    train_type, equipment_type, route_code, additional_provisions
                ))
                
                saved_count += 1
                
            except Exception as e:
                print(f"❌ Error saving rate {i+1}: {e}")
                continue  # Continue with other rates
        
        return saved_count
    
    def _save_notes_enhanced(self, cursor, doc_id: int, notes: List[Dict]) -> int:
        """Save notes with enhanced error handling"""
        saved_count = 0
        
        if not notes:
            print("ℹ️  No notes to save")
            return 0
        
        for i, note in enumerate(notes):
            try:
                note_type = self._safe_string(note.get('type', 'GENERAL'), 50)
                note_code = self._safe_string(note.get('code'), 10)
                note_text = self._safe_string(note.get('text'), 1000)
                applies_to = self._safe_string(note.get('applies_to', 'ALL'), 255)
                
                if not note_text:  # Skip if no text
                    continue
                
                print(f"   Saving note {i+1}: [{note_type}] {note_text[:50]}...")
                
                cursor.execute("""
                    INSERT INTO tariff_notes (
                        document_id, note_type, description, applies_to,
                        created_at
                    ) VALUES (?, ?, ?, ?, GETDATE())
                """, (doc_id, note_type, note_text, applies_to))
                
                saved_count += 1
                
            except Exception as e:
                print(f"❌ Error saving note {i+1}: {e}")
                continue  # Continue with other notes
        
        return saved_count
    
    def _safe_string(self, value, max_length: int = None) -> str:
        """Safely convert value to string with length limit"""
        if value is None:
            return ''
        
        result = str(value).strip()
        
        if max_length and len(result) > max_length:
            result = result[:max_length]
        
        return result
    
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
            # Handle string format like "$123.45"
            if isinstance(value, str):
                cleaned = value.replace('$', '').replace(',', '').strip()
                return float(cleaned)
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_date(self, value) -> Optional[str]:
        """Safely convert value to date string"""
        if not value:
            return None
        
        # If already in proper format, return as is
        if isinstance(value, str) and len(value) == 10 and value.count('-') == 2:
            return value
        
        try:
            # Parse various date formats and convert to YYYY-MM-DD
            if isinstance(value, str):
                # Handle "JUL 22, 2024" format
                import re
                from datetime import datetime
                
                # Try parsing common formats
                formats = [
                    '%Y-%m-%d',  # 2024-07-22
                    '%m/%d/%Y',  # 07/22/2024
                    '%d/%m/%Y',  # 22/07/2024
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return dt.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
                
                # Try parsing "JUL 22, 2024" format
                month_map = {
                    'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
                    'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
                    'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
                }
                
                match = re.search(r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})', value.upper())
                if match:
                    month = month_map.get(match.group(1), '01')
                    day = match.group(2).zfill(2)
                    year = match.group(3)
                    return f"{year}-{month}-{day}"
            
            return None
            
        except Exception:
            return None
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Get database statistics with enhanced error handling"""
        print("📊 Getting database statistics...")
        
        conn = self.get_database_connection()
        if conn is None:
            return {
                "total_documents": 0,
                "total_rates": 0,
                "database_status": "disconnected",
                "error": self.last_error
            }
        
        try:
            cursor = conn.cursor()
            
            # Get counts
            cursor.execute("SELECT COUNT(*) FROM tariff_documents")
            doc_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tariff_rates")
            rate_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tariff_commodities")
            commodity_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tariff_notes")
            note_count = cursor.fetchone()[0]
            
            # Get latest document
            latest_doc = None
            try:
                cursor.execute("""
                    SELECT TOP 1 item_number, upload_timestamp, pdf_name 
                    FROM tariff_documents 
                    ORDER BY id DESC
                """)
                latest = cursor.fetchone()
                if latest:
                    latest_doc = {
                        "item_number": latest[0],
                        "upload_timestamp": latest[1].isoformat() if latest[1] else None,
                        "pdf_name": latest[2]
                    }
            except Exception as e:
                print(f"⚠️  Could not get latest document: {e}")
            
            stats = {
                "total_documents": doc_count,
                "total_rates": rate_count,
                "total_commodities": commodity_count,
                "total_notes": note_count,
                "database_status": "connected",
                "latest_document": latest_doc
            }
            
            print(f"✅ Database statistics retrieved:")
            print(f"   Documents: {doc_count}")
            print(f"   Rates: {rate_count}")
            print(f"   Commodities: {commodity_count}")
            print(f"   Notes: {note_count}")
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting statistics: {e}")
            return {
                "total_documents": 0,
                "total_rates": 0,
                "total_commodities": 0,
                "total_notes": 0,
                "database_status": "error",
                "error": str(e)
            }
        finally:
            if conn:
                conn.close()
    
    def get_last_error(self) -> str:
        """Get the last error message"""
        return self.last_error or "No error recorded"

# For compatibility with existing code
CPTariffDatabase = CPTariffDatabaseFixed