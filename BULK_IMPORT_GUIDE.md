# Bulk Student Import Guide

## Overview
The bulk student import feature allows administrators to import multiple students at once using a CSV file.

## How to Use Bulk Import

### Step 1: Access Admin Setup
1. Log in as an admin user
2. Navigate to the Admin Setup page (`/admin/setup`)
3. Scroll down to the "Bulk Import Students" section

### Step 2: Prepare Your CSV File
Your CSV file must have these columns:
- `name` - Student's full name
- `email` - Student's email address
- `roll_number` - Student's roll number
- `class_name` - Name of the class (must exist in the system)
- `password` - (Optional) Student's password

### Step 3: CSV Format Example
```csv
name,email,roll_number,class_name,password
John Doe,john.doe@example.com,2021001,5CSE1,student123
Jane Smith,jane.smith@example.com,2021002,5CSE1,
Bob Johnson,bob.johnson@example.com,2021003,5CSE2,custompass456
```

### Step 4: Upload Process
1. Click "Choose File" and select your CSV file
2. (Optional) Enter a default password for students without passwords
3. Click "Import Students"

## Password Handling
- **With password in CSV**: Uses the password from the CSV file
- **Empty password in CSV**: Uses the default password you specify
- **No default password**: Generates a random 8-character password
- **No password column**: Uses default password or generates random

## Requirements
- Classes must exist before importing students
- Email addresses must be unique
- Roll numbers must be unique within the same class
- CSV file must be in UTF-8 encoding

## Troubleshooting

### Common Issues
1. **"Missing required columns"**: Ensure your CSV has all required columns
2. **"Class not found"**: Create the class first using the Admin Setup page
3. **"Email already exists"**: Student with that email already exists
4. **"Roll number already exists"**: Another student in the same class has that roll number

### Success Messages
- ✅ "Successfully imported X students!" - Import completed
- ⚠️ "Failed to import X students" - Some students couldn't be imported (check for duplicates)

## Sample CSV File
A sample CSV file is available for download on the Admin Setup page to help you understand the correct format.

## Best Practices
1. Always test with a small CSV file first
2. Ensure all class names exist in the system
3. Use unique email addresses and roll numbers
4. Keep a backup of your CSV file
5. Check the success/failure messages after import