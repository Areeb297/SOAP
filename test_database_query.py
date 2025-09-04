import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
database_url = os.getenv('DATABASE_URL')

if database_url:
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Test the exact query that's failing
        query = """
            SELECT T."TypeName", C."CodeDisplayValue" 
            FROM "Sys_TypeLookups" T
            INNER JOIN "Sys_Codes" C ON T."TypeID" = C."TypeID"
            WHERE C."CodeDisplayValue" ILIKE %s
            LIMIT 10
        """
        
        # Test with 'gabapentin'
        print('=== Testing database query for gabapentin ===')
        cursor.execute(query, ('%gabapentin%',))
        results = cursor.fetchall()
        
        print(f'Found {len(results)} results for gabapentin:')
        for i, row in enumerate(results):
            print(f'{i+1}. TypeName: "{row["TypeName"]}" | CodeDisplayValue: "{row["CodeDisplayValue"]}"')
        
        # Test with 'lamotrigine'
        print('\n=== Testing database query for lamotrigine ===')
        cursor.execute(query, ('%lamotrigine%',))
        results = cursor.fetchall()
        
        print(f'Found {len(results)} results for lamotrigine:')
        for i, row in enumerate(results):
            print(f'{i+1}. TypeName: "{row["TypeName"]}" | CodeDisplayValue: "{row["CodeDisplayValue"]}"')
            
        # Test with 'fludarabine'
        print('\n=== Testing database query for fludarabine ===')
        cursor.execute(query, ('%fludarabine%',))
        results = cursor.fetchall()
        
        print(f'Found {len(results)} results for fludarabine:')
        for i, row in enumerate(results):
            print(f'{i+1}. TypeName: "{row["TypeName"]}" | CodeDisplayValue: "{row["CodeDisplayValue"]}"')
            
        # Let's also check what tables exist
        print('\n=== Checking available tables ===')
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print('Available tables:')
        for table in tables:
            print(f'  - {table["table_name"]}')
            
        # Let's check the structure of the Sys_Codes table
        print('\n=== Checking Sys_Codes table structure ===')
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = 'Sys_Codes' AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        print('Sys_Codes table columns:')
        for col in columns:
            print(f'  - {col["column_name"]} ({col["data_type"]})')
            
        # Let's see some sample data from Sys_Codes
        print('\n=== Sample data from Sys_Codes table ===')
        cursor.execute("""
            SELECT "CodeDisplayValue", "TypeID"
            FROM "Sys_Codes" 
            WHERE "CodeDisplayValue" IS NOT NULL 
            AND LENGTH("CodeDisplayValue") > 5
            LIMIT 10
        """)
        samples = cursor.fetchall()
        print('Sample CodeDisplayValue entries:')
        for sample in samples:
            print(f'  - "{sample["CodeDisplayValue"]}" (TypeID: {sample["TypeID"]})')
            
        cursor.close()
        conn.close()
        print('\nDatabase connection successful!')
        
    except Exception as e:
        print(f'Database error: {e}')
        import traceback
        traceback.print_exc()
else:
    print('DATABASE_URL not found in environment')
