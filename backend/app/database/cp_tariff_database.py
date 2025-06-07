"""
CP Tariff Database Manager - SQL Server Compatible
File: backend/app/database/cp_tariff_database.py
"""
import pyodbc
import json
import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

class CPTariffDatabase:
    """Production database manager with SQL Server compatibility and comprehensive error handling"""
    
    def __init__(self):
        """Initialize database connection with environment variables"""
        self.server = os.getenv('DB_SERVER', 'DESKTOP-KL51D0H\\SQLEXPRESS')
        self.database = os.getenv('DB_NAME', 'cp_tariff')
        self.driver = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
        
        self.connection_string = (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            "Trusted_Connection=yes;"
        )
        
        print(f"🔗 Database configured: {self.server}/{self.database}")
    
    def get_database_connection(self):
        """Get database connection with error handling"""
        try:
            return pyodbc.connect(self.connection_string)
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None
    
    def test_database_connection(self) -> bool:
        """Test database connection and verify tables exist"""
        try:
            conn = self.get_database_connection()
            if conn is None:
                return False
            
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            # Check if required tables exist
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME IN ('tariff_documents', 'tariff_rates', 'tariff_commodities', 'tariff_notes')
            """)
            table_count = cursor.fetchone()[0]
            
            conn.close()
            
            if table_count == 4:
                print("✅ Database connection successful - all tables found")
                return True
            else:
                print(f"⚠️  Database connected but only {table_count}/4 tables found")
                return False
            
        except Exception as e:
            print(f"❌ Database connection test failed: {e}")
            return False
    
    def parse_tariff_date(self, date_str: str) -> Optional[str]:
        """Parse and standardize date strings for SQL Server - FIXED Implementation"""
        if not date_str:
            return None
        
        # Clean the input string
        date_str = str(date_str).strip()
        
        # Common CP Tariff date formats
        date_patterns = [
            # Month name formats
            (r'([A-Z]{3})\s+(\d{1,2}),?\s+(\d{4})', 'month_name'),  # JAN 01, 2024
            (r'([A-Z]{3})\s+(\d{1,2})\s+(\d{4})', 'month_name'),    # JAN 01 2024
            (r'([A-Z]{3})-(\d{1,2})-(\d{4})', 'month_name'),        # JAN-01-2024
            
            # Numeric formats
            (r'(\d{1,2})/(\d{1,2})/(\d{4})', 'mdy'),                # 01/01/2024  
            (r'(\d{4})-(\d{2})-(\d{2})', 'ymd'),                    # 2024-01-01
            (r'(\d{2})-(\d{2})-(\d{4})', 'mdy_dash'),               # 01-01-2024
        ]
        
        for pattern, format_type in date_patterns:
            match = re.search(pattern, date_str.upper())
            if match:
                try:
                    if format_type == 'month_name':
                        month_names = {
                            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
                            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
                        }
                        month = month_names.get(match.group(1), 1)
                        day = int(match.group(2))
                        year = int(match.group(3))
                        parsed_date = datetime(year, month, day)
                        
                    elif format_type == 'mdy' or format_type == 'mdy_dash':
                        month = int(match.group(1))
                        day = int(match.group(2)) 
                        year = int(match.group(3))
                        parsed_date = datetime(year, month, day)
                        
                    elif format_type == 'ymd':
                        year = int(match.group(1))
                        month = int(match.group(2))
                        day = int(match.group(3))
                        parsed_date = datetime(year, month, day)
                    
                    # Return in SQL Server compatible format (ISO 8601)
                    return parsed_date.strftime('%Y-%m-%d')
                    
                except (ValueError, KeyError) as e:
                    print(f"⚠️  Date parsing error for '{date_str}': {e}")
                    continue
        
        # If no pattern matches, return None
        print(f"⚠️  Could not parse date: '{date_str}'")
        return None
    
    def save_tariff_document_complete(self, extracted_data: Dict[str, Any], pdf_path: str = "") -> Optional[int]:
        """Save complete tariff document data to database with comprehensive error handling"""
        print("\n" + "="*50)
        print("💾 STARTING DATABASE SAVE PROCESS")
        print("="*50)
        
        print(f"📊 Input data structure:")
        print(f"   - Keys: {list(extracted_data.keys())}")
        print(f"   - Commodities: {len(extracted_data.get('commodities', []))}")
        print(f"   - Rates: {len(extracted_data.get('rates', []))}")
        print(f"   - Notes: {len(extracted_data.get('notes', []))}")
        print(f"   - Header: {extracted_data.get('header', {})}")
        
        conn = self.get_database_connection()
        if conn is None:
            print("❌ Cannot connect to database - aborting save")
            return None
        
        try:
            cursor = conn.cursor()
            
            # Step 1: Insert main document
            print("\n🔄 STEP 1: Inserting main document...")
            document_id = self._insert_main_document(cursor, extracted_data, pdf_path)
            
            if not document_id:
                print("❌ Document insertion failed - cannot proceed")
                conn.rollback()
                return None
            
            print(f"✅ Document inserted successfully with ID: {document_id}")
            
            # Step 2: Insert commodities
            commodities = extracted_data.get('commodities', [])
            if commodities:
                print(f"\n🔄 STEP 2: Inserting {len(commodities)} commodities...")
                success = self._insert_document_commodities(cursor, document_id, commodities)
                if success:
                    print("✅ Commodities inserted successfully")
                else:
                    print("❌ Commodity insertion failed")
            else:
                print("\n⚠️  STEP 2: No commodities to insert")
            
            # Step 3: Insert rates
            rates = extracted_data.get('rates', [])
            if rates:
                print(f"\n🔄 STEP 3: Inserting {len(rates)} rates...")
                success = self._insert_document_rates(cursor, document_id, rates)
                if success:
                    print("✅ Rates inserted successfully")
                else:
                    print("❌ Rate insertion failed")
            else:
                print("\n⚠️  STEP 3: No rates to insert")
            
            # Step 4: Insert notes
            notes = extracted_data.get('notes', [])
            if notes:
                print(f"\n🔄 STEP 4: Inserting {len(notes)} notes...")
                success = self._insert_document_notes(cursor, document_id, notes)
                if success:
                    print("✅ Notes inserted successfully")
                else:
                    print("❌ Note insertion failed")
            else:
                print("\n⚠️  STEP 4: No notes to insert")
            
            # Commit the transaction
            print("\n🔄 STEP 5: Committing transaction...")
            conn.commit()
            print("✅ Transaction committed successfully")
            
            # Verify the save
            print("\n🔍 VERIFICATION:")
            self._verify_document_save(cursor, document_id)
            
            print(f"\n🎉 SUCCESS: Document saved with ID {document_id}")
            print("="*50)
            
            return document_id
            
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR during save: {e}")
            import traceback
            traceback.print_exc()
            conn.rollback()
            print("🔄 Transaction rolled back")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def _insert_main_document(self, cursor, data: Dict[str, Any], pdf_path: str) -> Optional[int]:
        """Insert main document record - FIXED for SQL Server compatibility"""
        try:
            header = data.get('header', {})
            
            print(f"📝 Document data:")
            print(f"   - Header: {header}")
            print(f"   - PDF name: {data.get('pdf_name', 'UNKNOWN')}")
            print(f"   - Origin: {data.get('origin_info', '')}")
            print(f"   - Destination: {data.get('destination_info', '')}")
            
            insert_query = """
            INSERT INTO tariff_documents (
                item_number, revision, cprs_number, issue_date, effective_date, 
                expiration_date, pdf_name, pdf_path, origin_info, destination_info, 
                currency, change_description, raw_ocr_text, processed_json
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """
            
            # Process revision number
            revision = header.get('revision')
            if revision is not None:
                try:
                    revision = int(revision)
                except (ValueError, TypeError):
                    revision = None
            
            params = (
                header.get('item_number', ''),
                revision,
                header.get('cprs_number', ''),
                self.parse_tariff_date(header.get('issue_date')),
                self.parse_tariff_date(header.get('effective_date')),
                self.parse_tariff_date(header.get('expiration_date')),
                data.get('pdf_name', 'unknown.pdf'),
                pdf_path,
                data.get('origin_info', ''),
                data.get('destination_info', ''),
                data.get('currency', 'USD'),
                header.get('change_description', ''),
                data.get('raw_text', ''),
                json.dumps(data)
            )
            
            print(f"🔧 SQL Parameters: {params[:6]}...")  # Show first 6 params
            
            cursor.execute(insert_query, params)
            
            # FIXED: Get the inserted ID - SQL Server compatible version
            cursor.execute("SELECT SCOPE_IDENTITY()")  # Changed from @@IDENTITY
            result = cursor.fetchone()
            document_id = int(result[0]) if result and result[0] else None
            
            print(f"📋 Document ID returned: {document_id}")
            return document_id
            
        except Exception as e:
            print(f"❌ Document insertion error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _insert_document_commodities(self, cursor, document_id: int, commodities: List[Dict]) -> bool:
        """Insert commodities with improved error handling"""
        try:
            for i, commodity in enumerate(commodities):
                print(f"   📦 Commodity {i+1}: {commodity}")
                
                insert_query = """
                INSERT INTO tariff_commodities (
                    tariff_document_id, commodity_name, stcc_code, description
                ) VALUES (?, ?, ?, ?)
                """
                
                # Handle different key names for commodity name
                commodity_name = (
                    commodity.get('name') or 
                    commodity.get('commodity_name') or 
                    commodity.get('commodity') or
                    ''
                )
                
                params = (
                    document_id,
                    commodity_name,
                    commodity.get('stcc_code', ''),
                    commodity.get('description', '')
                )
                
                cursor.execute(insert_query, params)
                print(f"   ✅ Commodity {i+1} inserted")
            
            return True
                
        except Exception as e:
            print(f"❌ Commodity insertion error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _insert_document_rates(self, cursor, document_id: int, rates: List[Dict]) -> bool:
        """Insert rates with enhanced data cleaning - FIXED for SQL Server"""
        try:
            for i, rate in enumerate(rates):
                print(f"   💰 Rate {i+1}: {rate}")
                
                insert_query = """
                INSERT INTO tariff_rates (
                    tariff_document_id, origin, destination, origin_state, 
                    destination_state, rate_category, rate_amount, currency,
                    train_type, car_capacity_type, route_code, additional_provisions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                # Handle rate_amount conversion with better error handling
                rate_amount = rate.get('rate_amount')
                if rate_amount is not None:
                    try:
                        # Clean and convert rate amount
                        if isinstance(rate_amount, str):
                            # Remove currency symbols, commas, and whitespace
                            cleaned_amount = re.sub(r'[$,\s]', '', rate_amount)
                            rate_amount = float(cleaned_amount) if cleaned_amount else None
                        else:
                            rate_amount = float(rate_amount)
                    except (ValueError, TypeError):
                        print(f"   ⚠️  Could not convert rate amount: {rate.get('rate_amount')}")
                        rate_amount = None
                
                params = (
                    document_id,
                    rate.get('origin', '')[:255],  # Limit length for database
                    rate.get('destination', '')[:255],
                    rate.get('origin_state', '')[:50],
                    rate.get('destination_state', '')[:50],
                    rate.get('rate_category', '')[:10],
                    rate_amount,
                    rate.get('currency', 'USD')[:10],
                    rate.get('train_type', '')[:100],
                    rate.get('car_capacity_type', '')[:50],
                    rate.get('route_code', '')[:50],
                    rate.get('additional_provisions', '')[:500]
                )
                
                print(f"   🔧 Rate parameters: {params[:6]}...")  # Show first 6 params
                cursor.execute(insert_query, params)
                print(f"   ✅ Rate {i+1} inserted")
            
            return True
                
        except Exception as e:
            print(f"❌ Rate insertion error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _insert_document_notes(self, cursor, document_id: int, notes: List[Dict]) -> bool:
        """Insert notes with standardized structure handling"""
        try:
            for i, note in enumerate(notes):
                print(f"   📝 Note {i+1}: {note}")
                
                insert_query = """
                INSERT INTO tariff_notes (
                    tariff_document_id, note_type, note_code, note_text, sort_order
                ) VALUES (?, ?, ?, ?, ?)
                """
                
                # Handle different key names for note fields
                note_type = (
                    note.get('type') or 
                    note.get('note_type') or 
                    'GENERAL'
                )
                
                note_code = (
                    note.get('code') or 
                    note.get('note_code') or 
                    ''
                )
                
                note_text = (
                    note.get('text') or 
                    note.get('note_text') or
                    note.get('content') or
                    ''
                )
                
                params = (
                    document_id,
                    note_type[:20],  # Limit length
                    note_code[:10],
                    note_text[:2000],  # Limit text length
                    int(note.get('sort_order', i))
                )
                
                cursor.execute(insert_query, params)
                print(f"   ✅ Note {i+1} inserted")
            
            return True
                
        except Exception as e:
            print(f"❌ Note insertion error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _verify_document_save(self, cursor, document_id: int):
        """Verify that data was saved correctly"""
        try:
            # Check document
            cursor.execute("SELECT COUNT(*) FROM tariff_documents WHERE id = ?", (document_id,))
            doc_count = cursor.fetchone()[0]
            print(f"   📋 Documents with ID {document_id}: {doc_count}")
            
            # Check commodities
            cursor.execute("SELECT COUNT(*) FROM tariff_commodities WHERE tariff_document_id = ?", (document_id,))
            commodity_count = cursor.fetchone()[0]
            print(f"   📦 Commodities for document {document_id}: {commodity_count}")
            
            # Check rates
            cursor.execute("SELECT COUNT(*) FROM tariff_rates WHERE tariff_document_id = ?", (document_id,))
            rate_count = cursor.fetchone()[0]
            print(f"   💰 Rates for document {document_id}: {rate_count}")
            
            # Check notes
            cursor.execute("SELECT COUNT(*) FROM tariff_notes WHERE tariff_document_id = ?", (document_id,))
            note_count = cursor.fetchone()[0]
            print(f"   📝 Notes for document {document_id}: {note_count}")
            
        except Exception as e:
            print(f"❌ Verification error: {e}")
    
    def search_tariff_documents(self, **criteria) -> List[Dict]:
        """Search tariffs based on criteria with enhanced filtering"""
        conn = self.get_database_connection()
        if conn is None:
            return []
        
        try:
            cursor = conn.cursor()
            query = """
            SELECT d.id, d.item_number, d.revision, d.effective_date, d.expiration_date,
                   d.origin_info, d.destination_info, d.currency, d.pdf_name,
                   r.origin, r.destination, r.rate_amount, r.currency as rate_currency
            FROM tariff_documents d
            LEFT JOIN tariff_rates r ON d.id = r.tariff_document_id
            WHERE 1=1
            """
            
            params = []
            
            # Add filters based on criteria
            if criteria.get('origin'):
                query += " AND (r.origin LIKE ? OR d.origin_info LIKE ?)"
                origin_pattern = f"%{criteria['origin']}%"
                params.extend([origin_pattern, origin_pattern])
            
            if criteria.get('destination'):
                query += " AND (r.destination LIKE ? OR d.destination_info LIKE ?)"
                dest_pattern = f"%{criteria['destination']}%"
                params.extend([dest_pattern, dest_pattern])
            
            if criteria.get('item_number'):
                query += " AND d.item_number = ?"
                params.append(criteria['item_number'])
            
            # Only include active documents by default
            if not criteria.get('include_expired'):
                query += " AND (d.expiration_date IS NULL OR d.expiration_date > GETDATE())"
            
            query += " ORDER BY d.effective_date DESC, d.item_number"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in results]
            
        except Exception as e:
            print(f"❌ Error searching tariffs: {e}")
            return []
        finally:
            conn.close()
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
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
            
            # Get latest document info
            cursor.execute("""
                SELECT TOP 1 item_number, effective_date, pdf_name 
                FROM tariff_documents 
                ORDER BY created_at DESC
            """)
            latest_doc = cursor.fetchone()
            
            stats = {
                "total_documents": doc_count,
                "total_rates": rate_count,
                "total_commodities": commodity_count,
                "total_notes": note_count,
                "database_status": "connected"
            }
            
            if latest_doc:
                stats["latest_document"] = {
                    "item_number": latest_doc[0],
                    "effective_date": latest_doc[1].isoformat() if latest_doc[1] else None,
                    "pdf_name": latest_doc[2]
                }
            
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
            conn.close()

    # Alias methods for backward compatibility
    def test_connection(self):
        """Alias for test_database_connection"""
        return self.test_database_connection()
    
    def save_tariff_document(self, extracted_data: Dict[str, Any], pdf_path: str = "") -> Optional[int]:
        """Alias for save_tariff_document_complete"""
        return self.save_tariff_document_complete(extracted_data, pdf_path)
    
    def search_tariffs(self, **criteria):
        """Alias for search_tariff_documents"""
        return self.search_tariff_documents(**criteria)
    
    def get_statistics(self):
        """Alias for get_database_statistics"""
        return self.get_database_statistics()

# Create a default instance for backward compatibility
tariff_database = CPTariffDatabase()
