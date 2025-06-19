import sys
from models_postgresql import DatabaseManager

def set_user_as_admin(email):
    db = DatabaseManager()
    
    # Get user ID from email
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            result = cur.fetchone()
            if not result:
                print(f"❌ User with email {email} not found")
                return False
            
            user_id = result[0]
            
    # Set user as admin
    success = db.set_user_admin(user_id, True)
    if success:
        print(f"✅ Successfully set {email} as admin")
    else:
        print(f"❌ Failed to set {email} as admin")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python set_admin.py <email>")
        sys.exit(1)
        
    email = sys.argv[1]
    set_user_as_admin(email) 