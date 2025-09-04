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
        
        # Check the structure of the drug confusion table
        print('=== Checking top_50_worldwide_drugs_with_confusion table structure ===')
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = 'top_50_worldwide_drugs_with_confusion' AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        print('Table columns:')
        for col in columns:
            print(f'  - {col["column_name"]} ({col["data_type"]})')
            
        # Get sample data from this table
        print('\n=== Sample data from top_50_worldwide_drugs_with_confusion ===')
        cursor.execute("""
            SELECT * FROM "top_50_worldwide_drugs_with_confusion" 
            LIMIT 10
        """)
        samples = cursor.fetchall()
        print(f'Found {len(samples)} sample rows:')
        for i, sample in enumerate(samples):
            print(f'{i+1}. {dict(sample)}')
            
        # Test specific drugs that are causing issues
        print('\n=== Testing for gabapentin in drug confusion table ===')
        cursor.execute("""
            SELECT * FROM "top_50_worldwide_drugs_with_confusion" 
            WHERE LOWER("Drug name") LIKE %s OR LOWER("Similar/Confused drugs") LIKE %s
        """, ('%gabapentin%', '%gabapentin%'))
        results = cursor.fetchall()
        print(f'Found {len(results)} results for gabapentin:')
        for result in results:
            print(f'  - {dict(result)}')
            
        print('\n=== Testing for lamotrigine in drug confusion table ===')
        cursor.execute("""
            SELECT * FROM "top_50_worldwide_drugs_with_confusion" 
            WHERE LOWER("Drug name") LIKE %s OR LOWER("Similar/Confused drugs") LIKE %s
        """, ('%lamotrigine%', '%lamotrigine%'))
        results = cursor.fetchall()
        print(f'Found {len(results)} results for lamotrigine:')
        for result in results:
            print(f'  - {dict(result)}')
            
        print('\n=== Testing for fludarabine in drug confusion table ===')
        cursor.execute("""
            SELECT * FROM "top_50_worldwide_drugs_with_confusion" 
            WHERE LOWER("Drug name") LIKE %s OR LOWER("Similar/Confused drugs") LIKE %s
        """, ('%fludarabine%', '%fludarabine%'))
        results = cursor.fetchall()
        print(f'Found {len(results)} results for fludarabine:')
        for result in results:
            print(f'  - {dict(result)}')
            print(f'    Alternatives: {result["Similar/Confused drugs"]}')
            # Test the splitting logic
            alternatives = result["Similar/Confused drugs"].split(',')
            print(f'    Split alternatives: {alternatives}')
            
        cursor.close()
        conn.close()
        print('\nDatabase connection successful!')
        
    except Exception as e:
        print(f'Database error: {e}')
        import traceback
        traceback.print_exc()
else:
    print('DATABASE_URL not found in environment')
