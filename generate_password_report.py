#!/usr/bin/env python3
"""
Generate Password Report for Existing Students
This script generates a CSV report with student login credentials.
"""

import csv
import random
import string
import sys
from datetime import datetime
from app import create_app
from models import db, User, ClassModel
from werkzeug.security import generate_password_hash

def generate_password(length=8):
    """Generate a random password with letters and numbers"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def generate_password_report(output_file=None, default_password=None):
    """Generate a password report for all students"""
    app = create_app()
    
    with app.app_context():
        # Get all students
        students = User.query.filter_by(role='student').all()
        
        if not students:
            print("❌ No students found in the database.")
            return False
        
        print(f"📚 Found {len(students)} students")
        
        # Generate passwords and update database
        updated_students = []
        
        for student in students:
            # Generate new password if student doesn't have one or if we want to reset
            if not student.password_hash or default_password:
                password = default_password if default_password else generate_password()
                student.password_hash = generate_password_hash(password)
                
                updated_students.append({
                    'name': student.name,
                    'email': student.email,
                    'roll_number': student.roll_number or 'N/A',
                    'class_name': student.class_obj.name if student.class_obj else 'No Class',
                    'password': password
                })
                
                print(f"✅ {student.name} ({student.email}) - Password: {password}")
            else:
                print(f"⚠️ {student.name} ({student.email}) - Password already set")
        
        # Commit changes if any passwords were updated
        if updated_students:
            db.session.commit()
            print(f"\n✅ Updated passwords for {len(updated_students)} students")
        
        # Generate report file
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"student_passwords_{timestamp}.csv"
        
        with open(output_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Name', 'Email', 'Roll Number', 'Class', 'Password'])
            
            for student in updated_students:
                writer.writerow([
                    student['name'],
                    student['email'],
                    student['roll_number'],
                    student['class_name'],
                    student['password']
                ])
        
        print(f"\n📄 Password report saved to: {output_file}")
        print("⚠️ Keep this file secure - it contains student passwords!")
        
        return True

def main():
    """Main function"""
    print("🔑 Student Password Report Generator")
    print("=" * 40)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("Usage:")
            print("  python generate_password_report.py [output_file] [default_password]")
            print("\nExamples:")
            print("  python generate_password_report.py")
            print("  python generate_password_report.py passwords.csv")
            print("  python generate_password_report.py passwords.csv student123")
            return
        
        output_file = sys.argv[1]
        default_password = sys.argv[2] if len(sys.argv) > 2 else None
    else:
        output_file = None
        default_password = None
    
    if default_password:
        print(f"🔑 Using default password: {default_password}")
    else:
        print("🔑 Generating random passwords for each student")
    
    success = generate_password_report(output_file, default_password)
    
    if success:
        print("\n✅ Password report generated successfully!")
        print("\n📋 Next steps:")
        print("1. Share the password file securely with students")
        print("2. Students can log in with their email and password")
        print("3. Consider having students change their passwords after first login")
    else:
        print("\n❌ Failed to generate password report.")

if __name__ == "__main__":
    main()
