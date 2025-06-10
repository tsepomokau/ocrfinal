"""
Production Database Handler - Deployment Ready
File: backend/app/database/cp_tariff_database.py

Production-grade database handler with proper error handling and logging.
"""
import pyodbc
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class CPTariffDatabase:
    """Production database handler for CP Tariff documents"""
    
    def __init__(self, connection_string: str):
        """Initialize database connection"""
        self.connection_string = connection_string
        logger.info("Database handler initialized")
    
    def get_database_connection(self):
        """Get database connection with error handling"""
        try:
            conn = pyodbc.connect(self.connection_string)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return None
    
    def save_document(self, data: Dict[str, Any]) -> Optional[int]:
        """Save document data to database"""
        
        conn = self.get_database_connection()
        if conn is None:
            logger.error("Cannot save document - no database connection")
            return None
        
        try:
            cursor = conn.cursor()
            
            # Extract header data
            header = data.get('header', {})
            
            logger.info(f"Saving document: Item {header.get('item_number', 'N/A')}, "
                       f"Revision {header.get('revision', 'N/A')}")
            
            # Insert main document record
            insert_sql = """
            INSERT INTO tariff_documents (
                item_number, revision, cprs_number, issue_date, 
                effective_date, expiration_date, change_description,
                pdf_name, origin_info, destination_info,
                upload_timestamp, raw_ocr_text
            ) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?)
            """
            
            # Prepare parameters
            params = (
                str(header.get('item_number', '')),
                self._safe_int(header.get('revision', 0)),
                str(header.get('cprs_number', '')),
                self._parse_date(header.get('issue_date')),
                self._parse_date(header.get('effective_date')),
                self._parse_date(header.get('expiration_date')),
                str(header.get('change_description', '')),
                str(data.get('pdf_name', 'unknown.pdf')),
                str(data.get('origin_info', ''))[:500],
                str(data.get('destination_info', ''))[:500],
                str(data.get('raw_text', ''))[:4000]
            )
            
            # Execute insert
            cursor.execute(insert_sql, params)
            
            # Get document ID
            cursor.execute("SELECT @@IDENTITY")
            result = cursor.fetchone()
            
            if result and result[0]:
                doc_id = int(result[0])
                logger.info(f"Document inserted with ID: {doc_id}")
                
                # Save related data
                commodities_saved = self._save_commodities(cursor, doc_id, data.get('commodities', []))
                rates_saved = self._save_rates(cursor, doc_id, data.get('rates', []))
                notes_saved = self._save_notes(cursor, doc_id, data.get('notes', []))
                
                logger.info(f"Saved: {commodities_saved} commodities, {rates_saved} rates, {notes_saved} notes")
                
                # Commit all changes
                conn.commit()
                logger.info(f"Successfully saved all data for document {doc_id}")
                
                return doc_id
            else:
                logger.error("Document insertion failed - no ID returned")
                return None
                
        except Exception as e:
            logger.error(f"Database save error: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()
    
    def _save_commodities(self, cursor, doc_id: int, commodities: List[Dict]) -> int:
        """Save commodity data"""
        saved_count = 0
        
        for commodity in commodities:
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
                logger.error(f"Error saving commodity: {e}")
                continue
        
        return saved_count
    
    def _save_rates(self, cursor, doc_id: int, rates: List[Dict]) -> int:
        """Save rate data"""
        saved_count = 0
        
        for rate in rates:
            try:
                cursor.execute("""
                    INSERT INTO tariff_rates (
                        document_id, origin, destination,
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
                logger.error(f"Error saving rate: {e}")
                continue
        
        return saved_count
    
    def _save_notes(self, cursor, doc_id: int, notes: List[Dict]) -> int:
        """Save notes data"""
        saved_count = 0
        
        for note in notes:
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
                logger.error(f"Error saving note: {e}")
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
            try:
                # Validate date format
                datetime.strptime(date_str, '%Y-%m-%d')
                return date_str
            except ValueError:
                pass
        
        return str(date_str)
    
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
            
            # Get counts
            cursor.execute("SELECT COUNT(*) FROM tariff_documents")
            doc_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tariff_rates")
            rate_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tariff_commodities")
            commodity_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tariff_notes")
            note_count = cursor.fetchone()[0]
            
            # Get recent activity
            cursor.execute("""
                SELECT TOP 5 item_number, revision, upload_timestamp 
                FROM tariff_documents 
                ORDER BY upload_timestamp DESC
            """)
            recent_docs = cursor.fetchall()
            
            return {
                "total_documents": doc_count,
                "total_rates": rate_count,
                "total_commodities": commodity_count,
                "total_notes": note_count,
                "database_status": "connected",
                "recent_documents": [
                    {
                        "item": row[0], 
                        "revision": row[1], 
                        "uploaded": row[2].isoformat() if row[2] else None
                    } for row in recent_docs
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                "total_documents": 0,
                "total_rates": 0,
                "database_status": "error",
                "error": str(e)
            }
        finally:
            if conn:
                conn.close()
    
    def get_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        conn = self.get_database_connection()
        if conn is None:
            return None
        
        try:
            cursor = conn.cursor()
            
            # Get document
            cursor.execute("""
                SELECT item_number, revision, cprs_number, issue_date,
                       effective_date, expiration_date, pdf_name, 
                       origin_info, destination_info, upload_timestamp
                FROM tariff_documents 
                WHERE id = ?
            """, (doc_id,))
            
            doc_row = cursor.fetchone()
            if not doc_row:
                return None
            
            # Get rates
            cursor.execute("""
                SELECT origin, destination, rate_value, currency, equipment_type
                FROM tariff_rates 
                WHERE document_id = ?
            """, (doc_id,))
            rates = cursor.fetchall()
            
            # Get notes
            cursor.execute("""
                SELECT note_type, note_text
                FROM tariff_notes 
                WHERE document_id = ?
            """, (doc_id,))
            notes = cursor.fetchall()
            
            # Get commodities
            cursor.execute("""
                SELECT commodity_name, commodity_code, description
                FROM tariff_commodities 
                WHERE document_id = ?
            """, (doc_id,))
            commodities = cursor.fetchall()
            
            return {
                "document": {
                    "item_number": doc_row[0],
                    "revision": doc_row[1],
                    "cprs_number": doc_row[2],
                    "issue_date": doc_row[3],
                    "effective_date": doc_row[4],
                    "expiration_date": doc_row[5],
                    "pdf_name": doc_row[6],
                    "origin_info": doc_row[7],
                    "destination_info": doc_row[8],
                    "upload_timestamp": doc_row[9].isoformat() if doc_row[9] else None
                },
                "rates": [
                    {
                        "origin": rate[0],
                        "destination": rate[1],
                        "rate_value": float(rate[2]) if rate[2] else 0,
                        "currency": rate[3],
                        "equipment_type": rate[4]
                    } for rate in rates
                ],
                "notes": [
                    {
                        "type": note[0],
                        "text": note[1]
                    } for note in notes
                ],
                "commodities": [
                    {
                        "name": commodity[0],
                        "code": commodity[1],
                        "description": commodity[2]
                    } for commodity in commodities
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting document {doc_id}: {e}")
            return None
        finally:
            if conn:
                conn.close()