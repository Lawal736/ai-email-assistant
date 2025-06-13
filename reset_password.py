#!/usr/bin/env python3
"""
Script to reset password for lawalmoruf@gmail.com
"""

import sqlite3
from werkzeug.security import generate_password_hash

def reset_password():
    """Reset password for lawalmoruf@gmail.com"""
    
    # New password
    new_password = "newpassword123"
    
    # Generate proper password hash
    password_hash = generate_password_hash(new_password)
    
    # Connect to database
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    try:
        # Update the password
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (password_hash, 'lawalmoruf@gmail.com')
        )
        
        # Check if update was successful
        if cursor.rowcount > 0:
            conn.commit()
            print("✅ Password reset successfully!")
            print(f"📧 Email: lawalmoruf@gmail.com")
            print(f"🔑 New Password: {new_password}")
            print("\n💡 You can now login with these credentials")
        else:
            print("❌ User not found or no changes made")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    reset_password() 