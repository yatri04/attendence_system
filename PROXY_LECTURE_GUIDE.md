# 🎓 Proxy Lecture Guide

## Overview
The Proxy Lecture feature allows teachers to generate QR codes for substitute teachers or proxy lectures. This is perfect for situations where a teacher cannot be physically present but needs to take attendance for their class.

## ✨ Features

### 🔑 Key Capabilities
- **Generate QR codes for any class** - Teachers can create QR codes for classes they don't normally teach
- **Proxy teacher tracking** - Record the name of the substitute/proxy teacher
- **Flexible expiry times** - Choose from 30 seconds to 5 minutes
- **Secure time-limited codes** - QR codes automatically expire for security
- **Visual indicators** - Proxy lectures are clearly marked in the system
- **Full attendance tracking** - All attendance data is recorded normally

### 🎯 Use Cases
- **Substitute teachers** - When a regular teacher is absent
- **Guest lecturers** - For special sessions or guest speakers
- **Cross-department coverage** - When teachers cover other classes
- **Emergency situations** - Quick attendance setup when needed

## 🚀 How to Use

### Step 1: Access Proxy Lecture
1. **Login as a teacher**
2. **Go to Teacher Dashboard**
3. **Click "Proxy Lecture QR" button** in the Proxy Lecture Management section

### Step 2: Generate Proxy QR Code
1. **Select Class** - Choose the class for which you want to generate a QR code
2. **Enter Proxy Teacher Name** - Provide the name of the substitute/proxy teacher
3. **Set Expiry Time** - Choose how long the QR code should remain valid:
   - 30 seconds (quick sessions)
   - 1 minute (standard)
   - 2 minutes (extended)
   - 5 minutes (long sessions)
4. **Click "Generate Proxy QR Code"**

### Step 3: Share with Proxy Teacher
1. **Download/Save the QR code** that appears
2. **Send to the proxy teacher** via email, messaging, or in person
3. **Proxy teacher displays QR code** to students
4. **Students scan the QR code** to mark attendance

## 📊 System Behavior

### 🔍 Proxy Lecture Indicators
- **Class Page**: Shows "Proxy Lecture" badge with proxy teacher name
- **Session History**: Proxy lectures are clearly marked
- **Reports**: Include proxy teacher information
- **Analytics**: Track proxy lecture usage

### 🛡️ Security Features
- **Time-limited QR codes** - Automatically expire
- **Unique session IDs** - Each QR code is unique
- **Teacher accountability** - Proxy teacher name is recorded
- **Audit trail** - Full tracking of who generated what

### 📈 Data Tracking
- **Attendance records** are stored normally
- **Proxy teacher name** is recorded in session
- **Session metadata** includes proxy status
- **Analytics** can distinguish proxy vs regular lectures

## 🎨 User Interface

### Teacher Dashboard
- **New "Proxy Lecture Management" section**
- **Easy access button** to proxy lecture interface
- **Clear instructions** and guidance

### Proxy Lecture Interface
- **Class selection dropdown** - All available classes
- **Proxy teacher name field** - Required for accountability
- **Expiry time selection** - Flexible timing options
- **Helpful instructions** - Step-by-step guidance
- **Security notes** - Important reminders

### Class Page Updates
- **Proxy lecture badges** - Clear visual indicators
- **Proxy teacher names** - Displayed when applicable
- **Session information** - Enhanced with proxy details

## 🔧 Technical Details

### Database Changes
- **`is_proxy` column** - Boolean flag for proxy lectures
- **`proxy_teacher_name` column** - Stores proxy teacher name
- **Index on `is_proxy`** - Optimized queries for proxy sessions

### Session Model Updates
```python
is_proxy = db.Column(db.Boolean, default=False)
proxy_teacher_name = db.Column(db.String(100), nullable=True)
```

### New Routes
- **`/teacher/proxy_lecture`** - GET/POST for proxy lecture interface
- **Enhanced session creation** - Supports proxy lecture parameters

## 📋 Best Practices

### ✅ Do's
- **Always enter proxy teacher name** for accountability
- **Choose appropriate expiry time** based on session length
- **Share QR codes securely** with trusted proxy teachers
- **Verify proxy teacher identity** before sharing
- **Use shorter expiry times** for security

### ❌ Don'ts
- **Don't share QR codes publicly** or on social media
- **Don't use very long expiry times** unnecessarily
- **Don't forget to record proxy teacher name**
- **Don't generate QR codes for unauthorized classes**

## 🔍 Troubleshooting

### Common Issues
1. **"Class not found" error**
   - Ensure the class exists and is active
   - Check if you have proper permissions

2. **"Proxy teacher name required" error**
   - Always enter the proxy teacher's name
   - Use full name for better tracking

3. **QR code not working**
   - Check if the code has expired
   - Verify the session is still active
   - Ensure students are scanning correctly

### Support
- **Check session expiry** - QR codes are time-limited
- **Verify class access** - Ensure proper permissions
- **Contact admin** for persistent issues

## 🎯 Benefits

### For Teachers
- **Flexibility** - Generate QR codes for any class
- **Accountability** - Track who is taking attendance
- **Convenience** - Easy proxy lecture setup
- **Security** - Time-limited codes

### For Students
- **Consistent experience** - Same QR scanning process
- **Reliable attendance** - Works with any teacher
- **Clear indicators** - Know when it's a proxy lecture

### For Administrators
- **Full tracking** - Complete audit trail
- **Proxy teacher records** - Know who took attendance
- **Security** - Time-limited access
- **Analytics** - Track proxy lecture usage

## 🚀 Getting Started

1. **Run the migration** (if not already done):
   ```bash
   python migrate_proxy_lecture.py
   ```

2. **Login as a teacher**

3. **Navigate to Teacher Dashboard**

4. **Click "Proxy Lecture QR"**

5. **Follow the interface instructions**

6. **Generate your first proxy QR code!**

---

**🎉 You're all set! The proxy lecture functionality is now ready to use.**
