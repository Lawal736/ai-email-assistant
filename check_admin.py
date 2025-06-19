import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Database connection parameters
db_params = {
    'dbname': os.getenv('DB_NAME', 'ai_email_assistant_db_aqxm'),
    'user': os.getenv('DB_USER', 'ai_email_assistant_db_aqxm_user'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST', 'dpg-cnm7ue0l5elc73c0ue00-a.oregon-postgres.render.com'),
    'port': os.getenv('DB_PORT', '5432')
}

try:
    # Connect to the database
    conn = psycopg2.connect(**db_params)
    cursor = conn.cursor()
    
    # Query to check admin status
    cursor.execute("SELECT email, is_admin FROM users WHERE email = 'lawalmoruf@gmail.com';")
    result = cursor.fetchone()
    
    if result:
        email, is_admin = result
        print(f"User {email} admin status: {is_admin}")
    else:
        print("User not found")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close() 