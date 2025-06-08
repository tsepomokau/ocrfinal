import pyodbc
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class CPTariffDatabase:
    """Database handler for CP Tariff documents - FIXED VERSION"""
    
    def __init__(self, connection_string: str):
        """Initialize database connection"""
        self.connection_string = connection_string
        logger.info(f"🔗 Database configured: {connection_string}")
    
    def get_database_connection(self):
        """Get database connection - WORKING VERSION"""
        try:
            conn = pyodbc.connect(self.connection_string)
            return conn
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return None
    
    def save_document(self, data: Dict[str, Any]) -> Optional[int]:
        """Save document data to database - FIXED VERSION"""
        print("\n" + "="*50)
        print("💾 STARTING DATABASE SAVE PROCESS")
        print("="*50)
        
        conn = self.get_database_connection()
        if conn is None:
            print("❌ No database connection")
            return None
        
        try:
            cursor = conn.cursor()
            
            # Log input data structure
            print(f"📊 Input data structure:")
            print(f"   - Keys: {list(data.keys())}")
            print(f"   - Commodities: {len(data.get('commodities', []))}")
            print(f"   - Rates: {len(data.get('rates', []))}")
            print(f"   - Notes: {len(data.get('notes', []))}")
            print(f"   - Header: {data.get('header', {})}")
            
            print(f"\n🔄 STEP 1: Inserting main document...")
            
            # Get header data
            header = data.get('header', {})
            
            print(f"📝 Document data:")
            print(f"   - Header: {header}")
            print(f"   - PDF name: {data.get('pdf_name', 'unknown.pdf')}")
            print(f"   - Origin: {data.get('origin_info', '')}")
            print(f"   - Destination: {data.get('destination_info', '')}")
            
            # FIXED: Insert document with OUTPUT clause to get ID
            insert_sql = """
            INSERT INTO tariff_documents (
                item_number, revision, cprs_number, issue_date, 
                effective_date, expiration_date, change_description,
                pdf_name, origin_location, destination_location,
                upload_timestamp, raw_text
            ) 
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?)
            """
            
            # Prepare parameters with proper type conversion
            params = (
                str(header.get('item_number', '')),
                int(header.get('revision', 0)) if header.get('revision') else None,
                str(header.get('cprs_number', '')),
                header.get('issue_date'),
                header.get('effective_date'),
                header.get('expiration_date'),
                str(header.get('change_description', '')),
                str(data.get('pdf_name', 'unknown.pdf')),
                str(data.get('origin_info', '')),
                str(data.get('destination_info', '')),
                str(data.get('raw_text', ''))[:4000]  # Limit text length
            )
            
            print(f"🔧 SQL Parameters: {params[:6]}...")
            
            # FIXED: Execute and get document ID directly
            cursor.execute(insert_sql, params)
            result = cursor.fetchone()
            
            if result and result[0]:
                doc_id = int(result[0])
                print(f"✅ Document inserted with ID: {doc_id}")
                
                # Save related data
                print(f"\n🔄 STEP 2: Saving commodities...")
                commodities_saved = self._save_commodities(cursor, doc_id, data.get('commodities', []))
                print(f"✅ Saved {commodities_saved} commodities")
                
                print(f"\n🔄 STEP 3: Saving rates...")
                rates_saved = self._save_rates(cursor, doc_id, data.get('rates', []))
                print(f"✅ Saved {rates_saved} rates")
                
                print(f"\n🔄 STEP 4: Saving notes...")
                notes_saved = self._save_notes(cursor, doc_id, data.get('notes', []))
                print(f"✅ Saved {notes_saved} notes")
                
                # Commit all changes
                conn.commit()
                print(f"\n✅ All data saved successfully for document {doc_id}")
                print("="*50)
                
                return doc_id
            else:
                print(f"❌ Document insertion failed - no ID returned")
                print(f"📋 Document ID returned: {result}")
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
        """Save commodity data - FIXED VERSION"""
        saved_count = 0
        
        for commodity in commodities:
            try:
                cursor.execute("""
                    INSERT INTO tariff_commodities (
                        document_id, commodity_name, commodity_code, 
                        classification, created_at
                    ) VALUES (?, ?, ?, ?, GETDATE())
                """, (
                    doc_id,
                    str(commodity.get('name', ''))[:255],
                    str(commodity.get('code', ''))[:50],
                    str(commodity.get('classification', ''))[:100]
                ))
                saved_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error saving commodity: {e}")
                # Continue with other commodities
                continue
        
        return saved_count
    
    def _save_rates(self, cursor, doc_id: int, rates: List[Dict]) -> int:
        """Save rate data - FIXED VERSION"""
        saved_count = 0
        
        for rate in rates:
            try:
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
                    str(rate.get('rate_value', '0')),
                    str(rate.get('currency', 'CAD'))[:10],
                    str(rate.get('commodity', ''))[:255],
                    str(rate.get('equipment_type', ''))[:100]
                ))
                saved_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error saving rate: {e}")
                # Continue with other rates
                continue
        
        return saved_count
    
    def _save_notes(self, cursor, doc_id: int, notes: List[Dict]) -> int:
        """Save notes data - FIXED VERSION"""
        saved_count = 0
        
        for note in notes:
            try:
                cursor.execute("""
                    INSERT INTO tariff_notes (
                        document_id, note_type, description, applies_to,
                        created_at
                    ) VALUES (?, ?, ?, ?, GETDATE())
                """, (
                    doc_id,
                    str(note.get('type', 'GENERAL'))[:50],
                    str(note.get('description', ''))[:1000],
                    str(note.get('applies_to', 'ALL'))[:255]
                ))
                saved_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error saving note: {e}")
                # Continue with other notes
                continue
        
        return saved_count
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Get database statistics - WORKING VERSION"""
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
            
            # Get latest document info - SIMPLE VERSION
            latest_doc = None
            try:
                cursor.execute("""
                    SELECT TOP 1 item_number, effective_date, pdf_name 
                    FROM tariff_documents 
                    ORDER BY id DESC
                """)
                latest_doc = cursor.fetchone()
            except Exception:
                pass  # Ignore if this fails
            
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
            logger.error(f"❌ Error getting statistics: {e}")
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
    
    def get_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID - WORKING VERSION"""
        conn = self.get_database_connection()
        if conn is None:
            return None
        
        try:
            cursor = conn.cursor()
            
            # Get main document
            cursor.execute("""
                SELECT item_number, revision, cprs_number, issue_date,
                       effective_date, expiration_date, change_description,
                       pdf_name, origin_location, destination_location,
                       upload_timestamp, raw_text
                FROM tariff_documents 
                WHERE id = ?
            """, (doc_id,))
            
            doc_row = cursor.fetchone()
            if not doc_row:
                return None
            
            # Build document object
            document = {
                "id": doc_id,
                "item_number": doc_row[0],
                "revision": doc_row[1],
                "cprs_number": doc_row[2],
                "issue_date": doc_row[3].isoformat() if doc_row[3] else None,
                "effective_date": doc_row[4].isoformat() if doc_row[4] else None,
                "expiration_date": doc_row[5].isoformat() if doc_row[5] else None,
                "change_description": doc_row[6],
                "pdf_name": doc_row[7],
                "origin_location": doc_row[8],
                "destination_location": doc_row[9],
                "upload_timestamp": doc_row[10].isoformat() if doc_row[10] else None,
                "raw_text": doc_row[11]
            }
            
            # Get related data
            document["commodities"] = self._get_commodities_for_document(cursor, doc_id)
            document["rates"] = self._get_rates_for_document(cursor, doc_id)
            document["notes"] = self._get_notes_for_document(cursor, doc_id)
            
            return document
            
        except Exception as e:
            logger.error(f"❌ Error getting document {doc_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def _get_commodities_for_document(self, cursor, doc_id: int) -> List[Dict]:
        """Get commodities for a document"""
        cursor.execute("""
            SELECT commodity_name, commodity_code, classification
            FROM tariff_commodities 
            WHERE document_id = ?
        """, (doc_id,))
        
        return [
            {
                "name": row[0],
                "code": row[1],
                "classification": row[2]
            }
            for row in cursor.fetchall()
        ]
    
    def _get_rates_for_document(self, cursor, doc_id: int) -> List[Dict]:
        """Get rates for a document"""
        cursor.execute("""
            SELECT origin_location, destination_location, rate_value,
                   currency, commodity_type, equipment_type
            FROM tariff_rates 
            WHERE document_id = ?
        """, (doc_id,))
        
        return [
            {
                "origin": row[0],
                "destination": row[1],
                "rate_value": row[2],
                "currency": row[3],
                "commodity": row[4],
                "equipment_type": row[5]
            }
            for row in cursor.fetchall()
        ]
    
    def _get_notes_for_document(self, cursor, doc_id: int) -> List[Dict]:
        """Get notes for a document"""
        cursor.execute("""
            SELECT note_type, description, applies_to
            FROM tariff_notes 
            WHERE document_id = ?
        """, (doc_id,))
        
        return [
            {
                "type": row[0],
                "description": row[1],
                "applies_to": row[2]
            }
            for row in cursor.fetchall()
        ]
    
    def save_tariff_document_complete(self, data: Dict[str, Any], temp_path: str = None) -> Optional[int]:
        """
        Save complete tariff document - compatibility method
        temp_path parameter is ignored for compatibility with existing code
        """
        print(f"📁 save_tariff_document_complete called with temp_path: {temp_path}")
        print(f"🔄 Redirecting to save_document method...")
        return self.save_document(data)