# Database Persistence Fix for Digital Ocean

## Problem
SQLite database is stored in container filesystem and gets reset on every deployment, causing:
- User accounts to disappear
- Need to re-register after each deployment
- Loss of all user data and settings

## Solution: Add Volume Mount for Database

### Step 1: Update Digital Ocean App Spec
Add a volume mount to persist the database file:

```yaml
# In your app.yaml or Digital Ocean console
name: ai-email-assistant
services:
- name: web
  source_dir: /
  github:
    repo: Lawal736/ai-email-assistant
    branch: main
  run_command: gunicorn --bind 0.0.0.0:$PORT app:app --workers 2 --threads 4 --timeout 120
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  # ADD THIS SECTION:
  volumes:
  - name: database-volume
    mount_path: /app/data
    size: 1GB
    
# Then update your app to use /app/data/users.db instead of ./users.db
```

### Step 2: Update models.py to use persistent path

```python
# In models.py, change:
class DatabaseManager:
    def __init__(self, db_path='users.db'):  # OLD
    def __init__(self, db_path='/app/data/users.db'):  # NEW
```

### Step 3: Create data directory in Dockerfile (if using custom Docker)

```dockerfile
# Create persistent data directory
RUN mkdir -p /app/data
VOLUME /app/data
```

## Alternative: Use Digital Ocean Managed Database
1. Create PostgreSQL database in Digital Ocean
2. Update connection string
3. Migrate from SQLite to PostgreSQL

## Quick Workaround (Temporary)
Export/import user data on each deployment:
1. Add backup endpoint to export users
2. Create restore script for after deployment
3. Manually restore user data 