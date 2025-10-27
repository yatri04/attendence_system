# Admin Analytics Guide - Creating HOD and Principal Accounts

## Overview
Administrators can create HOD (Head of Department) and Principal accounts to provide them with access to analytics dashboards for monitoring attendance and institutional performance.

## Creating HOD and Principal Accounts

### Step 1: Access User Management
1. Log in as an admin user
2. Navigate to **Admin Dashboard** → **Manage Teachers** (or go to `/admin/teachers`)
3. Scroll to the "Create New User" section

### Step 2: Create HOD Account
1. **Fill in the form:**
   - **Name**: HOD's full name (e.g., "Dr. John Smith")
   - **Email**: HOD's email address
   - **Role**: Select "HOD" from dropdown
   - **Department**: Select the department this HOD will manage
   - **Password**: Set a secure password

2. **Click "Create User"**

3. **HOD will have access to:**
   - Department-specific analytics dashboard
   - Attendance statistics for their department
   - Class-wise attendance breakdown
   - Recent activity from department classes
   - Department performance metrics

### Step 3: Create Principal Account
1. **Fill in the form:**
   - **Name**: Principal's full name (e.g., "Dr. Jane Wilson")
   - **Email**: Principal's email address
   - **Role**: Select "Principal" from dropdown
   - **Department**: Leave empty (Principal has institution-wide access)
   - **Password**: Set a secure password

2. **Click "Create User"**

3. **Principal will have access to:**
   - Institution-wide analytics dashboard
   - All departments' statistics
   - Overall attendance trends
   - Department-wise performance comparison
   - Institution-wide attendance metrics

## Analytics Features by Role

### HOD Dashboard Features
- **Department Statistics**: Branches, classes, teachers, students in their department
- **Student Status**: Active vs Alumni breakdown
- **Class-wise Attendance**: Performance by class within department
- **Recent Sessions**: Last 10 attendance sessions from department classes
- **Average Attendance**: Overall department attendance rate

### Principal Dashboard Features
- **Institution Overview**: All departments, branches, classes, teachers, students
- **Department Comparison**: Side-by-side statistics for all departments
- **Overall Trends**: Institution-wide attendance patterns
- **Recent Activity**: Last 20 attendance sessions across all departments
- **Performance Metrics**: Institution-wide attendance rates

## Account Management

### Viewing Created Accounts
- Go to **Manage Teachers** page
- The table shows all users including HODs and Principals
- Filter by role to see specific account types

### Editing Accounts
- Click on any user in the management table
- Update name, email, or password
- For HODs: Change department assignment
- For Principals: Department field is not applicable

### Security Considerations
- **Strong Passwords**: Use complex passwords for HOD and Principal accounts
- **Email Verification**: Ensure email addresses are valid and accessible
- **Department Assignment**: Only assign HODs to departments they should manage
- **Regular Audits**: Periodically review account access and permissions

## Dashboard Access URLs

### HOD Dashboard
- **URL**: `/hod`
- **Access**: HOD role only
- **Features**: Department-specific analytics

### Principal Dashboard
- **URL**: `/principal`
- **Access**: Principal role only
- **Features**: Institution-wide analytics

## Best Practices

### For HOD Accounts
1. **One HOD per Department**: Assign only one HOD per department
2. **Department Alignment**: Ensure HOD is assigned to the correct department
3. **Regular Access**: HODs should have consistent access to monitor their department

### For Principal Accounts
1. **Limited Principals**: Typically only one Principal account needed
2. **Institution-wide Access**: Principal can see all departments
3. **Strategic Overview**: Principal dashboard for high-level decision making

## Troubleshooting

### Common Issues
1. **"No department assigned to HOD"**: Ensure HOD is assigned to a department
2. **Access Denied**: Check if user has correct role permissions
3. **Missing Data**: Ensure classes and students exist before viewing analytics

### Support
- Check user roles in the database
- Verify department assignments for HODs
- Ensure proper authentication and authorization

## Example Workflow

### Setting Up Analytics for a New Institution
1. **Create Departments**: Set up academic departments
2. **Create HOD Accounts**: One HOD per department
3. **Create Principal Account**: One Principal for institution overview
4. **Assign Classes**: Ensure classes are properly assigned to departments
5. **Add Students**: Import students into appropriate classes
6. **Test Access**: Verify HOD and Principal can access their dashboards

This setup provides comprehensive analytics access for institutional leadership to monitor attendance and academic performance.
