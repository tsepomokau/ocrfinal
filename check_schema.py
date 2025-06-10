import pyodbc

def check_database_schema():
    """Check what columns actually exist in your database"""
    
    connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=DESKTOP-KL51D0H\\SQLEXPRESS;DATABASE=cp_tariff;Trusted_Connection=yes"
    
    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        print("🔍 INVESTIGATING YOUR DATABASE SCHEMA")
        print("=" * 50)
        
        # Check tariff_documents table
        print("\n📋 TARIFF_DOCUMENTS table columns:")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'tariff_documents'
            ORDER BY ORDINAL_POSITION
        """)
        
        docs_columns = cursor.fetchall()
        for col in docs_columns:
            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
            max_len = f"({col[3]})" if col[3] else ""
            print(f"   ✅ {col[0]:<25} {col[1]}{max_len:<15} {nullable}")
        
        # Check tariff_rates table  
        print("\n💰 TARIFF_RATES table columns:")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'tariff_rates'
            ORDER BY ORDINAL_POSITION
        """)
        
        rates_columns = cursor.fetchall()
        for col in rates_columns:
            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
            max_len = f"({col[3]})" if col[3] else ""
            print(f"   ✅ {col[0]:<25} {col[1]}{max_len:<15} {nullable}")
            
        # Check tariff_commodities table
        print("\n📦 TARIFF_COMMODITIES table columns:")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'tariff_commodities'
            ORDER BY ORDINAL_POSITION
        """)
        
        commodities_columns = cursor.fetchall()
        for col in commodities_columns:
            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
            max_len = f"({col[3]})" if col[3] else ""
            print(f"   ✅ {col[0]:<25} {col[1]}{max_len:<15} {nullable}")
            
        # Check tariff_notes table
        print("\n📝 TARIFF_NOTES table columns:")
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'tariff_notes'
            ORDER BY ORDINAL_POSITION
        """)
        
        notes_columns = cursor.fetchall()
        for col in notes_columns:
            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
            max_len = f"({col[3]})" if col[3] else ""
            print(f"   ✅ {col[0]:<25} {col[1]}{max_len:<15} {nullable}")
        
        print("\n" + "=" * 50)
        print("🎯 COLUMN NAME MAPPING NEEDED:")
        print("=" * 50)
        
        # Analyze what needs to be fixed
        docs_column_names = [col[0] for col in docs_columns]
        
        if 'origin_location' not in docs_column_names:
            if 'origin_info' in docs_column_names:
                print("❌ Code uses 'origin_location' → should be 'origin_info'")
            elif 'origin' in docs_column_names:
                print("❌ Code uses 'origin_location' → should be 'origin'")
        
        if 'destination_location' not in docs_column_names:
            if 'destination_info' in docs_column_names:
                print("❌ Code uses 'destination_location' → should be 'destination_info'")
            elif 'destination' in docs_column_names:
                print("❌ Code uses 'destination_location' → should be 'destination'")
        
        if 'raw_text' not in docs_column_names:
            if 'raw_ocr_text' in docs_column_names:
                print("❌ Code uses 'raw_text' → should be 'raw_ocr_text'")
            elif 'ocr_text' in docs_column_names:
                print("❌ Code uses 'raw_text' → should be 'ocr_text'")
        
        print("\n🔧 NEXT STEPS:")
        print("1. Update your database file with the correct column names above")
        print("2. Restart your server")
        print("3. Test again")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
        return False

if __name__ == "__main__":
    check_database_schema()