#!/usr/bin/env python3
"""
Enhanced CSV validation script to check for common formatting issues.
"""

import csv
import io
import re

def validate_csv_file(filename):
    """Validate CSV file for common issues."""
    print(f"🔍 Validating CSV file: {filename}")
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for common issues
        issues = []
        
        # Check for tab characters (common copy-paste issue)
        if '\t' in content:
            issues.append("❌ Contains tab characters - use commas instead")
            print("⚠️  Found tab characters in CSV. This will cause parsing errors.")
            print("   Replace tabs with commas in your CSV file.")
        
        # Check for mixed line endings
        if '\r\n' in content and '\n' in content:
            issues.append("⚠️  Mixed line endings detected")
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(content))
        
        print(f"📋 Columns found: {csv_reader.fieldnames}")
        
        # Check required columns
        required_columns = ['name', 'email', 'roll_number', 'class_name']
        missing_columns = [col for col in required_columns if col not in csv_reader.fieldnames]
        
        if missing_columns:
            issues.append(f"❌ Missing required columns: {missing_columns}")
        else:
            print("✅ All required columns present")
        
        # Check data rows
        rows = list(csv_reader)
        print(f"📊 Found {len(rows)} data rows")
        
        # Validate each row
        for i, row in enumerate(rows, 1):
            row_issues = []
            
            # Check for empty required fields
            for field in required_columns:
                if not row.get(field, '').strip():
                    row_issues.append(f"Empty {field}")
            
            # Check email format
            email = row.get('email', '').strip()
            if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                row_issues.append("Invalid email format")
            
            # Check for extra spaces or special characters
            for field, value in row.items():
                if value and value != value.strip():
                    row_issues.append(f"Extra spaces in {field}")
            
            if row_issues:
                issues.append(f"Row {i}: {', '.join(row_issues)}")
                print(f"⚠️  Row {i} issues: {', '.join(row_issues)}")
            else:
                print(f"✅ Row {i}: {row['name']} - {row['email']} - {row['roll_number']} - {row['class_name']}")
        
        if issues:
            print(f"\n❌ Found {len(issues)} issues:")
            for issue in issues:
                print(f"  {issue}")
            return False
        else:
            print("\n✅ CSV file is valid and ready for import!")
            return True
            
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Enhanced CSV Validation")
    print("=" * 50)
    
    if validate_csv_file('test_students.csv'):
        print("\n🎉 Your CSV file is ready for bulk import!")
        print("\n📝 Next steps:")
        print("1. Go to Admin Setup page")
        print("2. Upload your CSV file")
        print("3. Check for success/error messages")
    else:
        print("\n❌ Please fix the issues above before importing.")
