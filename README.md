# WiFi-based Attendance Management System

A comprehensive attendance management system built with Flask that supports QR code-based attendance marking, role-based access control, and automated session management.

## 🚀 Features

### 1️⃣ Admin Side (Database Manager)
- **Comprehensive Dashboard**: View system statistics, recent activity, and quick actions
- **Department Management**: Create and manage academic departments (CSE, CE, IT)
- **Branch Management**: Organize branches within departments (CSE1, CSE2, etc.)
- **Semester Management**: Manage academic semesters (1-8)
- **Class Management**: Create classes with semester + division + branch structure
- **Advanced Student Management**: Bulk upload, class-based viewing, and comprehensive student operations
- **Bulk Student Upload**: CSV-based bulk import with advanced validation and error handling
- **Class-Based Organization**: View and manage students organized by classes
- **Bulk Operations**: Move, delete, and manage multiple students at once
- **Teacher Management**: Manage teacher accounts and class assignments
- **Reports & Analytics**: View and export attendance reports

### 2️⃣ Teacher Side (Attendance Manager)
- **Class Dashboard**: View assigned classes with student counts
- **QR Code Generation**: Generate QR codes with configurable expiry (30s or 1min)
- **WiFi Network Management**: Configure campus WiFi networks for attendance verification
- **WiFi Connection Testing**: Test current connection against configured networks
- **Attendance Review**: 1-hour window to manually adjust attendance
- **Session Management**: Lock sessions after review period
- **PDF Reports**: Download attendance reports for classes
- **Real-time Monitoring**: Track attendance as students scan QR codes

### 3️⃣ Student Side (Attendance Taker)
- **QR Scanner**: Scan teacher-generated QR codes to mark attendance
- **WiFi Connection Status**: Real-time display of WiFi connection status
- **Campus WiFi Verification**: Must be connected to configured WiFi networks
- **Attendance Statistics**: View attendance percentage and history
- **Student Information**: Display personal details and class information
- **Recent History**: View recent attendance sessions

## 📶 WiFi-Based Attendance Verification

### Overview
The system now includes comprehensive WiFi-based attendance verification to ensure students are physically present on campus when marking attendance. This prevents remote attendance marking and enhances the integrity of the attendance system.

### Key Features

#### For Teachers:
- **WiFi Network Configuration**: Add and manage campus WiFi networks by router IP
- **Subnet Management**: Configure specific subnet masks for precise network control
- **Network Testing**: Test current connection against configured networks
- **Multiple Networks**: Support for multiple WiFi networks (different buildings/areas)
- **Network Status**: Activate/deactivate networks as needed

#### For Students:
- **Real-time Status**: Live display of WiFi connection status
- **Automatic Verification**: System automatically checks WiFi connection during attendance
- **Clear Feedback**: Visual indicators showing connection status
- **Periodic Checks**: WiFi status updates every 30 seconds

### Technical Implementation

#### WiFi Network Model
```python
class WiFiNetwork(db.Model):
    name = db.Column(db.String(100), nullable=False)  # Network name
    router_ip = db.Column(db.String(45), nullable=False)  # Router IP
    subnet_mask = db.Column(db.String(45), nullable=True)  # Subnet mask
    is_active = db.Column(db.Boolean, default=True)  # Active status
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))  # Creator
```

#### Verification Process
1. **IP Detection**: System detects student's current IP address
2. **Network Matching**: Checks if IP is within configured WiFi networks
3. **Subnet Validation**: Validates against specific subnet masks
4. **Fallback Check**: Falls back to general private network check if no WiFi configured
5. **Attendance Recording**: Records attendance with WiFi network information

#### Configuration Examples
- **Campus WiFi**: Router IP `192.168.1.1` with `/24` subnet
- **Lab Network**: Router IP `192.168.2.1` with `/24` subnet  
- **Library WiFi**: Router IP `10.0.1.1` with `/24` subnet

### Usage Instructions

#### Setting Up WiFi Networks (Teachers)
1. Login as a teacher
2. Go to "WiFi Network Management" from dashboard
3. Click "Add WiFi Network"
4. Enter network name and router IP
5. Optionally specify subnet mask (defaults to /24)
6. Save and activate the network

#### Testing WiFi Connection
1. Use "Test Connection" button on teacher dashboard
2. System will show current IP and matched network
3. Verify connection before generating QR codes

#### Student Experience
1. Connect to campus WiFi
2. Login to student dashboard
3. Check WiFi status indicator (green = connected, red = not connected)
4. Scan QR code to mark attendance
5. System verifies WiFi connection automatically

## 📊 Bulk Student Management System

### Overview
The system includes a comprehensive bulk student management system that allows administrators to efficiently manage large numbers of students with class-based organization and advanced bulk operations.

### Key Features

#### Bulk Upload System
- **CSV Import**: Upload students via CSV files with comprehensive validation
- **Advanced Error Handling**: Detailed error reporting with row-specific feedback
- **Password Management**: Auto-generate passwords or use custom/default passwords
- **Duplicate Prevention**: Automatic detection and prevention of duplicate emails/roll numbers
- **Class Validation**: Ensures all students are assigned to existing classes

#### Class-Based Organization
- **Class Overview Cards**: Visual representation of student distribution across classes
- **Class-Specific Views**: Dedicated pages for each class with detailed student lists
- **Statistics Dashboard**: Real-time statistics showing active/inactive students per class
- **Search and Filter**: Advanced filtering by class, status, and search terms

#### Bulk Operations
- **Bulk Selection**: Select multiple students with checkboxes or "Select All" functionality
- **Bulk Delete**: Remove multiple students at once with confirmation
- **Bulk Move**: Transfer students between classes in bulk
- **Status Management**: Activate/deactivate students individually or in bulk

### Technical Implementation

#### CSV Format Requirements
```csv
name,email,roll_number,class_name,password
John Doe,john.doe@example.com,2021001,5CSE1,student123
Jane Smith,jane.smith@example.com,2021002,5CSE1,
Bob Johnson,bob.johnson@example.com,2021003,5CSE2,custompass456
```

#### Validation Features
- **Email Format Validation**: Ensures proper email format
- **Duplicate Detection**: Prevents duplicate emails and roll numbers within classes
- **Class Existence Check**: Validates that all referenced classes exist
- **Required Field Validation**: Ensures all mandatory fields are provided
- **Row-by-Row Error Reporting**: Shows specific errors for each failed row

#### Database Enhancements
- **Active Status Tracking**: Added `is_active` field for student status management
- **Creation Timestamps**: Track when students were added to the system
- **Class Relationships**: Maintain proper foreign key relationships with classes

### Usage Instructions

#### Bulk Upload Process
1. **Prepare CSV File**: Create CSV with required columns (name, email, roll_number, class_name, password)
2. **Access Upload Interface**: Go to Admin Dashboard → Manage Students → Bulk Upload
3. **Upload File**: Select CSV file and optionally set default password
4. **Review Results**: Check import results and error messages
5. **Verify Data**: Review imported students in class-based views

#### Class Management
1. **View Class Overview**: See student distribution across all classes
2. **Access Class Details**: Click on class cards to view detailed student lists
3. **Search and Filter**: Use search and filter options to find specific students
4. **Bulk Operations**: Select and perform bulk operations on multiple students

#### Student Operations
1. **Individual Actions**: Edit, delete, or change status of individual students
2. **Bulk Selection**: Use checkboxes to select multiple students
3. **Bulk Operations**: Move students between classes or delete multiple students
4. **Export Data**: Export student data to CSV for external use

### Error Handling and Validation

#### Upload Validation
- **File Format**: Ensures CSV file format is correct
- **Column Validation**: Verifies all required columns are present
- **Data Validation**: Validates email format, required fields, and data integrity
- **Duplicate Prevention**: Prevents duplicate emails and roll numbers
- **Class Validation**: Ensures all referenced classes exist in the system

#### Error Reporting
- **Row-Specific Errors**: Shows exact row number and error description
- **Summary Statistics**: Displays total imported vs failed records
- **Detailed Feedback**: Provides specific error messages for each validation failure
- **User-Friendly Messages**: Clear, actionable error messages for administrators

### Performance Features

#### Pagination
- **Efficient Loading**: Paginated student lists for better performance
- **Configurable Page Size**: Adjustable number of students per page
- **Navigation Controls**: Easy navigation between pages

#### Search and Filter
- **Real-time Search**: Instant search across name, email, and roll number
- **Class Filtering**: Filter students by specific classes
- **Status Filtering**: Filter by active/inactive status
- **Combined Filters**: Use multiple filters simultaneously

## 🏗️ System Architecture

### Database Models
- **User**: Admin, Teacher, and Student accounts with role-based access
- **Department**: Academic departments (CSE, CE, IT)
- **Branch**: Branches within departments
- **Semester**: Academic semesters (1-8)
- **ClassModel**: Classes with semester + division + branch structure
- **SessionModel**: QR code sessions with configurable expiry
- **Attendance**: Student attendance records
- **AttendanceOverride**: Manual attendance changes by teachers
- **TeacherClass**: Teacher-class assignments

### Key Features
- **QR Expiry**: Configurable 30-second or 1-minute expiry
- **Review Window**: 1-hour window for teachers to manually adjust attendance
- **Session Locking**: Automatic locking after review period
- **No WiFi Validation**: Pure QR-based attendance (as per requirements)
- **Promotion Logic**: Automatic student promotion between semesters
- **Status Tracking**: Active/Alumni student status management

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- PostgreSQL database
- pip package manager

### 1. Clone the Repository
```bash
git clone <repository-url>
cd wifi-based-attendance
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Setup
1. Create a PostgreSQL database:
```sql
CREATE DATABASE attendance_db;
```

2. Update database connection in `app.py`:
```python
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://username:password@localhost:5432/attendance_db"
```

3. Initialize the database with sample data:
```bash
python setup_database.py
```

### 4. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 📱 Usage Guide

### Admin Workflow
1. **Login** as admin using `admin@attendance.com` / `admin123`
2. **View Dashboard** to see system statistics
3. **Manage Structure**:
   - Create departments (CSE, CE, IT)
   - Create branches within departments
   - Set up semesters (1-8)
   - Create classes (e.g., 1CSE1, 5CSE2)
4. **Manage Users**:
   - Add teachers and assign to classes
   - Add students to specific classes
   - Handle student promotions

### Teacher Workflow
1. **Login** as teacher
2. **View Assigned Classes** on dashboard
3. **Generate QR Code**:
   - Select class
   - Choose expiry time (30s or 1min)
   - Display QR code to students
4. **Monitor Attendance** in real-time
5. **Review & Adjust**:
   - Within 1-hour window, manually mark students present/absent
   - Lock session when done
6. **Download Reports** as PDF

### Student Workflow
1. **Login** as student
2. **View Dashboard** with attendance statistics
3. **Scan QR Code** when teacher displays it
4. **Confirm Attendance** with success message
5. **View History** of recent attendance sessions

## 🔧 Configuration

### QR Code Settings
- **Expiry Time**: 30 seconds or 1 minute (teacher's choice)
- **Session Lock**: Automatic after 1 hour
- **Review Window**: 1 hour from session creation

### Database Configuration
Update the database URL in `app.py`:
```python
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://user:pass@host:port/dbname"
```

### Security Settings
- Change default passwords in production
- Update `SECRET_KEY` in environment variables
- Configure proper user permissions

## 📊 Sample Data

The setup script creates:
- **3 Departments**: CSE, CE, IT
- **6 Branches**: CSE1, CSE2, CE1, CE2, IT1, IT2
- **8 Semesters**: 1-8
- **20 Classes**: Various combinations (1CSE1, 5CSE2, etc.)
- **1 Admin**: admin@attendance.com / admin123
- **3 Teachers**: Various email addresses / teacher123
- **8 Students**: Sample students in different classes / student123

## 🚨 System Rules

1. **QR Expiry**: 30 seconds or 1 minute (teacher decides)
2. **No WiFi Validation**: Pure QR-based attendance
3. **Review Window**: 1 hour for manual adjustments
4. **Session Locking**: Automatic after 1 hour
5. **Student Promotion**: Automatic at semester end
6. **Alumni Status**: Students in semester 8 become alumni

## 🔍 API Endpoints

### Admin Routes
- `GET /admin` - Admin dashboard
- `GET /admin/setup` - System setup page
- `POST /admin/assign_teacher` - Assign teacher to class

### Teacher Routes
- `GET /teacher` - Teacher dashboard
- `GET /teacher/class/<id>` - Class management page
- `POST /teacher/class/<id>/generate_qr` - Generate QR code
- `GET /teacher/class/<id>/review` - Review attendance
- `POST /teacher/class/<id>/lock_session` - Lock session

### Student Routes
- `GET /student` - Student dashboard
- `POST /mark_attendance` - Mark attendance via QR scan

## 🛡️ Security Features

- **Role-based Access Control**: Admin, Teacher, Student roles
- **Session Management**: Secure session handling
- **Password Hashing**: Werkzeug security
- **Input Validation**: Form validation and sanitization
- **CSRF Protection**: Flask-WTF integration

## 📈 Future Enhancements

- [ ] Department and Branch CRUD operations
- [ ] Advanced reporting and analytics
- [ ] Email notifications
- [ ] Mobile app integration
- [ ] Bulk student import/export
- [ ] Attendance trends analysis
- [ ] Integration with LMS systems

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

---

**Note**: This system is designed for educational institutions and requires proper setup and configuration for production use.