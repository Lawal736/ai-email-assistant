#!/usr/bin/env python3

from models import DatabaseManager, User

def create_test_admin():
    """Create a test admin user"""
    try:
        db_manager = DatabaseManager()
        user_model = User(db_manager)
        
        # Create a test admin user
        user_model.create_user('admin@test.com', 'admin123', 'Admin', 'User')
        
        # Set as admin
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_admin = 1 WHERE email = ?', ('admin@test.com',))
        conn.commit()
        conn.close()
        
        print('✅ Admin user created successfully')
        print('Email: admin@test.com')
        print('Password: admin123')
        
        # Test admin dashboard methods
        print('\n🧪 Testing admin dashboard methods:')
        
        # Test count_users
        total_users = user_model.count_users()
        print(f'Total users: {total_users}')
        
        # Test get_active_subscriptions_count
        active_subs = user_model.get_active_subscriptions_count()
        print(f'Active subscriptions: {active_subs}')
        
        # Test get_recent_activity
        recent_activity = user_model.get_recent_activity(limit=5)
        print(f'Recent activity count: {len(recent_activity)}')
        
        # Test get_table_stats
        table_stats = user_model.db_manager.get_table_stats()
        print(f'Table stats: {len(table_stats)} tables found')
        
        print('\n✅ All admin dashboard methods working correctly!')
        
    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == '__main__':
    create_test_admin() 