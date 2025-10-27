# Admin Setup Guide - WiFi-based Attendance Management System

This guide will help you set up and manage the complete attendance system as an administrator.

## 🚀 Quick Start

### 1. Database Setup
```bash
# Option 1: Fresh start (recommended)
python reset_database.py
python setup_database.py

# Option 2: Migrate existing database
python migrate_database.py
python setup_database.py
```

### 2. Run the Application
```bash
python app.py
```

### 3. Admin Login
- **URL**: http://localhost:5000
- **Email**: admin@attendance.com
- **Password**: admin123

## 📋 Complete Admin Workflow

### Step 1: Login
1. Go to http://localhost:5000
2. Login with admin credentials
3. You'll see the admin dashboard with system statistics

### Step 2: Set Up System Structure

#### 2.1 Create Departments
1. Click "Manage Departments" on dashboard
2. Create departments:
   - **CSE** - Computer Science Engineering
   - **CE** - Civil Engineering  
   - **IT** - Information Technology

#### 2.2 Create Branches
1. Click "Manage Branches" on dashboard
2. Create branches within each department:
   - **CSE1, CSE2** (under CSE)
   - **CE1, CE2** (under CE)
   - **IT1, IT2** (under IT)

#### 2.3 Create Classes
1. Click "Manage Classes" on dashboard
2. Create classes with structure: **Semester + Division + Branch**
   - Examples: 1CSE1, 1CSE2, 2CSE1, 2CSE2, etc.
   - For all semesters 1-8

### Step 3: Manage Teachers

#### 3.1 Create Teacher Accounts
1. Click "Manage Teachers" on dashboard
2. Create teacher accounts:
   - Name, Email, Password
   - Default password: teacher123

#### 3.2 Assign Teachers to Classes
1. In "Manage Teachers" section
2. Select teacher and class
3. Click "Assign" to link them

### Step 4: Manage Students

#### 4.1 Create Student Accounts
1. Click "Manage Students" on dashboard
2. Create student accounts:
   - Name, Email, Roll Number, Class
   - Default password: student123

#### 4.2 Student Promotion (End of Semester)
1. In "Manage Students" section
2. Select current semester
3. Click "Promote" to move students to next semester
4. Semester 8 students become Alumni

## 🎯 System Features

### Admin Capabilities
- ✅ **Dashboard**: View system statistics and recent activity
- ✅ **Department Management**: Create/Edit/Delete departments
- ✅ **Branch Management**: Create/Edit/Delete branches within departments
- ✅ **Class Management**: Create classes with Semester + Division + Branch structure
- ✅ **Teacher Management**: Create teacher accounts and assign to classes
- ✅ **Student Management**: Create student accounts and handle promotions
- ✅ **Reports**: View attendance reports (coming soon)

### Teacher Capabilities
- ✅ **Class Dashboard**: View assigned classes with detailed info
- ✅ **QR Generation**: Generate QR codes with 30s or 1min expiry
- ✅ **Attendance Review**: 1-hour window to manually adjust attendance
- ✅ **Session Management**: Lock sessions after review period
- ✅ **PDF Reports**: Download attendance reports

### Student Capabilities
- ✅ **Class Information**: View class details (Name, Semester, Division, Branch, Total Students)
- ✅ **Attendance Statistics**: View attendance percentage and history
- ✅ **QR Scanning**: Scan teacher-generated QR codes
- ✅ **Attendance Confirmation**: Get confirmation messages

## 🔧 System Rules

### QR Code System
- **Expiry**: 30 seconds or 1 minute (teacher chooses)
- **No WiFi Validation**: Pure QR-based attendance
- **Session Lock**: Automatic after 1 hour

### Student Promotion
- **Semester 1-7**: Move to next semester class
- **Semester 8**: Mark as Alumni
- **Automatic**: Based on semester + branch + division

### Account Creation
- **Admin Only**: No self-signup allowed
- **Default Passwords**: 
  - Teachers: teacher123
  - Students: student123
- **Admin**: admin123

## 📊 Class Structure Examples

### CSE Department
- **Branches**: CSE1, CSE2
- **Classes**: 1CSE1, 1CSE2, 2CSE1, 2CSE2, ..., 8CSE1, 8CSE2

### CE Department  
- **Branches**: CE1, CE2
- **Classes**: 1CE1, 1CE2, 2CE1, 2CE2, ..., 8CE1, 8CE2

### IT Department
- **Branches**: IT1, IT2
- **Classes**: 1IT1, 1IT2, 2IT1, 2IT2, ..., 8IT1, 8IT2

## 🚨 Important Notes

1. **No Self-Signup**: Only admin creates accounts
2. **Class Assignment**: Students must be assigned to classes
3. **Teacher Assignment**: Teachers must be assigned to classes
4. **Promotion Logic**: Students move automatically based on semester
5. **Session Management**: Teachers have 1-hour review window
6. **QR Expiry**: Configurable 30s or 1min

## 🔍 Troubleshooting

### Common Issues
1. **Database Errors**: Run reset_database.py and setup_database.py
2. **Missing Classes**: Create departments → branches → classes in order
3. **No Students**: Create classes first, then add students
4. **No Teachers**: Create teacher accounts and assign to classes

### Testing the System
```bash
# Test all components
python test_system.py

# Check database
python -c "from app import create_app; from models import *; app = create_app(); app.app_context().push(); print('Departments:', Department.query.count()); print('Branches:', Branch.query.count()); print('Classes:', ClassModel.query.count()); print('Teachers:', User.query.filter_by(role='teacher').count()); print('Students:', User.query.filter_by(role='student').count())"
```

## 📞 Support

If you encounter any issues:
1. Check the error logs in the terminal
2. Verify database connection
3. Ensure all dependencies are installed
4. Run the test script to verify setup

---

**The system is now ready for use!** Follow this guide to set up your complete attendance management system.
