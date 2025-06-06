"""
Debug CP Tariff Database Manager with extensive logging
"""
import pyodbc
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

class CPTariffDatabase:
    """Database manager with detailed debugging"""
    
    def __init__(self):
        """Initialize database connection"""
        self.server = os.getenv('DB_SERVER', 'DESKTOP-KL51D0H\\SQLEXPRESS')
        self.database = os.getenv('DB_NAME', 'cp_tariff')
        
        self.connection_string = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            "Trusted_Connection=yes;"
        )
        
        print(f"🔗 Database configured: {self.server}/{self.database}")
    
    def get_connection(self):
        """Get database connection"""
        try:
            return pyodbc.connect(self.connection_string)
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = self.get_connection()
            if conn is None:
                return False
            
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            conn.close()
            
            print("✅ Database connection successful")
            return True
            
        except Exception as e:
            print(f"❌ Database connection test failed: {e}")
            return False
    
    def save_tariff_document(self, extracted_data: Dict[str, Any], pdf_path: str = "") -> Optional[int]:
        """Save complete tariff document data to database with detailed debugging"""
        print("\n" + "="*50)
        print("💾 STARTING DATABASE SAVE PROCESS")
        print("="*50)
        
        print(f"📊 Input data structure:")
        print(f"   - Keys: {list(extracted_data.keys())}")
        print(f"   - Commodities: {len(extracted_data.get('commodities', []))}")
        print(f"   - Rates: {len(extracted_data.get('rates', []))}")
        print(f"   - Notes: {len(extracted_data.get('notes', []))}")
        print(f"   - Header: {extracted_data.get('header', {})}")
        
        conn = self.get_connection()
        if conn is None:
            print("❌ Cannot connect to database - aborting save")
            return None
        
        try:
            cursor = conn.cursor()
            
            # Step 1: Insert main document
            print("\n🔄 STEP 1: Inserting main document...")
            document_id = self._insert_document_debug(cursor, extracted_data, pdf_path)
            
            if not document_id:
                print("❌ Document insertion failed - cannot proceed")
                conn.rollback()
                return None
            
            print(f"✅ Document inserted successfully with ID: {document_id}")
            
            # Step 2: Insert commodities
            commodities = extracted_data.get('commodities', [])
            if commodities:
                print(f"\n🔄 STEP 2: Inserting {len(commodities)} commodities...")
                success = self._insert_commodities_debug(cursor, document_id, commodities)
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
                success = self._insert_rates_debug(cursor, document_id, rates)
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
                success = self._insert_notes_debug(cursor, document_id, notes)
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
            self._verify_save(cursor, document_id)
            
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
    
    def _insert_document_debug(self, cursor, data: Dict[str, Any], pdf_path: str) -> Optional[int]:
        """Insert main document record with debugging"""
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
            
            params = (
                header.get('item_number', ''),
                int(header.get('revision', 0)) if header.get('revision') else None,
                header.get('cprs_number', ''),
                self._parse_date(header.get('issue_date')),
                self._parse_date(header.get('effective_date')),
                self._parse_date(header.get('expiration_date')),
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
            
            # Get the inserted ID
            cursor.execute("SELECT @@IDENTITY")
            result = cursor.fetchone()
            document_id = int(result[0]) if result else None
            
            print(f"📋 Document ID returned: {document_id}")
            return document_id
            
        except Exception as e:
            print(f"❌ Document insertion error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _insert_commodities_debug(self, cursor, document_id: int, commodities: List[Dict]) -> bool:
        """Insert commodities with debugging"""
        try:
            for i, commodity in enumerate(commodities):
                print(f"   📦 Commodity {i+1}: {commodity}")
                
                insert_query = """
                INSERT INTO tariff_commodities (
                    tariff_document_id, commodity_name, stcc_code, description
                ) VALUES (?, ?, ?, ?)
                """
                
                params = (
                    document_id,
                    commodity.get('name', ''),
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
    
    def _insert_rates_debug(self, cursor, document_id: int, rates: List[Dict]) -> bool:
        """Insert rates with debugging"""
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
                
                params = (
                    document_id,
                    rate.get('origin', ''),
                    rate.get('destination', ''),
                    rate.get('origin_state', ''),
                    rate.get('destination_state', ''),
                    rate.get('rate_category', ''),
                    float(rate.get('rate_amount', 0)) if rate.get('rate_amount') else None,
                    rate.get('currency', 'USD'),
                    rate.get('train_type', ''),
                    rate.get('car_capacity_type', ''),
                    rate.get('route_code', ''),
                    rate.get('additional_provisions', '')
                )
                
                print(f"   🔧 Rate parameters: {params}")
                cursor.execute(insert_query, params)
                print(f"   ✅ Rate {i+1} inserted")
            
            return True
                
        except Exception as e:
            print(f"❌ Rate insertion error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _insert_notes_debug(self, cursor, document_id: int, notes: List[Dict]) -> bool:
        """Insert notes with debugging"""
        try:
            for i, note in enumerate(notes):
                print(f"   📝 Note {i+1}: {note}")
                
                insert_query = """
                INSERT INTO tariff_notes (
                    tariff_document_id, note_type, note_code, note_text, sort_order
                ) VALUES (?, ?, ?, ?, ?)
                """
                
                params = (
                    document_id,
                    note.get('type', 'GENERAL'),
                    note.get('code', ''),
                    note.get('text', ''),
                    int(note.get('sort_order', 0))
                )
                
                cursor.execute(insert_query, params)
                print(f"   ✅ Note {i+1} inserted")
            
            return True
                
        except Exception as e:
            print(f"❌ Note insertion error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _verify_save(self, cursor, document_id: int):
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
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to proper format"""
        if not date_str:
            return None
        return date_str
    
    # ... (rest of the methods remain the same)
    def search_tariffs(self, **criteria) -> List[Dict]:
        """Search tariffs based on criteria"""
        conn = self.get_connection()
        if conn is None:
            return []
        
        try:
            cursor = conn.cursor()
            query = """
            SELECT d.item_number, d.revision, d.effective_date, d.expiration_date,
                   r.origin, r.destination, r.rate_amount, r.currency
            FROM tariff_documents d
            LEFT JOIN tariff_rates r ON d.id = r.tariff_document_id
            WHERE d.status = 'ACTIVE'
            """
            
            params = []
            if criteria.get('origin'):
                query += " AND r.origin LIKE ?"
                params.append(f"%{criteria['origin']}%")
            
            if criteria.get('destination'):
                query += " AND r.destination LIKE ?"
                params.append(f"%{criteria['destination']}%")
            
            query += " ORDER BY d.effective_date DESC"
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in results]
            
        except Exception as e:
            print(f"❌ Error searching tariffs: {e}")
            return []
        finally:
            conn.close()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = self.get_connection()
        if conn is None:
            return {
                "total_documents": 0,
                "total_rates": 0,
                "database_status": "disconnected"
            }
        
        try:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM tariff_documents")
            doc_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tariff_rates")
            rate_count = cursor.fetchone()[0]
            
            return {
                "total_documents": doc_count,
                "total_rates": rate_count,
                "database_status": "connected"
            }
            
        except Exception as e:
            print(f"❌ Error getting statistics: {e}")
            return {
                "total_documents": 0,
                "total_rates": 0,
                "database_status": "error"
            }
        finally:
            conn.close()

# Create a default instance
database = CPTariffDatabase()