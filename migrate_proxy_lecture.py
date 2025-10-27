#!/usr/bin/env python3
"""
Database migration script to add proxy lecture support to SessionModel.
This script adds is_proxy and proxy_teacher_name columns to the sessions table.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def get_db_connection():
    """Get database connection using environment variables or defaults."""
    # Try to get from environment variables first
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'attendance_db')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', 'yatri04112005y')
    
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except psycopg2.Error as e:
        print(f"❌ Database connection failed: {e}")
        return None

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s AND column_name = %s
    """, (table_name, column_name))
    return cursor.fetchone() is not None

def migrate_proxy_lecture():
    """Add proxy lecture columns to sessions table."""
    print("🔄 Starting proxy lecture migration...")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Could not connect to database. Please check your connection settings.")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if sessions table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'sessions'
            )
        """)
        if not cursor.fetchone()[0]:
            print("❌ Sessions table does not exist. Please run the main migration first.")
            return False
        
        # Check if columns already exist
        is_proxy_exists = check_column_exists(cursor, 'sessions', 'is_proxy')
        proxy_teacher_name_exists = check_column_exists(cursor, 'sessions', 'proxy_teacher_name')
        
        if is_proxy_exists and proxy_teacher_name_exists:
            print("✅ Proxy lecture columns already exist. Migration not needed.")
            return True
        
        print("📝 Adding proxy lecture columns to sessions table...")
        
        # Add is_proxy column if it doesn't exist
        if not is_proxy_exists:
            print("  ➕ Adding is_proxy column...")
            cursor.execute("""
                ALTER TABLE sessions 
                ADD COLUMN is_proxy BOOLEAN DEFAULT FALSE
            """)
            print("  ✅ is_proxy column added successfully")
        else:
            print("  ⏭️  is_proxy column already exists")
        
        # Add proxy_teacher_name column if it doesn't exist
        if not proxy_teacher_name_exists:
            print("  ➕ Adding proxy_teacher_name column...")
            cursor.execute("""
                ALTER TABLE sessions 
                ADD COLUMN proxy_teacher_name VARCHAR(100)
            """)
            print("  ✅ proxy_teacher_name column added successfully")
        else:
            print("  ⏭️  proxy_teacher_name column already exists")
        
        # Add index on is_proxy for better query performance
        try:
            print("  ➕ Adding index on is_proxy column...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_is_proxy 
                ON sessions (is_proxy)
            """)
            print("  ✅ Index on is_proxy added successfully")
        except psycopg2.Error as e:
            print(f"  ⚠️  Index creation failed (may already exist): {e}")
        
        print("✅ Proxy lecture migration completed successfully!")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Migration failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verify_migration():
    """Verify that the migration was successful."""
    print("\n🔍 Verifying migration...")
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if columns exist
        is_proxy_exists = check_column_exists(cursor, 'sessions', 'is_proxy')
        proxy_teacher_name_exists = check_column_exists(cursor, 'sessions', 'proxy_teacher_name')
        
        if is_proxy_exists and proxy_teacher_name_exists:
            print("✅ Migration verification successful!")
            print("  ✅ is_proxy column exists")
            print("  ✅ proxy_teacher_name column exists")
            
            # Check if index exists
            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'sessions' AND indexname = 'idx_sessions_is_proxy'
            """)
            if cursor.fetchone():
                print("  ✅ Index on is_proxy exists")
            else:
                print("  ⚠️  Index on is_proxy not found")
            
            return True
        else:
            print("❌ Migration verification failed!")
            if not is_proxy_exists:
                print("  ❌ is_proxy column missing")
            if not proxy_teacher_name_exists:
                print("  ❌ proxy_teacher_name column missing")
            return False
            
    except psycopg2.Error as e:
        print(f"❌ Verification failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Proxy Lecture Database Migration")
    print("=" * 50)
    
    # Run migration
    success = migrate_proxy_lecture()
    
    if success:
        # Verify migration
        verify_migration()
        print("\n🎉 Proxy lecture migration completed successfully!")
        print("\n📋 What was added:")
        print("  • is_proxy (BOOLEAN) - Marks sessions as proxy lectures")
        print("  • proxy_teacher_name (VARCHAR) - Name of the proxy teacher")
        print("  • Index on is_proxy for better query performance")
        print("\n✨ You can now use proxy lecture functionality!")
    else:
        print("\n❌ Migration failed. Please check the error messages above.")
        sys.exit(1)
