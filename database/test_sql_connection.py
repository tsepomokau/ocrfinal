import pyodbc
import os

def test_sql_server():
    try:
        # Connection string for SQL Server Express with Windows Authentication
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=DESKTOP-KL51D0H\\SQLEXPRESS;"
            "DATABASE=cp_tariff;"
            "Trusted_Connection=yes;"
        )
        
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Test connection
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(f"✅ Connected to: {version}")
        
        # Check tables
        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'tariff_%'")
        table_count = cursor.fetchone()[0]
        print(f"✅ Found {table_count} tariff tables")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_sql_server()