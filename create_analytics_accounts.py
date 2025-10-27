#!/usr/bin/env python3
"""
Script to help admins create HOD and Principal accounts for analytics.
This script provides a command-line interface for creating these accounts.
"""

import os
import sys
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash

def get_database_url():
    """Get database URL from environment or use default."""
    default_db = "postgresql://postgres:yatri04112005y@localhost:5432/attendance_db"
    return os.environ.get("DATABASE_URL", default_db)

def create_user_account(name, email, role, password, department_id=None):
    """Create a user account in the database."""
    database_url = get_database_url()
    
    # Normalize PostgreSQL URL
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if user already exists
            check_query = "SELECT id FROM users WHERE email = %s"
            result = conn.execute(text(check_query), (email,))
            existing_user = result.fetchone()
            
            if existing_user:
                print(f"❌ User with email {email} already exists!")
                return False
            
            # Check if department exists (for HOD)
            if role == "hod" and department_id:
                dept_query = "SELECT id FROM departments WHERE id = %s"
                result = conn.execute(text(dept_query), (department_id,))
                if not result.fetchone():
                    print(f"❌ Department with ID {department_id} not found!")
                    return False
            
            # Generate password hash
            password_hash = generate_password_hash(password)
            
            # Create user
            insert_query = """
            INSERT INTO users (name, email, password_hash, role, department_id, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            
            conn.execute(text(insert_query), (
                name, email, password_hash, role, department_id, True
            ))
            conn.commit()
            
            print(f"✅ Successfully created {role.upper()} account:")
            print(f"   Name: {name}")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
            if department_id:
                print(f"   Department ID: {department_id}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating account: {e}")
        return False

def list_departments():
    """List available departments."""
    database_url = get_database_url()
    
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            query = "SELECT id, name, code FROM departments ORDER BY name"
            result = conn.execute(text(query))
            departments = result.fetchall()
            
            if departments:
                print("📋 Available Departments:")
                for dept_id, name, code in departments:
                    print(f"   ID: {dept_id} - {name} ({code})")
                return departments
            else:
                print("❌ No departments found. Create departments first.")
                return []
                
    except Exception as e:
        print(f"❌ Error listing departments: {e}")
        return []

def main():
    """Main function to create analytics accounts."""
    print("🔧 Analytics Account Creation Tool")
    print("=" * 50)
    
    # List departments
    departments = list_departments()
    
    if not departments:
        print("\n❌ No departments available. Please create departments first.")
        return
    
    print("\n📝 Creating HOD Account")
    print("-" * 30)
    
    # Get HOD details
    hod_name = input("HOD Name: ").strip()
    hod_email = input("HOD Email: ").strip()
    hod_password = input("HOD Password: ").strip()
    
    if not hod_name or not hod_email or not hod_password:
        print("❌ All fields are required!")
        return
    
    # Select department
    print("\nSelect Department for HOD:")
    for dept_id, name, code in departments:
        print(f"   {dept_id}: {name} ({code})")
    
    try:
        dept_id = int(input("Department ID: "))
        if not any(d[0] == dept_id for d in departments):
            print("❌ Invalid department ID!")
            return
    except ValueError:
        print("❌ Please enter a valid department ID!")
        return
    
    # Create HOD account
    if create_user_account(hod_name, hod_email, "hod", hod_password, dept_id):
        print("\n✅ HOD account created successfully!")
    
    print("\n📝 Creating Principal Account")
    print("-" * 30)
    
    # Get Principal details
    principal_name = input("Principal Name: ").strip()
    principal_email = input("Principal Email: ").strip()
    principal_password = input("Principal Password: ").strip()
    
    if not principal_name or not principal_email or not principal_password:
        print("❌ All fields are required!")
        return
    
    # Create Principal account
    if create_user_account(principal_name, principal_email, "principal", principal_password):
        print("\n✅ Principal account created successfully!")
    
    print("\n🎉 Analytics accounts setup complete!")
    print("\n📋 Account Summary:")
    print(f"   HOD: {hod_name} ({hod_email}) - Department ID: {dept_id}")
    print(f"   Principal: {principal_name} ({principal_email})")
    print("\n🌐 Dashboard URLs:")
    print("   HOD Dashboard: /hod")
    print("   Principal Dashboard: /principal")

if __name__ == "__main__":
    main()
