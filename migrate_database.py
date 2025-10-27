#!/usr/bin/env python3
"""
Database migration script to add department_id column to users table.
This script handles the database schema update for the new HOD and Principal roles.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

def get_database_url():
    """Get database URL from environment or use default."""
    default_db = "postgresql://postgres:yatri04112005y@localhost:5432/attendance_db"
    return os.environ.get("DATABASE_URL", default_db)

def migrate_database():
    """Add department_id column to users table if it doesn't exist."""
    database_url = get_database_url()
    
    # Normalize PostgreSQL URL
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if department_id column already exists
            check_column_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'department_id'
            """
            
            result = conn.execute(text(check_column_query))
            column_exists = result.fetchone() is not None
            
            if not column_exists:
                print("Adding department_id column to users table...")
                
                # Add the department_id column
                alter_table_query = """
                ALTER TABLE users 
                ADD COLUMN department_id INTEGER REFERENCES departments(id)
                """
                
                conn.execute(text(alter_table_query))
                conn.commit()
                
                print("✅ Successfully added department_id column to users table")
                
                # Add index for better performance
                try:
                    index_query = """
                    CREATE INDEX IF NOT EXISTS ix_users_department_id ON users(department_id)
                    """
                    conn.execute(text(index_query))
                    conn.commit()
                    print("✅ Successfully added index on department_id column")
                except Exception as e:
                    print(f"⚠️  Warning: Could not create index on department_id: {e}")
                
            else:
                print("✅ department_id column already exists in users table")
                
            # Update the user_roles enum to include new roles
            print("Updating user_roles enum...")
            
            # Check if new roles are already in the enum
            check_enum_query = """
            SELECT unnest(enum_range(NULL::user_roles)) as role_name
            """
            
            result = conn.execute(text(check_enum_query))
            existing_roles = [row[0] for row in result.fetchall()]
            
            if 'hod' not in existing_roles or 'principal' not in existing_roles:
                # Add new roles to the enum
                try:
                    add_roles_query = """
                    ALTER TYPE user_roles ADD VALUE IF NOT EXISTS 'hod';
                    ALTER TYPE user_roles ADD VALUE IF NOT EXISTS 'principal';
                    """
                    conn.execute(text(add_roles_query))
                    conn.commit()
                    print("✅ Successfully added 'hod' and 'principal' to user_roles enum")
                except Exception as e:
                    print(f"⚠️  Warning: Could not update enum (this might be expected): {e}")
            else:
                print("✅ user_roles enum already includes 'hod' and 'principal'")
                
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        sys.exit(1)
    
    print("🎉 Database migration completed successfully!")

if __name__ == "__main__":
    migrate_database()