#!/usr/bin/env python3
"""
Verify database schema is correct after migration.
"""

import os
from sqlalchemy import create_engine, text

def verify_database():
    """Verify that the database schema is correct."""
    default_db = "postgresql://postgres:yatri04112005y@localhost:5432/attendance_db"
    database_url = os.environ.get("DATABASE_URL", default_db)
    
    # Normalize PostgreSQL URL
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if department_id column exists
            check_column_query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'department_id'
            """
            
            result = conn.execute(text(check_column_query))
            column_info = result.fetchone()
            
            if column_info:
                print(f"✅ department_id column exists: {column_info[0]} ({column_info[1]}, nullable: {column_info[2]})")
            else:
                print("❌ department_id column not found")
                return False
            
            # Check user_roles enum values
            check_enum_query = """
            SELECT unnest(enum_range(NULL::user_roles)) as role_name
            ORDER BY role_name
            """
            
            result = conn.execute(text(check_enum_query))
            roles = [row[0] for row in result.fetchall()]
            
            print(f"✅ Available user roles: {', '.join(roles)}")
            
            expected_roles = ['admin', 'hod', 'principal', 'student', 'teacher']
            missing_roles = [role for role in expected_roles if role not in roles]
            
            if missing_roles:
                print(f"❌ Missing roles: {', '.join(missing_roles)}")
                return False
            else:
                print("✅ All expected roles are present")
            
            # Check if index exists
            check_index_query = """
            SELECT indexname 
            FROM pg_indexes 
            WHERE tablename = 'users' AND indexname = 'ix_users_department_id'
            """
            
            result = conn.execute(text(check_index_query))
            index_exists = result.fetchone() is not None
            
            if index_exists:
                print("✅ Index on department_id column exists")
            else:
                print("⚠️  Index on department_id column not found")
            
            return True
            
    except Exception as e:
        print(f"❌ Error verifying database: {e}")
        return False

if __name__ == "__main__":
    if verify_database():
        print("🎉 Database verification successful!")
    else:
        print("❌ Database verification failed!")
