# Database Migration Plan: SQLite → PostgreSQL on Digital Ocean

## Overview
Migrate from SQLite to Digital Ocean Managed PostgreSQL for better scalability, reliability, and performance.

## Phase 1: Preparation (Week 1)

### 1.1 Create Digital Ocean Managed Database
```bash
# Via Digital Ocean Dashboard:
1. Create PostgreSQL cluster (smallest size initially)
2. Configure security settings
3. Get connection credentials
4. Set up connection pooling
```

### 1.2 Database Schema Migration
```python
# Create PostgreSQL-compatible schema
# File: migrations/postgresql_schema.sql

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    gmail_token TEXT,
    gmail_email VARCHAR(255),
    subscription_plan VARCHAR(50) DEFAULT 'free',
    subscription_status VARCHAR(50) DEFAULT 'active',
    subscription_expires TIMESTAMP,
    stripe_customer_id VARCHAR(100),
    api_usage_count INTEGER DEFAULT 0,
    monthly_usage_limit INTEGER DEFAULT 100
);

CREATE TABLE subscription_plans (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    price_monthly DECIMAL(10,2) NOT NULL,
    price_yearly DECIMAL(10,2) NOT NULL,
    email_limit INTEGER NOT NULL,
    features TEXT,
    stripe_price_id_monthly VARCHAR(100),
    stripe_price_id_yearly VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE
);

-- Add indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_subscription ON users(subscription_plan, subscription_status);
CREATE INDEX idx_usage_tracking_user_date ON usage_tracking(user_id, created_at);
```

### 1.3 Update Database Connection Layer
```python
# File: database_config.py
import os
import psycopg2
from psycopg2.pool import ThreadedConnectionPool

class DatabaseConfig:
    def __init__(self):
        self.db_type = os.getenv('DB_TYPE', 'sqlite')  # sqlite or postgresql
        
        if self.db_type == 'postgresql':
            self.pg_config = {
                'host': os.getenv('DB_HOST'),
                'port': os.getenv('DB_PORT', 5432),
                'database': os.getenv('DB_NAME'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD'),
                'sslmode': 'require'
            }
            self.connection_pool = ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                **self.pg_config
            )
    
    def get_connection(self):
        if self.db_type == 'postgresql':
            return self.connection_pool.getconn()
        else:
            # Fallback to SQLite for development
            return sqlite3.connect('users.db')
```

## Phase 2: Dual Database Operation (Week 2)

### 2.1 Implement Database Abstraction Layer
```python
# File: database_abstraction.py
class DatabaseAbstraction:
    def __init__(self, config):
        self.config = config
        self.db_type = config.db_type
    
    def execute_query(self, query, params=None, fetch=False):
        conn = self.config.get_connection()
        try:
            if self.db_type == 'postgresql':
                cursor = conn.cursor()
                cursor.execute(query, params)
                if fetch:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount
                conn.commit()
                return result
            else:
                # SQLite logic
                cursor = conn.cursor()
                cursor.execute(query, params)
                if fetch:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount
                conn.commit()
                return result
        finally:
            if self.db_type == 'postgresql':
                self.config.connection_pool.putconn(conn)
            else:
                conn.close()
```

### 2.2 Data Migration Script
```python
# File: migrate_data.py
import sqlite3
import psycopg2
from datetime import datetime

def migrate_sqlite_to_postgresql():
    """Migrate all data from SQLite to PostgreSQL"""
    
    # Connect to both databases
    sqlite_conn = sqlite3.connect('users.db')
    pg_conn = psycopg2.connect(**postgresql_config)
    
    tables_to_migrate = [
        'users',
        'subscription_plans', 
        'payment_records',
        'usage_tracking',
        'password_reset_tokens',
        'user_preferences'
    ]
    
    for table in tables_to_migrate:
        print(f"Migrating {table}...")
        
        # Read from SQLite
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute(f"SELECT * FROM {table}")
        rows = sqlite_cursor.fetchall()
        
        # Get column names
        column_names = [description[0] for description in sqlite_cursor.description]
        
        # Insert into PostgreSQL
        pg_cursor = pg_conn.cursor()
        
        for row in rows:
            placeholders = ','.join(['%s'] * len(row))
            columns = ','.join(column_names)
            
            insert_query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
            
            try:
                pg_cursor.execute(insert_query, row)
            except Exception as e:
                print(f"Error migrating row in {table}: {e}")
                # Handle conflicts, data type issues, etc.
        
        pg_conn.commit()
        print(f"✅ {table} migrated successfully")
    
    sqlite_conn.close()
    pg_conn.close()
```

## Phase 3: Testing & Validation (Week 3)

### 3.1 Environment Variables Update
```bash
# Add to Digital Ocean App Environment
DB_TYPE=postgresql
DB_HOST=your-postgres-host.db.ondigitalocean.com
DB_PORT=25060
DB_NAME=ai-email-assistant
DB_USER=your-username
DB_PASSWORD=your-password
DB_SSL_MODE=require
```

### 3.2 Validation Scripts
```python
# File: validate_migration.py
def validate_data_integrity():
    """Compare SQLite and PostgreSQL data"""
    
    # Count records in each table
    tables = ['users', 'payment_records', 'usage_tracking']
    
    for table in tables:
        sqlite_count = get_sqlite_count(table)
        pg_count = get_postgresql_count(table)
        
        if sqlite_count == pg_count:
            print(f"✅ {table}: {sqlite_count} records match")
        else:
            print(f"❌ {table}: SQLite={sqlite_count}, PostgreSQL={pg_count}")
    
    # Validate specific user data
    test_user_data_consistency()
    test_authentication_flow()
    test_gmail_token_storage()
```

## Phase 4: Production Cutover (Week 4)

### 4.1 Blue-Green Deployment
1. **Blue Environment**: Current SQLite setup
2. **Green Environment**: New PostgreSQL setup
3. **Gradual Migration**: 
   - 10% traffic → PostgreSQL
   - 50% traffic → PostgreSQL  
   - 100% traffic → PostgreSQL

### 4.2 Rollback Plan
```python
# Emergency rollback to SQLite
if postgresql_issues_detected():
    # Switch DB_TYPE back to sqlite
    # Sync any new data from PostgreSQL back to SQLite
    # Redirect traffic back to SQLite
```

## Benefits After Migration

### Performance Improvements
- **10x faster** complex queries
- **Better concurrency** handling
- **Connection pooling** efficiency
- **Query optimization** capabilities

### Reliability Improvements  
- **Automatic backups** (point-in-time recovery)
- **High availability** with failover
- **Data corruption** protection
- **ACID compliance** guarantees

### Scalability Improvements
- **Horizontal scaling** options
- **Read replicas** for performance
- **Connection limits** handling
- **Resource monitoring**

## Cost Estimation
- **Basic PostgreSQL Cluster**: $15-25/month
- **Production-ready Setup**: $50-100/month
- **High-availability**: $100-200/month

## Timeline
- **Week 1**: Setup & Schema Migration
- **Week 2**: Code Updates & Dual Operation
- **Week 3**: Data Migration & Testing  
- **Week 4**: Production Cutover

## Emergency Fixes Compatibility
All current emergency fixes will work with PostgreSQL:
- ✅ User recovery mechanisms
- ✅ Token persistence safeguards
- ✅ Session/database consistency checks
- ✅ Automatic corruption detection

The emergency fixes provide an additional safety layer regardless of database backend. 