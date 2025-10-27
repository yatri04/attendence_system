from datetime import datetime, timedelta, timezone
import os
import uuid
import ipaddress
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode

from models import (
    db, User, Attendance, SessionModel, ClassModel, TeacherClass, WiFiNetwork,
    Department, Branch, Semester, AttendanceOverride, PasswordLog
)


def _normalize_database_url(database_url: str) -> str:
    """Ensure SQLAlchemy-compatible PostgreSQL URL prefix.

    Heroku and some envs use the deprecated 'postgres://' scheme. SQLAlchemy expects
    'postgresql://'. This helper normalizes that.
    """
    if database_url and database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


def create_app() -> Flask:
    """Application factory to create and configure the Flask app."""
    app = Flask(__name__)

    # Basic configuration. In production, override with environment variables.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    default_db = "postgresql://postgres:yatri04112005y@localhost:5432/attendance_db"

    app.config["SQLALCHEMY_DATABASE_URI"] = _normalize_database_url(
        os.environ.get("DATABASE_URL", default_db)
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize database and login manager
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        # Flask-Login user loader
        return User.query.get(int(user_id))

    # Create database tables on first run (dev-friendly). For production, use migrations.
    with app.app_context():
        db.create_all()

    # --------------------------
    # Utility helpers
    # --------------------------
    # Allow configuring campus Wi‑Fi networks using CIDR ranges. Defaults include
    # common private networks (192.168.0.0/16, 172.16.0.0/12, 10.0.0.0/8).
    allowed_cidrs_env = os.environ.get(
        "WIFI_ALLOWED_CIDRS", "192.168.0.0/16,172.16.0.0/12"
    )
    allowed_networks = []
    for cidr in [c.strip() for c in allowed_cidrs_env.split(",") if c.strip()]:
        try:
            allowed_networks.append(ipaddress.ip_network(cidr, strict=False))
        except Exception:
            pass
    def role_required(required_role: str):
        """Decorator to require a specific role ("admin", "student", or "teacher")."""

        from functools import wraps

        def decorator(view_func):
            @wraps(view_func)
            def wrapper(*args, **kwargs):
                if not current_user.is_authenticated:
                    return redirect(url_for("login"))
                if current_user.role != required_role:
                    flash("You do not have access to this page.", "danger")
                    # Send users to their appropriate dashboard if they have the other role
                    if current_user.role == "admin":
                        return redirect(url_for("admin_dashboard"))
                    if current_user.role == "teacher":
                        return redirect(url_for("teacher_dashboard"))
                    if current_user.role == "student":
                        return redirect(url_for("student_dashboard"))
                    if current_user.role == "hod":
                        return redirect(url_for("hod_dashboard"))
                    if current_user.role == "principal":
                        return redirect(url_for("principal_dashboard"))
                    return redirect(url_for("login"))
                return view_func(*args, **kwargs)

            return wrapper

        return decorator

    def get_client_ip() -> str:
        """Get the best-effort client IP, considering proxies (X-Forwarded-For)."""
        xff = request.headers.get("X-Forwarded-For", "")
        if xff:
            # The left-most IP is the original client in most setups
            return xff.split(",")[0].strip()
        return request.remote_addr or ""

    def is_on_allowed_network(ip_str: str) -> bool:
        """Check if the provided IP is within any allowed CIDR networks."""
        if not ip_str:
            return False
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            # Normalize IPv4-mapped IPv6 (e.g., ::ffff:192.168.1.10) to IPv4
            if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
                ip_obj = ip_obj.ipv4_mapped
        except Exception:
            return False
        # Only match networks with same IP version
        for net in allowed_networks:
            if ip_obj.version == net.version and ip_obj in net:
                return True
        return False

    def is_on_configured_wifi(ip_str: str) -> tuple[bool, WiFiNetwork]:
        """Check if the provided IP is on a configured WiFi network and return the network."""
        if not ip_str:
            return False, None
        
        try:
            client_ip = ipaddress.ip_address(ip_str)
            # Normalize IPv4-mapped IPv6 to IPv4
            if isinstance(client_ip, ipaddress.IPv6Address) and client_ip.ipv4_mapped:
                client_ip = client_ip.ipv4_mapped
        except Exception:
            return False, None
        
        # Get all active WiFi networks
        active_networks = WiFiNetwork.query.filter_by(is_active=True).all()
        
        for wifi_network in active_networks:
            try:
                # Parse router IP
                router_ip = ipaddress.ip_address(wifi_network.router_ip)
                
                # If subnet mask is provided, create network
                if wifi_network.subnet_mask:
                    if wifi_network.subnet_mask.startswith('/'):
                        # CIDR notation
                        network = ipaddress.ip_network(f"{wifi_network.router_ip}{wifi_network.subnet_mask}", strict=False)
                    else:
                        # Traditional subnet mask
                        network = ipaddress.ip_network(f"{wifi_network.router_ip}/{wifi_network.subnet_mask}", strict=False)
                    
                    if client_ip.version == network.version and client_ip in network:
                        return True, wifi_network
                else:
                    # If no subnet mask, check if client IP is in the same /24 network as router
                    if client_ip.version == router_ip.version:
                        # Create /24 network for the router IP
                        router_network = ipaddress.ip_network(f"{wifi_network.router_ip}/24", strict=False)
                        if client_ip in router_network:
                            return True, wifi_network
            except Exception:
                continue
        
        return False, None

    def generate_random_password(length=8):
        """Generate a random password for users."""
        import random
        import string
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    def log_password_change(user_id, action, method, notes=None):
        """Log password changes for security auditing."""
        try:
            password_log = PasswordLog(
                user_id=user_id,
                admin_id=current_user.id,
                action=action,
                method=method,
                ip_address=get_client_ip(),
                user_agent=request.headers.get('User-Agent', ''),
                notes=notes
            )
            db.session.add(password_log)
            db.session.commit()
        except Exception as e:
            app.logger.error(f"Failed to log password change: {e}")

    def send_password_notification(user, new_password, method="manual"):
        """Send password notification to user (placeholder for email integration)."""
        # This is a placeholder - in production, integrate with email service
        app.logger.info(f"Password notification for {user.email}: {new_password} (method: {method})")
        # TODO: Implement actual email sending
        return True

    # --------------------------
    # Routes - Home & Auth
    # --------------------------
    @app.route("/")
    def index():
        if current_user.is_authenticated:
            if current_user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            if current_user.role == "teacher":
                return redirect(url_for("teacher_dashboard"))
            if current_user.role == "student":
                return redirect(url_for("student_dashboard"))
            if current_user.role == "hod":
                return redirect(url_for("hod_dashboard"))
            if current_user.role == "principal":
                return redirect(url_for("principal_dashboard"))
        return redirect(url_for("login"))

    # Signup removed - only admin creates accounts

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").lower().strip()
            password = request.form.get("password", "")

            user = User.query.filter_by(email=email).first()
            if not user or not check_password_hash(user.password_hash, password):
                flash("Invalid email or password.", "danger")
                return render_template("login.html")

            login_user(user)
            flash("Logged in successfully.", "success")
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            if user.role == "teacher":
                return redirect(url_for("teacher_dashboard"))
            if user.role == "hod":
                return redirect(url_for("hod_dashboard"))
            if user.role == "principal":
                return redirect(url_for("principal_dashboard"))
            return redirect(url_for("student_dashboard"))

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Logged out.", "info")
        return redirect(url_for("login"))

    # --------------------------
    # Routes - Admin
    # --------------------------
    @app.route("/admin", methods=["GET"])
    @login_required
    @role_required("admin")
    def admin_dashboard():
        """Admin dashboard with system statistics and management options."""
        # Get system statistics
        total_departments = Department.query.count()
        total_branches = Branch.query.count()
        total_semesters = Semester.query.count()
        total_classes = ClassModel.query.count()
        total_teachers = User.query.filter_by(role="teacher").count()
        total_students = User.query.filter_by(role="student").count()
        active_students = User.query.filter_by(role="student", status="Active").count()
        alumni_students = User.query.filter_by(role="student", status="Alumni").count()
        
        # Get recent activity (last 10 sessions)
        recent_sessions = SessionModel.query.order_by(SessionModel.created_at.desc()).limit(10).all()
        
        # Add current time for template comparison
        current_time = datetime.now(timezone.utc)
        
        stats = {
            'departments': total_departments,
            'branches': total_branches,
            'semesters': total_semesters,
            'classes': total_classes,
            'teachers': total_teachers,
            'students': total_students,
            'active_students': active_students,
            'alumni_students': alumni_students
        }
        
        return render_template("admin_dashboard.html", stats=stats, recent_sessions=recent_sessions, current_time=current_time)

    # --------------------------
    # Routes - HOD
    # --------------------------
    @app.route("/hod", methods=["GET"])
    @login_required
    @role_required("hod")
    def hod_dashboard():
        """HOD dashboard with department-specific analytics."""
        # Get HOD's department
        hod_department = current_user.department
        if not hod_department:
            flash("No department assigned to HOD.", "danger")
            return redirect(url_for("login"))
        
        # Get department statistics
        department_branches = Branch.query.filter_by(department_id=hod_department.id).all()
        department_classes = ClassModel.query.join(Branch).filter(Branch.department_id == hod_department.id).all()
        department_teachers = User.query.filter_by(role="teacher").join(ClassModel).join(Branch).filter(Branch.department_id == hod_department.id).distinct().all()
        department_students = User.query.filter_by(role="student").join(ClassModel).join(Branch).filter(Branch.department_id == hod_department.id).all()
        active_students = [s for s in department_students if s.status == "Active"]
        alumni_students = [s for s in department_students if s.status == "Alumni"]
        
        # Get recent sessions for department classes
        class_ids = [c.id for c in department_classes]
        recent_sessions = SessionModel.query.filter(SessionModel.class_id.in_(class_ids)).order_by(SessionModel.created_at.desc()).limit(10).all()
        
        # Calculate attendance statistics
        total_sessions = len(recent_sessions)
        total_attendance = 0
        for session in recent_sessions:
            total_attendance += len(session.attendances)
        
        avg_attendance = (total_attendance / total_sessions) if total_sessions > 0 else 0
        
        # Get attendance by class
        class_attendance = {}
        for class_obj in department_classes:
            class_sessions = SessionModel.query.filter_by(class_id=class_obj.id).all()
            class_total_attendance = sum(len(session.attendances) for session in class_sessions)
            class_attendance[class_obj.id] = {
                'name': class_obj.name,
                'total_attendance': class_total_attendance,
                'sessions': len(class_sessions)
            }
        
        stats = {
            'department_name': hod_department.name,
            'branches': len(department_branches),
            'classes': len(department_classes),
            'teachers': len(department_teachers),
            'students': len(department_students),
            'active_students': len(active_students),
            'alumni_students': len(alumni_students),
            'total_sessions': total_sessions,
            'avg_attendance': round(avg_attendance, 1)
        }
        
        current_time = datetime.now(timezone.utc)
        
        return render_template("hod_dashboard.html", 
                             stats=stats, 
                             recent_sessions=recent_sessions, 
                             class_attendance=class_attendance,
                             current_time=current_time)

    # --------------------------
    # Routes - Principal
    # --------------------------
    @app.route("/principal", methods=["GET"])
    @login_required
    @role_required("principal")
    def principal_dashboard():
        """Principal dashboard with institution-wide analytics."""
        # Get institution-wide statistics
        total_departments = Department.query.count()
        total_branches = Branch.query.count()
        total_semesters = Semester.query.count()
        total_classes = ClassModel.query.count()
        total_teachers = User.query.filter_by(role="teacher").count()
        total_students = User.query.filter_by(role="student").count()
        active_students = User.query.filter_by(role="student", status="Active").count()
        alumni_students = User.query.filter_by(role="student", status="Alumni").count()
        
        # Get department-wise statistics
        departments = Department.query.all()
        dept_stats = []
        for dept in departments:
            dept_branches = Branch.query.filter_by(department_id=dept.id).count()
            dept_classes = ClassModel.query.join(Branch).filter(Branch.department_id == dept.id).count()
            dept_students = User.query.filter_by(role="student").join(ClassModel).join(Branch).filter(Branch.department_id == dept.id).count()
            dept_teachers = User.query.filter_by(role="teacher").join(ClassModel).join(Branch).filter(Branch.department_id == dept.id).distinct().count()
            
            dept_stats.append({
                'name': dept.name,
                'branches': dept_branches,
                'classes': dept_classes,
                'students': dept_students,
                'teachers': dept_teachers
            })
        
        # Get recent activity (last 20 sessions)
        recent_sessions = SessionModel.query.order_by(SessionModel.created_at.desc()).limit(20).all()
        
        # Calculate overall attendance statistics
        total_sessions = len(recent_sessions)
        total_attendance = 0
        for session in recent_sessions:
            total_attendance += len(session.attendances)
        
        avg_attendance = (total_attendance / total_sessions) if total_sessions > 0 else 0
        
        stats = {
            'departments': total_departments,
            'branches': total_branches,
            'semesters': total_semesters,
            'classes': total_classes,
            'teachers': total_teachers,
            'students': total_students,
            'active_students': active_students,
            'alumni_students': alumni_students,
            'total_sessions': total_sessions,
            'avg_attendance': round(avg_attendance, 1)
        }
        
        current_time = datetime.now(timezone.utc)
        
        return render_template("principal_dashboard.html", 
                             stats=stats, 
                             dept_stats=dept_stats,
                             recent_sessions=recent_sessions, 
                             current_time=current_time)

    # Department Management
    @app.route("/admin/departments", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def manage_departments():
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "create":
                name = request.form.get("name", "").strip()
                code = request.form.get("code", "").strip().upper()
                
                if not name or not code:
                    flash("Please fill all fields.", "danger")
                else:
                    existing = Department.query.filter_by(code=code).first()
                    if existing:
                        flash("Department with this code already exists.", "danger")
                    else:
                        dept = Department(name=name, code=code)
                        db.session.add(dept)
                        db.session.commit()
                        flash(f"Department '{name}' created successfully.", "success")
            
            elif action == "edit":
                dept_id = request.form.get("dept_id")
                name = request.form.get("name", "").strip()
                code = request.form.get("code", "").strip().upper()
                
                dept = Department.query.get(dept_id)
                if dept:
                    dept.name = name
                    dept.code = code
                    db.session.commit()
                    flash("Department updated successfully.", "success")
            
            elif action == "delete":
                dept_id = request.form.get("dept_id")
                dept = Department.query.get(dept_id)
                if dept:
                    # Check if department has branches
                    if dept.branches:
                        flash("Cannot delete department with existing branches.", "danger")
                    else:
                        db.session.delete(dept)
                        db.session.commit()
                        flash("Department deleted successfully.", "success")
            
            return redirect(url_for("manage_departments"))
        
        departments = Department.query.order_by(Department.name).all()
        return render_template("admin_departments.html", departments=departments)

    # Branch Management
    @app.route("/admin/branches", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def manage_branches():
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "create":
                name = request.form.get("name", "").strip()
                code = request.form.get("code", "").strip().upper()
                department_id = request.form.get("department_id")
                
                if not name or not code or not department_id:
                    flash("Please fill all fields.", "danger")
                else:
                    existing = Branch.query.filter_by(
                        code=code, department_id=department_id
                    ).first()
                    if existing:
                        flash("Branch with this code already exists in this department.", "danger")
                    else:
                        branch = Branch(name=name, code=code, department_id=department_id)
                        db.session.add(branch)
                        db.session.commit()
                        flash(f"Branch '{name}' created successfully.", "success")
            
            elif action == "edit":
                branch_id = request.form.get("branch_id")
                name = request.form.get("name", "").strip()
                code = request.form.get("code", "").strip().upper()
                department_id = request.form.get("department_id")
                
                branch = Branch.query.get(branch_id)
                if branch:
                    branch.name = name
                    branch.code = code
                    branch.department_id = department_id
                    db.session.commit()
                    flash("Branch updated successfully.", "success")
            
            elif action == "delete":
                branch_id = request.form.get("branch_id")
                branch = Branch.query.get(branch_id)
                if branch:
                    # Check if branch has classes
                    if branch.classes:
                        flash("Cannot delete branch with existing classes.", "danger")
                    else:
                        db.session.delete(branch)
                        db.session.commit()
                        flash("Branch deleted successfully.", "success")
            
            return redirect(url_for("manage_branches"))
        
        branches = Branch.query.join(Department).order_by(Department.name, Branch.name).all()
        departments = Department.query.order_by(Department.name).all()
        return render_template("admin_branches.html", branches=branches, departments=departments)

    # Class Management
    @app.route("/admin/classes", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def manage_classes():
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "create":
                name = request.form.get("name", "").strip()
                division = request.form.get("division", "").strip()
                semester_id = request.form.get("semester_id")
                branch_id = request.form.get("branch_id")
                
                if not name or not semester_id or not branch_id:
                    flash("Please fill all required fields.", "danger")
                else:
                    existing = ClassModel.query.filter_by(name=name).first()
                    if existing:
                        flash("Class with this name already exists.", "danger")
                    else:
                        class_obj = ClassModel(
                            name=name,
                            division=division,
                            semester_id=semester_id,
                            branch_id=branch_id
                        )
                        db.session.add(class_obj)
                        db.session.commit()
                        flash(f"Class '{name}' created successfully.", "success")
            
            elif action == "edit":
                class_id = request.form.get("class_id")
                name = request.form.get("name", "").strip()
                division = request.form.get("division", "").strip()
                semester_id = request.form.get("semester_id")
                branch_id = request.form.get("branch_id")
                
                class_obj = ClassModel.query.get(class_id)
                if class_obj:
                    class_obj.name = name
                    class_obj.division = division
                    class_obj.semester_id = semester_id
                    class_obj.branch_id = branch_id
                    db.session.commit()
                    flash("Class updated successfully.", "success")
            
            elif action == "delete":
                class_id = request.form.get("class_id")
                class_obj = ClassModel.query.get(class_id)
                if class_obj:
                    # Check if class has students
                    if class_obj.students:
                        flash("Cannot delete class with existing students.", "danger")
                    else:
                        db.session.delete(class_obj)
                        db.session.commit()
                        flash("Class deleted successfully.", "success")
            
            return redirect(url_for("manage_classes"))
        
        classes = ClassModel.query.join(Semester).join(Branch).join(Department).order_by(
            Semester.number, Department.name, Branch.name, ClassModel.division
        ).all()
        semesters = Semester.query.order_by(Semester.number).all()
        branches = Branch.query.join(Department).order_by(Department.name, Branch.name).all()
        return render_template("admin_classes.html", classes=classes, semesters=semesters, branches=branches)

    # Teacher Management
    @app.route("/admin/teachers", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def manage_teachers():
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "create":
                name = request.form.get("name", "").strip()
                email = request.form.get("email", "").lower().strip()
                password = request.form.get("password", "")
                role = request.form.get("role", "teacher")
                department_id = request.form.get("department_id", None)
                
                if not name or not email or not password:
                    flash("Please fill all fields.", "danger")
                else:
                    existing = User.query.filter_by(email=email).first()
                    if existing:
                        flash("User with this email already exists.", "danger")
                    else:
                        user_data = {
                            'name': name,
                            'email': email,
                            'password_hash': generate_password_hash(password),
                            'role': role
                        }
                        
                        # Add department_id for HOD role
                        if role == "hod" and department_id:
                            user_data['department_id'] = department_id
                        
                        user = User(**user_data)
                        db.session.add(user)
                        db.session.commit()
                        
                        # Log password creation
                        log_password_change(user.id, "created", "manual", f"{role.title()} account created by admin")
                        
                        flash(f"{role.title()} '{name}' created successfully.", "success")
            
            elif action == "edit":
                teacher_id = request.form.get("teacher_id")
                name = request.form.get("name", "").strip()
                email = request.form.get("email", "").lower().strip()
                password = request.form.get("password", "")
                
                teacher = User.query.get(teacher_id)
                if teacher and teacher.role in ["teacher", "hod", "principal"]:
                    teacher.name = name
                    teacher.email = email
                    if password:
                        teacher.password_hash = generate_password_hash(password)
                        # Log password update
                        log_password_change(teacher.id, "updated", "manual", f"{teacher.role.title()} password updated by admin")
                    db.session.commit()
                    flash(f"{teacher.role.title()} updated successfully.", "success")
            
            elif action == "delete":
                teacher_id = request.form.get("teacher_id")
                teacher = User.query.get(teacher_id)
                if teacher and teacher.role in ["teacher", "hod", "principal"]:
                    # Remove teacher-class assignments (only for teachers)
                    if teacher.role == "teacher":
                        TeacherClass.query.filter_by(teacher_id=teacher_id).delete()
                    
                    db.session.delete(teacher)
                    db.session.commit()
                    flash(f"{teacher.role.title()} deleted successfully.", "success")
            
            elif action == "assign_class":
                teacher_id = request.form.get("teacher_id")
                class_id = request.form.get("class_id")
                
                if teacher_id and class_id:
                    existing = TeacherClass.query.filter_by(
                        teacher_id=teacher_id, class_id=class_id
                    ).first()
                    if existing:
                        flash("Teacher is already assigned to this class.", "warning")
                    else:
                        teacher_class = TeacherClass(teacher_id=teacher_id, class_id=class_id)
                        db.session.add(teacher_class)
                        db.session.commit()
                        flash("Teacher assigned to class successfully.", "success")
            
            elif action == "remove_assignment":
                assignment_id = request.form.get("assignment_id")
                assignment = TeacherClass.query.get(assignment_id)
                if assignment:
                    db.session.delete(assignment)
                    db.session.commit()
                    flash("Class assignment removed successfully.", "success")
            
            elif action == "reset_password":
                user_id = request.form.get("user_id")
                new_password = request.form.get("new_password", "").strip()
                password_type = request.form.get("password_type", "manual")
                
                if not user_id:
                    flash("User ID is required.", "danger")
                elif not new_password and password_type == "manual":
                    flash("New password is required.", "danger")
                else:
                    user = User.query.get(user_id)
                    if user and user.role in ["teacher", "hod", "principal"]:
                        # Generate password if auto type
                        if password_type == "auto":
                            import random
                            import string
                            new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                        
                        # Update password
                        user.password_hash = generate_password_hash(new_password)
                        db.session.commit()
                        
                        # Log password change
                        log_password_change(user.id, "reset", password_type, f"Password reset by admin for {user.role}")
                        
                        flash(f"Password reset for {user.name} ({user.role.upper()}). New password: {new_password}", "success")
                    else:
                        flash("User not found or invalid role.", "danger")
            
            return redirect(url_for("manage_teachers"))
        
        teachers = User.query.filter(User.role.in_(["teacher", "hod", "principal"])).order_by(User.role, User.name).all()
        classes = ClassModel.query.join(Semester).join(Branch).join(Department).order_by(
            Semester.number, Department.name, Branch.name, ClassModel.division
        ).all()
        teacher_classes = TeacherClass.query.join(User).join(ClassModel).order_by(User.name).all()
        departments = Department.query.order_by(Department.name).all()
        return render_template("admin_teachers.html", teachers=teachers, classes=classes, teacher_classes=teacher_classes, departments=departments)

    # Student Management
    @app.route("/admin/students", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def manage_students():
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "create":
                name = request.form.get("name", "").strip()
                email = request.form.get("email", "").lower().strip()
                roll_number = request.form.get("roll_number", "").strip()
                class_id = request.form.get("class_id")
                password = request.form.get("password", "student123")  # Default password
                
                if not name or not email or not roll_number or not class_id:
                    flash("Please fill all required fields.", "danger")
                else:
                    existing_email = User.query.filter_by(email=email).first()
                    if existing_email:
                        flash("Student with this email already exists.", "danger")
                    else:
                        existing_roll = User.query.filter_by(
                            roll_number=roll_number, class_id=class_id
                        ).first()
                        if existing_roll:
                            flash("Student with this roll number already exists in this class.", "danger")
                        else:
                            student = User(
                                name=name,
                                email=email,
                                password_hash=generate_password_hash(password),
                                role="student",
                                roll_number=roll_number,
                                class_id=class_id,
                                status="Active"
                            )
                            db.session.add(student)
                            db.session.commit()
                            
                            # Log password creation
                            log_password_change(student.id, "created", "manual", f"Student account created by admin")
                            
                            flash(f"Student '{name}' created successfully.", "success")
            
            elif action == "edit":
                student_id = request.form.get("student_id")
                name = request.form.get("name", "").strip()
                email = request.form.get("email", "").lower().strip()
                roll_number = request.form.get("roll_number", "").strip()
                class_id = request.form.get("class_id")
                status = request.form.get("status", "Active")
                password = request.form.get("password", "")
                
                student = User.query.get(student_id)
                if student and student.role == "student":
                    student.name = name
                    student.email = email
                    student.roll_number = roll_number
                    student.class_id = class_id
                    student.status = status
                    if password:
                        student.password_hash = generate_password_hash(password)
                        # Log password update
                        log_password_change(student.id, "updated", "manual", f"Student password updated by admin")
                    db.session.commit()
                    flash("Student updated successfully.", "success")
            
            elif action == "delete":
                student_id = request.form.get("student_id")
                student = User.query.get(student_id)
                if student and student.role == "student":
                    # Remove attendance records
                    Attendance.query.filter_by(user_id=student_id).delete()
                    db.session.delete(student)
                    db.session.commit()
                    flash("Student deleted successfully.", "success")
            
            elif action == "promote":
                # Promote all students to next semester
                current_semester = request.form.get("current_semester")
                if current_semester:
                    # Get all students in current semester
                    students = User.query.join(ClassModel).join(Semester).filter(
                        User.role == "student",
                        Semester.number == int(current_semester)
                    ).all()
                    
                    promoted_count = 0
                    for student in students:
                        if student.class_obj and student.class_obj.semester:
                            current_sem_num = student.class_obj.semester.number
                            if current_sem_num < 8:
                                # Find next semester class
                                next_semester = Semester.query.filter_by(number=current_sem_num + 1).first()
                                if next_semester:
                                    # Find class with same branch and division
                                    next_class = ClassModel.query.filter_by(
                                        semester_id=next_semester.id,
                                        branch_id=student.class_obj.branch_id,
                                        division=student.class_obj.division
                                    ).first()
                                    if next_class:
                                        student.class_id = next_class.id
                                        promoted_count += 1
                            else:
                                # Mark as Alumni
                                student.status = "Alumni"
                                promoted_count += 1
                    
                    db.session.commit()
                    flash(f"Promoted {promoted_count} students successfully.", "success")
            
            return redirect(url_for("manage_students"))
        
        students = User.query.filter_by(role="student").join(ClassModel).join(Semester).join(Branch).join(Department).order_by(
            Semester.number, Department.name, Branch.name, ClassModel.division, User.roll_number
        ).all()
        classes = ClassModel.query.join(Semester).join(Branch).join(Department).order_by(
            Semester.number, Department.name, Branch.name, ClassModel.division
        ).all()
        semesters = Semester.query.order_by(Semester.number).all()
        # Get class statistics
        class_stats = {}
        for class_obj in classes:
            student_count = User.query.filter_by(role="student", class_id=class_obj.id).count()
            class_stats[class_obj.id] = student_count
        
        return render_template("admin_students.html", 
                             students=students, 
                             classes=classes, 
                             semesters=semesters,
                             class_stats=class_stats,
                             class_filter="",
                             search_query="")

    # Password Management
    @app.route("/admin/passwords", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def manage_passwords():
        """Password management interface for admin."""
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "reset_password":
                user_id = request.form.get("user_id")
                password_type = request.form.get("password_type")  # "manual" or "auto"
                new_password = request.form.get("new_password", "").strip()
                send_notification = request.form.get("send_notification") == "on"
                
                user = User.query.get(user_id)
                if not user:
                    flash("User not found.", "danger")
                    return redirect(url_for("manage_passwords"))
                
                if password_type == "auto":
                    new_password = generate_random_password(8)
                    method = "auto_generated"
                else:
                    if not new_password:
                        flash("Please enter a new password.", "danger")
                        return redirect(url_for("manage_passwords"))
                    method = "manual"
                
                # Update password
                user.password_hash = generate_password_hash(new_password)
                db.session.commit()
                
                # Log password change
                log_password_change(user.id, "reset", method, f"Password reset by admin")
                
                # Send notification if requested
                if send_notification:
                    send_password_notification(user, new_password, method)
                
                flash(f"Password updated for {user.name}. New password: {new_password}", "success")
            
            elif action == "bulk_reset":
                role = request.form.get("role")
                password_type = request.form.get("bulk_password_type")
                new_password = request.form.get("bulk_new_password", "").strip()
                
                if not role:
                    flash("Please select a role.", "danger")
                    return redirect(url_for("manage_passwords"))
                
                users = User.query.filter_by(role=role).all()
                if not users:
                    flash(f"No {role}s found.", "warning")
                    return redirect(url_for("manage_passwords"))
                
                updated_count = 0
                for user in users:
                    if password_type == "auto":
                        new_password = generate_random_password(8)
                        method = "auto_generated"
                    else:
                        if not new_password:
                            flash("Please enter a new password.", "danger")
                            return redirect(url_for("manage_passwords"))
                        method = "manual"
                    
                    user.password_hash = generate_password_hash(new_password)
                    log_password_change(user.id, "reset", method, f"Bulk password reset by admin")
                    updated_count += 1
                
                db.session.commit()
                flash(f"Updated passwords for {updated_count} {role}s. New password: {new_password}", "success")
            
            return redirect(url_for("manage_passwords"))
        
        # Get all users with their password log info
        users = User.query.filter(User.role.in_(["teacher", "student"])).order_by(User.role, User.name).all()
        
        # Get recent password changes
        recent_changes = PasswordLog.query.join(User, PasswordLog.user_id == User.id).order_by(
            PasswordLog.timestamp.desc()
        ).limit(20).all()
        
        return render_template("admin_passwords.html", users=users, recent_changes=recent_changes)

    @app.route("/admin/passwords/bulk_upload", methods=["POST"])
    @login_required
    @role_required("admin")
    def bulk_upload_passwords():
        """Handle bulk password upload via CSV."""
        import csv
        import io
        
        file = request.files['csv_file']
        password_column = request.form.get('password_column', 'password')
        auto_generate_missing = request.form.get('auto_generate_missing') == 'on'
        default_password = request.form.get('default_password', '').strip()
        
        if file.filename == '':
            flash('No file selected', 'warning')
            return redirect(url_for("manage_passwords"))
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file', 'warning')
            return redirect(url_for("manage_passwords"))
        
        try:
            # Read CSV content
            content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            # Validate required columns
            required_columns = ['email']
            if password_column not in csv_reader.fieldnames:
                flash(f'Password column "{password_column}" not found in CSV', 'danger')
                return redirect(url_for("manage_passwords"))
            
            updated_count = 0
            failed_count = 0
            
            for row in csv_reader:
                try:
                    email = row['email'].strip().lower()
                    password = row.get(password_column, '').strip()
                    
                    if not email:
                        failed_count += 1
                        continue
                    
                    user = User.query.filter_by(email=email).first()
                    if not user:
                        failed_count += 1
                        continue
                    
                    # Determine password and method
                    if password:
                        new_password = password
                        method = "bulk_upload"
                    elif auto_generate_missing:
                        new_password = generate_random_password(8)
                        method = "auto_generated"
                    elif default_password:
                        new_password = default_password
                        method = "bulk_upload"
                    else:
                        failed_count += 1
                        continue
                    
                    # Update password
                    user.password_hash = generate_password_hash(new_password)
                    log_password_change(user.id, "updated", method, f"Bulk upload - password updated")
                    updated_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    continue
            
            if updated_count > 0:
                db.session.commit()
                flash(f'Successfully updated passwords for {updated_count} users!', 'success')
                if failed_count > 0:
                    flash(f'Failed to update {failed_count} users (invalid email or missing data)', 'warning')
            else:
                flash('No users were updated. Check your CSV format and data.', 'warning')
            
        except Exception as e:
            flash(f'Error processing CSV file: {str(e)}', 'danger')
        
        return redirect(url_for("manage_passwords"))

    @app.route("/admin/passwords/download_template")
    @login_required
    @role_required("admin")
    def download_password_template():
        """Download CSV template for bulk password upload."""
        import csv
        import io
        
        # Create sample CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['email', 'password'])
        
        # Write sample data
        sample_data = [
            ['teacher1@university.edu', 'newpassword123'],
            ['student1@student.edu', 'studentpass456'],
            ['teacher2@university.edu', ''],  # Empty password for auto-generation
            ['student2@student.edu', 'custompass789'],
        ]
        
        for row in sample_data:
            writer.writerow(row)
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            as_attachment=True,
            download_name='password_template.csv',
            mimetype='text/csv'
        )

    # --------------------------
    # Routes - Teacher
    # --------------------------
    @app.route("/teacher", methods=["GET"])
    @login_required
    @role_required("teacher")
    def teacher_dashboard():
        # Get classes assigned to this teacher
        teacher_classes = TeacherClass.query.filter_by(teacher_id=current_user.id).all()
        class_ids = [tc.class_id for tc in teacher_classes]
        classes = ClassModel.query.filter(ClassModel.id.in_(class_ids)).order_by(ClassModel.name).all()
        
        return render_template("teacher_dashboard.html", classes=classes)

    @app.route("/teacher/class/<int:class_id>", methods=["GET"])
    @login_required
    @role_required("teacher")
    def class_page(class_id):
        # Verify teacher has access to this class
        teacher_class = TeacherClass.query.filter_by(
            teacher_id=current_user.id, class_id=class_id
        ).first()
        if not teacher_class:
            flash("You don't have access to this class.", "danger")
            return redirect(url_for("teacher_dashboard"))
        
        class_obj = ClassModel.query.get_or_404(class_id)
        students = User.query.filter_by(class_id=class_id, role="student").order_by(User.roll_number).all()
        
        # Get the latest session for this class
        latest_session = SessionModel.query.filter_by(class_id=class_id).order_by(SessionModel.created_at.desc()).first()
        
        # Get attendance status for each student in the latest session
        attendance_data = []
        if latest_session:
            for student in students:
                attendance = Attendance.query.filter_by(
                    user_id=student.id, session_id=latest_session.id
                ).first()
                attendance_data.append({
                    'student': student,
                    'present': attendance is not None
                })
        else:
            attendance_data = [{'student': student, 'present': False} for student in students]
        
        return render_template("class_page.html", 
                             class_obj=class_obj, 
                             students=students, 
                             attendance_data=attendance_data,
                             latest_session=latest_session)

    @app.route("/teacher/class/<int:class_id>/generate_qr", methods=["POST"])
    @login_required
    @role_required("teacher")
    def generate_class_qr(class_id):
        # Verify teacher has access to this class
        teacher_class = TeacherClass.query.filter_by(
            teacher_id=current_user.id, class_id=class_id
        ).first()
        if not teacher_class:
            flash("You don't have access to this class.", "danger")
            return redirect(url_for("teacher_dashboard"))
        
        # Get QR expiry from form (30 seconds or 1 minute)
        qr_expiry_seconds = int(request.form.get("qr_expiry", 30))
        if qr_expiry_seconds not in [30, 60]:
            qr_expiry_seconds = 30
        
        # Create a new attendance session
        new_session_uuid = str(uuid.uuid4())
        expiry = datetime.now(timezone.utc) + timedelta(seconds=qr_expiry_seconds)

        session_row = SessionModel(
            session_uuid=new_session_uuid, 
            expiry=expiry, 
            class_id=class_id,
            teacher_id=current_user.id,
            qr_expiry_seconds=qr_expiry_seconds
        )
        db.session.add(session_row)
        db.session.commit()

        # QR payload contains session_id and expiry in ISO format
        qr_payload = f"{new_session_uuid}|{expiry.isoformat()}"

        # Ensure static directory exists
        static_dir = os.path.join(app.root_path, "static")
        os.makedirs(static_dir, exist_ok=True)
        qr_path = os.path.join(static_dir, f"qr_class_{class_id}.png")

        # Generate and save QR image
        img = qrcode.make(qr_payload)
        img.save(qr_path)

        flash(f"QR generated for this class (expires in {qr_expiry_seconds}s). Students can now scan to mark attendance.", "success")
        return redirect(url_for("class_page", class_id=class_id))

    @app.route("/teacher/proxy_lecture", methods=["GET", "POST"])
    @login_required
    @role_required("teacher")
    def proxy_lecture():
        """Proxy lecture interface for generating QR codes for any class."""
        if request.method == "POST":
            class_id = request.form.get("class_id")
            qr_expiry_seconds = int(request.form.get("qr_expiry", 30))
            proxy_teacher_name = request.form.get("proxy_teacher_name", "").strip()
            
            if not class_id:
                flash("Please select a class.", "danger")
                return redirect(url_for("proxy_lecture"))
            
            if not proxy_teacher_name:
                flash("Please enter the proxy teacher's name.", "danger")
                return redirect(url_for("proxy_lecture"))
            
            # Validate QR expiry
            if qr_expiry_seconds not in [30, 60, 120, 300]:
                qr_expiry_seconds = 30
            
            # Get the class
            class_obj = ClassModel.query.get(class_id)
            if not class_obj:
                flash("Class not found.", "danger")
                return redirect(url_for("proxy_lecture"))
            
            # Create a new attendance session for proxy lecture
            new_session_uuid = str(uuid.uuid4())
            expiry = datetime.now(timezone.utc) + timedelta(seconds=qr_expiry_seconds)

            session_row = SessionModel(
                session_uuid=new_session_uuid, 
                expiry=expiry, 
                class_id=class_id,
                teacher_id=current_user.id,  # Current teacher generating the QR
                qr_expiry_seconds=qr_expiry_seconds,
                is_proxy=True,  # Mark as proxy lecture
                proxy_teacher_name=proxy_teacher_name
            )
            db.session.add(session_row)
            db.session.commit()

            # Generate QR code
            qr_payload = f"{new_session_uuid}|{expiry.isoformat()}"
            
            # Ensure static directory exists
            static_dir = os.path.join(app.root_path, "static")
            os.makedirs(static_dir, exist_ok=True)
            qr_path = os.path.join(static_dir, f"proxy_qr_{class_id}_{new_session_uuid[:8]}.png")
            
            # Generate and save QR image
            img = qrcode.make(qr_payload)
            img.save(qr_path)

            flash(f"Proxy QR generated for {class_obj.name} (expires in {qr_expiry_seconds}s). Proxy teacher: {proxy_teacher_name}", "success")
            return redirect(url_for("proxy_lecture"))
        
        # GET request - show proxy lecture interface
        # Get all classes for the dropdown
        all_classes = ClassModel.query.order_by(ClassModel.name).all()
        
        return render_template("proxy_lecture.html", classes=all_classes)

    @app.route("/teacher/class/<int:class_id>/download_pdf", methods=["GET"])
    @login_required
    @role_required("teacher")
    def download_class_pdf(class_id):
        # Verify teacher has access to this class
        teacher_class = TeacherClass.query.filter_by(
            teacher_id=current_user.id, class_id=class_id
        ).first()
        if not teacher_class:
            flash("You don't have access to this class.", "danger")
            return redirect(url_for("teacher_dashboard"))
        
        class_obj = ClassModel.query.get_or_404(class_id)
        students = User.query.filter_by(class_id=class_id, role="student").order_by(User.roll_number).all()
        
        # Get the latest session for this class
        latest_session = SessionModel.query.filter_by(class_id=class_id).order_by(SessionModel.created_at.desc()).first()
        
        if not latest_session:
            flash("No session found for this class.", "warning")
            return redirect(url_for("class_page", class_id=class_id))
        
        # Get attendance data
        present_students = []
        absent_students = []
        
        for student in students:
            attendance = Attendance.query.filter_by(
                user_id=student.id, session_id=latest_session.id
            ).first()
            if attendance:
                present_students.append(student)
            else:
                absent_students.append(student)
        
        # Generate PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph(f"Attendance Report - {class_obj.name}", title_style))
        story.append(Spacer(1, 12))
        
        # Session info
        session_style = ParagraphStyle(
            'SessionInfo',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20
        )
        story.append(Paragraph(f"Session Date: {latest_session.created_at.strftime('%Y-%m-%d %H:%M:%S')}", session_style))
        story.append(Paragraph(f"Session ID: {latest_session.session_uuid}", session_style))
        story.append(Spacer(1, 20))
        
        # Present students table
        if present_students:
            story.append(Paragraph("Present Students", styles['Heading2']))
            present_data = [['Roll No', 'Name']]
            for student in present_students:
                present_data.append([student.roll_number or 'N/A', student.name])
            
            present_table = Table(present_data, colWidths=[1.5*inch, 4*inch])
            present_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(present_table)
            story.append(Spacer(1, 20))
        
        # Absent students table
        if absent_students:
            story.append(Paragraph("Absent Students", styles['Heading2']))
            absent_data = [['Roll No', 'Name']]
            for student in absent_students:
                absent_data.append([student.roll_number or 'N/A', student.name])
            
            absent_table = Table(absent_data, colWidths=[1.5*inch, 4*inch])
            absent_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightcoral),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(absent_table)
        
        # Summary
        story.append(Spacer(1, 20))
        summary_style = ParagraphStyle(
            'Summary',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=10
        )
        total_students = len(students)
        present_count = len(present_students)
        absent_count = len(absent_students)
        attendance_percentage = (present_count / total_students * 100) if total_students > 0 else 0
        
        story.append(Paragraph(f"Total Students: {total_students}", summary_style))
        story.append(Paragraph(f"Present: {present_count}", summary_style))
        story.append(Paragraph(f"Absent: {absent_count}", summary_style))
        story.append(Paragraph(f"Attendance Rate: {attendance_percentage:.1f}%", summary_style))
        
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"attendance_{class_obj.name}_{latest_session.created_at.strftime('%Y%m%d_%H%M')}.pdf",
            mimetype='application/pdf'
        )

    @app.route("/teacher/class/<int:class_id>/review", methods=["GET", "POST"])
    @login_required
    @role_required("teacher")
    def review_attendance(class_id):
        """Review and manually adjust attendance within 1-hour window."""
        # Verify teacher has access to this class
        teacher_class = TeacherClass.query.filter_by(
            teacher_id=current_user.id, class_id=class_id
        ).first()
        if not teacher_class:
            flash("You don't have access to this class.", "danger")
            return redirect(url_for("teacher_dashboard"))
        
        class_obj = ClassModel.query.get_or_404(class_id)
        students = User.query.filter_by(class_id=class_id, role="student").order_by(User.roll_number).all()
        
        # Get the latest session for this class
        latest_session = SessionModel.query.filter_by(class_id=class_id).order_by(SessionModel.created_at.desc()).first()
        
        if not latest_session:
            flash("No session found for this class.", "warning")
            return redirect(url_for("class_page", class_id=class_id))
        
        # Check if session is still within 1-hour review window
        now_utc = datetime.now(timezone.utc)
        review_deadline = latest_session.created_at + timedelta(hours=1)
        is_within_review_window = now_utc <= review_deadline and not latest_session.is_locked
        
        if request.method == "POST":
            if not is_within_review_window:
                flash("Review window has expired or session is locked.", "danger")
                return redirect(url_for("review_attendance", class_id=class_id))
            
            # Handle manual attendance changes
            student_id = request.form.get("student_id")
            action = request.form.get("action")  # "mark_present" or "mark_absent"
            reason = request.form.get("reason", "")
            
            if not student_id or not action:
                flash("Invalid request.", "danger")
                return redirect(url_for("review_attendance", class_id=class_id))
            
            student = User.query.get(student_id)
            if not student or student.class_id != class_id:
                flash("Student not found in this class.", "danger")
                return redirect(url_for("review_attendance", class_id=class_id))
            
            # Check current attendance status
            current_attendance = Attendance.query.filter_by(
                user_id=student_id, session_id=latest_session.id
            ).first()
            
            if action == "mark_present" and not current_attendance:
                # Mark present
                attendance = Attendance(user_id=student_id, session_id=latest_session.id)
                db.session.add(attendance)
                
                # Record override
                override = AttendanceOverride(
                    session_id=latest_session.id,
                    student_id=student_id,
                    teacher_id=current_user.id,
                    action="mark_present",
                    reason=reason
                )
                db.session.add(override)
                
                flash(f"Marked {student.name} as present.", "success")
                
            elif action == "mark_absent" and current_attendance:
                # Mark absent
                db.session.delete(current_attendance)
                
                # Record override
                override = AttendanceOverride(
                    session_id=latest_session.id,
                    student_id=student_id,
                    teacher_id=current_user.id,
                    action="mark_absent",
                    reason=reason
                )
                db.session.add(override)
                
                flash(f"Marked {student.name} as absent.", "success")
            
            db.session.commit()
            return redirect(url_for("review_attendance", class_id=class_id))
        
        # Get attendance data for review
        attendance_data = []
        for student in students:
            attendance = Attendance.query.filter_by(
                user_id=student.id, session_id=latest_session.id
            ).first()
            attendance_data.append({
                'student': student,
                'present': attendance is not None,
                'attendance_id': attendance.id if attendance else None
            })
        
        return render_template("attendance_review.html", 
                             class_obj=class_obj, 
                             students=students, 
                             attendance_data=attendance_data,
                             latest_session=latest_session,
                             is_within_review_window=is_within_review_window,
                             review_deadline=review_deadline)

    @app.route("/teacher/class/<int:class_id>/lock_session", methods=["POST"])
    @login_required
    @role_required("teacher")
    def lock_session(class_id):
        """Lock a session to prevent further changes."""
        # Verify teacher has access to this class
        teacher_class = TeacherClass.query.filter_by(
            teacher_id=current_user.id, class_id=class_id
        ).first()
        if not teacher_class:
            flash("You don't have access to this class.", "danger")
            return redirect(url_for("teacher_dashboard"))
        
        # Get the latest session for this class
        latest_session = SessionModel.query.filter_by(class_id=class_id).order_by(SessionModel.created_at.desc()).first()
        
        if not latest_session:
            flash("No session found for this class.", "warning")
            return redirect(url_for("class_page", class_id=class_id))
        
        if latest_session.is_locked:
            flash("Session is already locked.", "info")
        else:
            latest_session.is_locked = True
            db.session.commit()
            flash("Session locked successfully.", "success")
        
        return redirect(url_for("review_attendance", class_id=class_id))

    @app.route("/teacher/class/<int:class_id>/records", methods=["GET"])
    @login_required
    @role_required("teacher")
    def view_class_records(class_id):
        """View past attendance records for a class."""
        # Verify teacher has access to this class
        teacher_class = TeacherClass.query.filter_by(
            teacher_id=current_user.id, class_id=class_id
        ).first()
        if not teacher_class:
            flash("You don't have access to this class.", "danger")
            return redirect(url_for("teacher_dashboard"))
        
        class_obj = ClassModel.query.get_or_404(class_id)
        students = User.query.filter_by(class_id=class_id, role="student").order_by(User.roll_number).all()
        
        # Get all sessions for this class
        sessions = SessionModel.query.filter_by(class_id=class_id).order_by(SessionModel.created_at.desc()).all()
        
        # Get attendance data for each session
        attendance_records = []
        for session in sessions:
            session_attendance = []
            for student in students:
                attendance = Attendance.query.filter_by(
                    user_id=student.id, session_id=session.id
                ).first()
                session_attendance.append({
                    'student': student,
                    'present': attendance is not None,
                    'timestamp': attendance.timestamp if attendance else None
                })
            
            attendance_records.append({
                'session': session,
                'attendance': session_attendance,
                'present_count': len([a for a in session_attendance if a['present']]),
                'total_count': len(students)
            })
        
        return render_template("class_records.html", 
                             class_obj=class_obj, 
                             students=students,
                             attendance_records=attendance_records)

    @app.route("/teacher/class/<int:class_id>/records/download", methods=["GET"])
    @login_required
    @role_required("teacher")
    def download_class_records(class_id):
        """Download attendance records for a class as CSV."""
        # Verify teacher has access to this class
        teacher_class = TeacherClass.query.filter_by(
            teacher_id=current_user.id, class_id=class_id
        ).first()
        if not teacher_class:
            flash("You don't have access to this class.", "danger")
            return redirect(url_for("teacher_dashboard"))
        
        class_obj = ClassModel.query.get_or_404(class_id)
        students = User.query.filter_by(class_id=class_id, role="student").order_by(User.roll_number).all()
        
        # Get all sessions for this class
        sessions = SessionModel.query.filter_by(class_id=class_id).order_by(SessionModel.created_at.desc()).all()
        
        # Create CSV content
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        header = ['Student Name', 'Roll Number', 'Email']
        for session in sessions:
            header.append(f"Session {session.id} ({session.created_at.strftime('%Y-%m-%d %H:%M')})")
        writer.writerow(header)
        
        # Write student data
        for student in students:
            row = [student.name, student.roll_number or 'N/A', student.email]
            for session in sessions:
                attendance = Attendance.query.filter_by(
                    user_id=student.id, session_id=session.id
                ).first()
                row.append('Present' if attendance else 'Absent')
            writer.writerow(row)
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            as_attachment=True,
            download_name=f"attendance_records_{class_obj.name}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mimetype='text/csv'
        )

    @app.route("/teacher/class/<int:class_id>/records/pdf", methods=["GET"])
    @login_required
    @role_required("teacher")
    def download_class_records_pdf(class_id):
        """Download attendance records for a class as PDF."""
        # Verify teacher has access to this class
        teacher_class = TeacherClass.query.filter_by(
            teacher_id=current_user.id, class_id=class_id
        ).first()
        if not teacher_class:
            flash("You don't have access to this class.", "danger")
            return redirect(url_for("teacher_dashboard"))
        
        class_obj = ClassModel.query.get_or_404(class_id)
        students = User.query.filter_by(class_id=class_id, role="student").order_by(User.roll_number).all()
        
        # Get all sessions for this class
        sessions = SessionModel.query.filter_by(class_id=class_id).order_by(SessionModel.created_at.desc()).all()
        
        # Generate PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph(f"Attendance Records - {class_obj.name}", title_style))
        story.append(Spacer(1, 12))
        
        # Class info
        info_style = ParagraphStyle(
            'ClassInfo',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20
        )
        story.append(Paragraph(f"Total Students: {len(students)}", info_style))
        story.append(Paragraph(f"Total Sessions: {len(sessions)}", info_style))
        story.append(Spacer(1, 20))
        
        # Create attendance table
        if sessions:
            # Table header
            table_data = [['Student Name', 'Roll No']]
            for session in sessions:
                table_data[0].append(session.created_at.strftime('%m/%d %H:%M'))
            
            # Student rows
            for student in students:
                row = [student.name, student.roll_number or 'N/A']
                for session in sessions:
                    attendance = Attendance.query.filter_by(
                        user_id=student.id, session_id=session.id
                    ).first()
                    row.append('✓' if attendance else '✗')
                table_data.append(row)
            
            # Create table
            table = Table(table_data, colWidths=[2*inch, 0.8*inch] + [0.6*inch] * len(sessions))
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 7)
            ]))
            story.append(table)
        
        # Summary statistics
        story.append(Spacer(1, 20))
        summary_style = ParagraphStyle(
            'Summary',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=10
        )
        
        # Calculate attendance statistics
        total_possible_attendance = len(students) * len(sessions)
        total_actual_attendance = 0
        for session in sessions:
            total_actual_attendance += len(session.attendances)
        
        attendance_percentage = (total_actual_attendance / total_possible_attendance * 100) if total_possible_attendance > 0 else 0
        
        story.append(Paragraph(f"Total Possible Attendance: {total_possible_attendance}", summary_style))
        story.append(Paragraph(f"Total Actual Attendance: {total_actual_attendance}", summary_style))
        story.append(Paragraph(f"Overall Attendance Rate: {attendance_percentage:.1f}%", summary_style))
        
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"attendance_records_{class_obj.name}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mimetype='application/pdf'
        )

    @app.route("/generate_qr", methods=["POST"])
    @login_required
    @role_required("teacher")
    def generate_qr():
        # Create a new attendance session valid for 5 minutes
        new_session_uuid = str(uuid.uuid4())
        expiry = datetime.now(timezone.utc) + timedelta(minutes=5)

        session_row = SessionModel(session_uuid=new_session_uuid, expiry=expiry)
        db.session.add(session_row)
        db.session.commit()

        # QR payload contains session_id and expiry in ISO format
        qr_payload = f"{new_session_uuid}|{expiry.isoformat()}"

        # Ensure static directory exists
        static_dir = os.path.join(app.root_path, "static")
        os.makedirs(static_dir, exist_ok=True)
        qr_path = os.path.join(static_dir, "current_qr.png")

        # Generate and save QR image
        img = qrcode.make(qr_payload)
        img.save(qr_path)

        flash("QR generated. Students can now scan to mark attendance.", "success")
        return redirect(url_for("teacher_dashboard"))

    # --------------------------
    # Routes - Student
    # --------------------------
    @app.route("/student", methods=["GET"])
    @login_required
    @role_required("student")
    def student_dashboard():
        # Get student's attendance statistics
        student_sessions = SessionModel.query.join(ClassModel).filter(
            ClassModel.id == current_user.class_id
        ).order_by(SessionModel.created_at.desc()).all()
        
        # Calculate attendance percentage
        total_sessions = len(student_sessions)
        attended_sessions = Attendance.query.join(SessionModel).filter(
            Attendance.user_id == current_user.id,
            SessionModel.class_id == current_user.class_id
        ).count()
        
        attendance_percentage = (attended_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        # Get recent attendance history (last 10 sessions)
        recent_attendance = []
        for session in student_sessions[:10]:
            attendance = Attendance.query.filter_by(
                user_id=current_user.id, session_id=session.id
            ).first()
            recent_attendance.append({
                'session': session,
                'present': attendance is not None,
                'timestamp': attendance.timestamp if attendance else None
            })
        
        stats = {
            'total_sessions': total_sessions,
            'attended_sessions': attended_sessions,
            'attendance_percentage': round(attendance_percentage, 1)
        }
        
        return render_template("student.html", stats=stats, recent_attendance=recent_attendance)

    @app.route("/mark_attendance", methods=["POST"])
    @login_required
    @role_required("student")
    def mark_attendance():
        # Expect JSON: { qr_data: "<uuid>|<expiry_iso>", student_id: <id> }
        payload = request.get_json(silent=True) or {}
        qr_data = str(payload.get("qr_data", "")).strip()

        if not qr_data or "|" not in qr_data:
            return jsonify({"ok": False, "message": "Invalid QR data."}), 400

        session_uuid, expiry_iso = qr_data.split("|", 1)
        try:
            expiry_dt = datetime.fromisoformat(expiry_iso)
        except Exception:
            return jsonify({"ok": False, "message": "Malformed expiry in QR."}), 400

        # Validate session exists and not expired
        session_row = SessionModel.query.filter_by(session_uuid=session_uuid).first()
        if not session_row:
            return jsonify({"ok": False, "message": "Session not found."}), 404

        now_utc = datetime.now(timezone.utc)
        if session_row.expiry < now_utc:
            return jsonify({"ok": False, "message": "Session expired."}), 400

        # Prevent duplicate attendance for the same session
        existing = Attendance.query.join(SessionModel, Attendance.session_id == SessionModel.id).filter(
            Attendance.user_id == current_user.id, SessionModel.session_uuid == session_uuid
        ).first()
        if existing:
            return jsonify({"ok": True, "message": "Attendance already recorded for this session."})

        attendance = Attendance(
            user_id=current_user.id, 
            session_id=session_row.id
        )
        db.session.add(attendance)
        db.session.commit()

        # Get class name for confirmation message
        class_name = session_row.class_obj.name if session_row.class_obj else "Unknown Class"
        return jsonify({
            "ok": True, 
            "message": f"Attendance marked for {class_name} on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        })

    # --------------------------
    # Admin routes for setup
    # --------------------------
    @app.route("/admin/setup", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def admin_setup():
        """Setup route to create sample classes and assign teachers (for development)"""
        if request.method == "POST":
            # Check if this is a CSV upload
            if 'csv_file' in request.files:
                return handle_csv_upload(request)
            
            # Create sample classes
            sample_classes = ["5CSE1", "5CSE2", "1CSE1", "1CSE2", "3CSE1", "3CSE2"]
            created_classes = []
            
            for class_name in sample_classes:
                existing = ClassModel.query.filter_by(name=class_name).first()
                if not existing:
                    class_obj = ClassModel(name=class_name)
                    db.session.add(class_obj)
                    created_classes.append(class_name)
            
            db.session.commit()
            
            if created_classes:
                flash(f"Created classes: {', '.join(created_classes)}", "success")
            else:
                flash("All classes already exist.", "info")
            
            return redirect(url_for("admin_setup"))
        
        classes = ClassModel.query.order_by(ClassModel.name).all()
        teachers = User.query.filter_by(role="teacher").all()
        teacher_classes = TeacherClass.query.all()
        
        return render_template("admin_setup.html", classes=classes, teachers=teachers, teacher_classes=teacher_classes)

    def handle_csv_upload(request):
        """Handle CSV file upload for bulk student import"""
        import csv
        import io
        import random
        import string
        from werkzeug.security import generate_password_hash
        
        def generate_password(length=8):
            characters = string.ascii_letters + string.digits
            return ''.join(random.choice(characters) for _ in range(length))
        
        try:
            file = request.files['csv_file']
            default_password = request.form.get('default_password', '').strip()
            
            if not file or file.filename == '':
                flash('No file selected', 'warning')
                return redirect(url_for("admin_setup"))
            
            if not file.filename.endswith('.csv'):
                flash('Please upload a CSV file', 'warning')
                return redirect(url_for("admin_setup"))
        except Exception as e:
            flash(f'Error processing file upload: {str(e)}', 'danger')
            return redirect(url_for("admin_setup"))
        
        try:
            # Read CSV content
            content = file.read().decode('utf-8')
            
            # Check for common CSV issues
            if '\t' in content:
                flash('CSV file contains tab characters. Please use commas to separate columns.', 'danger')
                return redirect(url_for("admin_setup"))
            
            csv_reader = csv.DictReader(io.StringIO(content))
            
            # Validate required columns
            required_columns = ['name', 'email', 'roll_number', 'class_name']
            missing_columns = [col for col in required_columns if col not in csv_reader.fieldnames]
            
            if missing_columns:
                flash(f'Missing required columns: {", ".join(missing_columns)}', 'danger')
                return redirect(url_for("admin_setup"))
            
            # Debug: Show available columns
            app.logger.info(f"CSV columns found: {csv_reader.fieldnames}")
            
        except Exception as e:
            flash(f'Error reading CSV file: {str(e)}. Please check your CSV format.', 'danger')
            return redirect(url_for("admin_setup"))
        
        # Check if password column exists
        has_password_column = 'password' in csv_reader.fieldnames
        
        # Get available classes
        classes = {class_obj.name: class_obj.id for class_obj in ClassModel.query.all()}
        
        imported_count = 0
        failed_count = 0
        
        # Reset file pointer
        file.seek(0)
        content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content))
        
        for row in csv_reader:
            try:
                name = row['name'].strip()
                email = row['email'].strip().lower()
                roll_number = row['roll_number'].strip()
                class_name = row['class_name'].strip()
                
                # Get password from CSV or use default
                if has_password_column:
                    csv_password = row.get('password', '').strip()
                    if csv_password:
                        password = csv_password
                        method = "bulk_upload"
                    else:
                        password = default_password if default_password else generate_password()
                        method = "auto_generated" if not default_password else "bulk_upload"
                else:
                    password = default_password if default_password else generate_password()
                    method = "bulk_upload" if default_password else "auto_generated"
                
                # Validate required fields
                if not all([name, email, roll_number, class_name]):
                    failed_count += 1
                    continue
                
                # Check if class exists
                if class_name not in classes:
                    failed_count += 1
                    continue
                
                # Check if email already exists
                existing_user = User.query.filter_by(email=email).first()
                if existing_user:
                    failed_count += 1
                    continue
                
                # Check if roll number already exists in the same class
                existing_roll = User.query.filter_by(
                    roll_number=roll_number, 
                    class_id=classes[class_name]
                ).first()
                if existing_roll:
                    failed_count += 1
                    continue
                
                password_hash = generate_password_hash(password)
                
                # Create user
                user = User(
                    name=name,
                    email=email,
                    password_hash=password_hash,
                    role='student',
                    roll_number=roll_number,
                    class_id=classes[class_name],
                    status='Active'
                )
                
                db.session.add(user)
                db.session.flush()  # Get user ID for logging
                
                # Log password creation
                log_password_change(user.id, "created", method, f"Bulk upload - student account created")
                
                imported_count += 1
                
            except Exception:
                failed_count += 1
                continue
        
        if imported_count > 0:
            db.session.commit()
            flash(f'Successfully imported {imported_count} students!', 'success')
            if failed_count > 0:
                flash(f'Failed to import {failed_count} students (duplicates or invalid data)', 'warning')
        else:
            flash('No students were imported. Check your CSV format and data.', 'warning')
        
        return redirect(url_for("admin_setup"))

    def handle_bulk_student_upload(request):
        """Enhanced bulk student upload with better error handling and validation"""
        import csv
        import io
        import random
        import string
        from werkzeug.security import generate_password_hash
        
        def generate_password(length=8):
            characters = string.ascii_letters + string.digits
            return ''.join(random.choice(characters) for _ in range(length))
        
        file = request.files['csv_file']
        default_password = request.form.get('default_password', '').strip()
        
        if file.filename == '':
            flash('No file selected', 'warning')
            return redirect(url_for("manage_students_advanced"))
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file', 'warning')
            return redirect(url_for("manage_students_advanced"))
        
        try:
            # Read CSV content
            content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            # Validate required columns
            required_columns = ['name', 'email', 'roll_number', 'class_name']
            missing_columns = [col for col in required_columns if col not in csv_reader.fieldnames]
            
            if missing_columns:
                flash(f'Missing required columns: {", ".join(missing_columns)}', 'danger')
                return redirect(url_for("manage_students_advanced"))
            
            # Get available classes
            classes = {class_obj.name: class_obj.id for class_obj in ClassModel.query.all()}
            
            imported_count = 0
            failed_count = 0
            errors = []
            
            # Reset file pointer
            file.seek(0)
            content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because of header
                try:
                    name = row['name'].strip()
                    email = row['email'].strip().lower()
                    roll_number = row['roll_number'].strip()
                    class_name = row['class_name'].strip()
                    
                    # Validate required fields
                    if not all([name, email, roll_number, class_name]):
                        errors.append(f"Row {row_num}: Missing required fields")
                        failed_count += 1
                        continue
                    
                    # Validate email format
                    if '@' not in email or '.' not in email.split('@')[1]:
                        errors.append(f"Row {row_num}: Invalid email format - {email}")
                        failed_count += 1
                        continue
                    
                    # Check if class exists
                    if class_name not in classes:
                        errors.append(f"Row {row_num}: Class '{class_name}' does not exist")
                        failed_count += 1
                        continue
                    
                    # Check if email already exists
                    existing_user = User.query.filter_by(email=email).first()
                    if existing_user:
                        errors.append(f"Row {row_num}: Email '{email}' already exists")
                        failed_count += 1
                        continue
                    
                    # Check if roll number already exists in the same class
                    existing_roll = User.query.filter_by(
                        roll_number=roll_number, 
                        class_id=classes[class_name]
                    ).first()
                    if existing_roll:
                        errors.append(f"Row {row_num}: Roll number '{roll_number}' already exists in class '{class_name}'")
                        failed_count += 1
                        continue
                    
                    # Generate password
                    password = default_password if default_password else generate_password()
                    password_hash = generate_password_hash(password)
                    
                    # Create user
                    user = User(
                        name=name,
                        email=email,
                        password_hash=password_hash,
                        role='student',
                        roll_number=roll_number,
                        class_id=classes[class_name],
                        is_active=True
                    )
                    
                    db.session.add(user)
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    failed_count += 1
                    continue
            
            if imported_count > 0:
                db.session.commit()
                flash(f'Successfully imported {imported_count} students!', 'success')
            
            if failed_count > 0:
                flash(f'Failed to import {failed_count} students', 'warning')
                # Show first 5 errors
                for error in errors[:5]:
                    flash(error, 'warning')
                if len(errors) > 5:
                    flash(f'... and {len(errors) - 5} more errors', 'warning')
            
            if imported_count == 0:
                flash('No students were imported. Check your CSV format and data.', 'warning')
            
        except Exception as e:
            flash(f'Error processing CSV file: {str(e)}', 'danger')
        
        return redirect(url_for("manage_students_advanced"))

    @app.route("/admin/assign_teacher", methods=["POST"])
    def assign_teacher():
        """Assign a teacher to a class"""
        teacher_id = request.form.get("teacher_id")
        class_id = request.form.get("class_id")
        
        if not teacher_id or not class_id:
            flash("Please select both teacher and class.", "warning")
            return redirect(url_for("admin_setup"))
        
        # Check if assignment already exists
        existing = TeacherClass.query.filter_by(teacher_id=teacher_id, class_id=class_id).first()
        if existing:
            flash("Teacher is already assigned to this class.", "warning")
            return redirect(url_for("admin_setup"))
        
        teacher_class = TeacherClass(teacher_id=teacher_id, class_id=class_id)
        db.session.add(teacher_class)
        db.session.commit()
        
        flash("Teacher assigned to class successfully.", "success")
        return redirect(url_for("admin_setup"))

    @app.route("/admin/students-advanced", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def manage_students_advanced():
        """Comprehensive student management with class-based viewing"""
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "bulk_upload":
                return handle_bulk_student_upload(request)
            elif action == "add_single":
                name = request.form.get("name", "").strip()
                email = request.form.get("email", "").lower().strip()
                roll_number = request.form.get("roll_number", "").strip()
                class_id = request.form.get("class_id")
                password = request.form.get("password", "student123").strip()
                
                if not name or not email or not roll_number or not class_id:
                    flash("Please fill all required fields.", "danger")
                else:
                    # Check if email already exists
                    existing_email = User.query.filter_by(email=email).first()
                    if existing_email:
                        flash("Student with this email already exists.", "danger")
                    else:
                        # Check if roll number already exists in this class
                        existing_roll = User.query.filter_by(
                            roll_number=roll_number, class_id=class_id
                        ).first()
                        if existing_roll:
                            flash("Student with this roll number already exists in this class.", "danger")
                        else:
                            # Generate password hash
                            password_hash = generate_password_hash(password)
                            
                            # Create student
                            student = User(
                                name=name,
                                email=email,
                                password_hash=password_hash,
                                role="student",
                                roll_number=roll_number,
                                class_id=class_id,
                                status="Active",
                                is_active=True
                            )
                            db.session.add(student)
                            db.session.commit()
                            
                            flash(f"Student '{name}' added successfully to class.", "success")
                
                return redirect(url_for("view_class_students", class_id=class_id))
            elif action == "delete":
                student_id = request.form.get("student_id")
                student = User.query.get(student_id)
                if student and student.role == "student":
                    # Remove attendance records
                    Attendance.query.filter_by(user_id=student_id).delete()
                    db.session.delete(student)
                    db.session.commit()
                    flash("Student deleted successfully.", "success")
                return redirect(url_for("manage_students_advanced"))
            elif action == "bulk_delete":
                student_ids = request.form.getlist("student_ids")
                if student_ids:
                    deleted_count = 0
                    for student_id in student_ids:
                        try:
                            student = User.query.get(int(student_id))
                            if student and student.role == "student":
                                # Remove attendance records
                                Attendance.query.filter_by(user_id=student_id).delete()
                                db.session.delete(student)
                                deleted_count += 1
                        except (ValueError, AttributeError):
                            continue
                    db.session.commit()
                    flash(f"Successfully deleted {deleted_count} students.", "success")
                return redirect(url_for("manage_students_advanced"))
            elif action == "bulk_move":
                student_ids = request.form.getlist("student_ids")
                new_class_id = request.form.get("new_class_id")
                if student_ids and new_class_id:
                    moved_count = 0
                    for student_id in student_ids:
                        try:
                            student = User.query.get(int(student_id))
                            if student and student.role == "student":
                                student.class_id = int(new_class_id)
                                moved_count += 1
                        except (ValueError, AttributeError):
                            continue
                    db.session.commit()
                    flash(f"Successfully moved {moved_count} students to new class.", "success")
                return redirect(url_for("manage_students_advanced"))
        
        # Get filter parameters
        class_filter = request.args.get("class_filter", "")
        search_query = request.args.get("search", "")
        page = int(request.args.get("page", 1))
        per_page = 20
        
        # Build query
        query = User.query.filter_by(role="student")
        
        if class_filter:
            query = query.filter(User.class_id == int(class_filter))
        
        if search_query:
            query = query.filter(
                db.or_(
                    User.name.ilike(f"%{search_query}%"),
                    User.email.ilike(f"%{search_query}%"),
                    User.roll_number.ilike(f"%{search_query}%")
                )
            )
        
        # Get paginated results
        students = query.order_by(User.class_id, User.roll_number).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Get all classes for filter dropdown
        classes = ClassModel.query.order_by(ClassModel.name).all()
        
        # Get class statistics
        class_stats = {}
        for class_obj in classes:
            student_count = User.query.filter_by(role="student", class_id=class_obj.id).count()
            class_stats[class_obj.id] = student_count
        
        return render_template("admin_students.html", 
                             students=students, 
                             classes=classes, 
                             class_stats=class_stats,
                             class_filter=class_filter,
                             search_query=search_query)

    @app.route("/admin/students/class/<int:class_id>")
    @login_required
    @role_required("admin")
    def view_class_students(class_id):
        """View all students in a specific class"""
        class_obj = ClassModel.query.get_or_404(class_id)
        students = User.query.filter_by(role="student", class_id=class_id).order_by(User.roll_number).all()
        
        # Get class statistics
        total_students = len(students)
        active_students = len([s for s in students if s.is_active])
        
        return render_template("admin_class_students.html", 
                             class_obj=class_obj, 
                             students=students,
                             total_students=total_students,
                             active_students=active_students)

    @app.route("/admin/students/export")
    @login_required
    @role_required("admin")
    def export_students():
        """Export students to CSV"""
        import csv
        import io
        
        class_filter = request.args.get("class_filter", "")
        search_query = request.args.get("search", "")
        
        # Build query
        query = User.query.filter_by(role="student")
        
        if class_filter:
            query = query.filter(User.class_id == int(class_filter))
        
        if search_query:
            query = query.filter(
                db.or_(
                    User.name.ilike(f"%{search_query}%"),
                    User.email.ilike(f"%{search_query}%"),
                    User.roll_number.ilike(f"%{search_query}%")
                )
            )
        
        students = query.order_by(User.class_id, User.roll_number).all()
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Name', 'Email', 'Roll Number', 'Class', 'Status', 'Created Date'])
        
        # Write data
        for student in students:
            class_name = student.class_obj.name if student.class_obj else "No Class"
            status = "Active" if student.is_active else "Inactive"
            created_date = student.created_at.strftime('%Y-%m-%d') if hasattr(student, 'created_at') else "N/A"
            
            writer.writerow([
                student.name,
                student.email,
                student.roll_number or "N/A",
                class_name,
                status,
                created_date
            ])
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            as_attachment=True,
            download_name=f'students_export_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
            mimetype='text/csv'
        )

    @app.route("/admin/promotion", methods=["GET", "POST"])
    @login_required
    @role_required("admin")
    def manage_promotion():
        """Manage student promotion to next semester."""
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "promote_all":
                try:
                    # Get all active students (not alumni)
                    students = User.query.filter_by(role="student", status="Active").all()
                    
                    promotion_stats = {
                        'total_students': len(students),
                        'promoted': 0,
                        'moved_to_alumni': 0,
                        'errors': []
                    }
                    
                    for student in students:
                        if not student.class_obj:
                            promotion_stats['errors'].append(f"Student {student.name} has no class assigned")
                            continue
                            
                        current_class = student.class_obj
                        current_semester = current_class.semester.number if current_class.semester else None
                        
                        if current_semester is None:
                            promotion_stats['errors'].append(f"Student {student.name} has no semester assigned")
                            continue
                        
                        # Determine next class
                        if current_semester == 8:
                            # Move to Alumni
                            student.status = "Alumni"
                            student.class_id = None
                            promotion_stats['moved_to_alumni'] += 1
                        else:
                            # Find next semester class with same branch and division
                            next_semester = Semester.query.filter_by(number=current_semester + 1).first()
                            if not next_semester:
                                promotion_stats['errors'].append(f"Next semester {current_semester + 1} not found")
                                continue
                            
                            # Find next class with same branch and division
                            next_class = ClassModel.query.filter_by(
                                branch_id=current_class.branch_id,
                                division=current_class.division,
                                semester_id=next_semester.id
                            ).first()
                            
                            if not next_class:
                                promotion_stats['errors'].append(f"Next class not found for {current_class.name}")
                                continue
                            
                            # Update student's class
                            student.class_id = next_class.id
                            promotion_stats['promoted'] += 1
                    
                    # Commit all changes
                    db.session.commit()
                    
                    # Prepare success message
                    success_msg = f"Promotion completed! {promotion_stats['promoted']} students promoted, {promotion_stats['moved_to_alumni']} moved to Alumni."
                    if promotion_stats['errors']:
                        success_msg += f" {len(promotion_stats['errors'])} errors occurred."
                    
                    flash(success_msg, "success")
                    
                    # Log errors if any
                    if promotion_stats['errors']:
                        for error in promotion_stats['errors'][:5]:  # Show first 5 errors
                            flash(f"Error: {error}", "warning")
                        if len(promotion_stats['errors']) > 5:
                            flash(f"... and {len(promotion_stats['errors']) - 5} more errors", "warning")
                    
                except Exception as e:
                    db.session.rollback()
                    flash(f"Promotion failed: {str(e)}", "danger")
            
            return redirect(url_for("manage_promotion"))
        
        # GET request - show promotion interface
        # Get current promotion statistics
        total_students = User.query.filter_by(role="student", status="Active").count()
        alumni_students = User.query.filter_by(role="student", status="Alumni").count()
        
        # Get students by semester
        students_by_semester = {}
        for semester in Semester.query.filter_by(is_active=True).order_by(Semester.number).all():
            students_count = User.query.join(ClassModel).filter(
                User.role == "student",
                User.status == "Active",
                ClassModel.semester_id == semester.id
            ).count()
            students_by_semester[semester] = students_count
        
        return render_template("admin_promotion.html", 
                             total_students=total_students,
                             alumni_students=alumni_students,
                             students_by_semester=students_by_semester)

    @app.route("/admin/download-sample-csv")
    def download_sample_csv():
        """Download a sample CSV file for bulk student import"""
        import csv
        import io
        
        # Create sample CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['name', 'email', 'roll_number', 'class_name', 'password'])
        
        # Write sample data
        sample_data = [
            ['John Doe', 'john.doe@example.com', '2021001', '5CSE1', 'student123'],
            ['Jane Smith', 'jane.smith@example.com', '2021002', '5CSE1', ''],
            ['Bob Johnson', 'bob.johnson@example.com', '2021003', '5CSE2', 'custompass456'],
            ['Alice Brown', 'alice.brown@example.com', '2021004', '5CSE2', ''],
            ['Charlie Wilson', 'charlie.wilson@example.com', '2021005', '1CSE1', 'student789'],
            ['Diana Davis', 'diana.davis@example.com', '2021006', '1CSE1', ''],
        ]
        
        for row in sample_data:
            writer.writerow(row)
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            as_attachment=True,
            download_name='sample_students.csv',
            mimetype='text/csv'
        )

    # --------------------------
    # WiFi Network Management Routes
    # --------------------------
    @app.route("/teacher/wifi-networks", methods=["GET", "POST"])
    @login_required
    @role_required("teacher")
    def manage_wifi_networks():
        """Manage WiFi networks for attendance verification"""
        if request.method == "POST":
            action = request.form.get("action")
            
            if action == "add":
                name = request.form.get("name", "").strip()
                router_ip = request.form.get("router_ip", "").strip()
                subnet_mask = request.form.get("subnet_mask", "").strip()
                
                if not name or not router_ip:
                    flash("Name and Router IP are required.", "danger")
                    return redirect(url_for("manage_wifi_networks"))
                
                # Validate IP address
                try:
                    ipaddress.ip_address(router_ip)
                except ValueError:
                    flash("Invalid router IP address format.", "danger")
                    return redirect(url_for("manage_wifi_networks"))
                
                # Validate subnet mask if provided
                if subnet_mask:
                    try:
                        if subnet_mask.startswith('/'):
                            ipaddress.ip_network(f"{router_ip}{subnet_mask}", strict=False)
                        else:
                            ipaddress.ip_network(f"{router_ip}/{subnet_mask}", strict=False)
                    except ValueError:
                        flash("Invalid subnet mask format.", "danger")
                        return redirect(url_for("manage_wifi_networks"))
                
                # Check for duplicate router IP
                existing = WiFiNetwork.query.filter_by(router_ip=router_ip).first()
                if existing:
                    flash("A WiFi network with this router IP already exists.", "warning")
                    return redirect(url_for("manage_wifi_networks"))
                
                wifi_network = WiFiNetwork(
                    name=name,
                    router_ip=router_ip,
                    subnet_mask=subnet_mask if subnet_mask else None,
                    created_by=current_user.id
                )
                db.session.add(wifi_network)
                db.session.commit()
                
                flash(f"WiFi network '{name}' added successfully.", "success")
                return redirect(url_for("manage_wifi_networks"))
            
            elif action == "toggle":
                wifi_id = request.form.get("wifi_id")
                try:
                    wifi_network = WiFiNetwork.query.get(int(wifi_id))
                    if wifi_network and wifi_network.created_by == current_user.id:
                        wifi_network.is_active = not wifi_network.is_active
                        db.session.commit()
                        status = "activated" if wifi_network.is_active else "deactivated"
                        flash(f"WiFi network '{wifi_network.name}' {status}.", "success")
                    else:
                        flash("WiFi network not found or access denied.", "danger")
                except (ValueError, AttributeError):
                    flash("Invalid WiFi network ID.", "danger")
                return redirect(url_for("manage_wifi_networks"))
            
            elif action == "delete":
                wifi_id = request.form.get("wifi_id")
                try:
                    wifi_network = WiFiNetwork.query.get(int(wifi_id))
                    if wifi_network and wifi_network.created_by == current_user.id:
                        db.session.delete(wifi_network)
                        db.session.commit()
                        flash(f"WiFi network '{wifi_network.name}' deleted.", "success")
                    else:
                        flash("WiFi network not found or access denied.", "danger")
                except (ValueError, AttributeError):
                    flash("Invalid WiFi network ID.", "danger")
                return redirect(url_for("manage_wifi_networks"))
        
        # Get WiFi networks created by this teacher
        wifi_networks = WiFiNetwork.query.filter_by(created_by=current_user.id).order_by(WiFiNetwork.created_at.desc()).all()
        return render_template("wifi_networks.html", wifi_networks=wifi_networks)

    @app.route("/teacher/wifi-test", methods=["POST"])
    @login_required
    @role_required("teacher")
    def test_wifi_connection():
        """Test current WiFi connection against configured networks"""
        client_ip = get_client_ip()
        is_on_wifi, wifi_network = is_on_configured_wifi(client_ip)
        
        if is_on_wifi:
            return jsonify({
                "ok": True,
                "message": f"Connected to WiFi: {wifi_network.name} (Router: {wifi_network.router_ip})",
                "wifi_network": {
                    "name": wifi_network.name,
                    "router_ip": wifi_network.router_ip,
                    "subnet_mask": wifi_network.subnet_mask
                }
            })
        else:
            return jsonify({
                "ok": False,
                "message": f"Not connected to any configured WiFi network. Your IP: {client_ip}",
                "client_ip": client_ip
            })

    @app.route("/student/wifi-status", methods=["GET"])
    @login_required
    @role_required("student")
    def student_wifi_status():
        """Check student's WiFi connection status"""
        client_ip = get_client_ip()
        is_on_wifi, wifi_network = is_on_configured_wifi(client_ip)
        
        if is_on_wifi:
            return jsonify({
                "ok": True,
                "message": f"Connected to campus WiFi: {wifi_network.name}",
                "wifi_network": {
                    "name": wifi_network.name,
                    "router_ip": wifi_network.router_ip
                }
            })
        else:
            return jsonify({
                "ok": False,
                "message": f"Not connected to campus WiFi. Your IP: {client_ip}",
                "client_ip": client_ip
            })

    return app


# Create app instance for WSGI servers like gunicorn
app = create_app()

# Enable running with `python app.py`
if __name__ == "__main__":
    # Use 0.0.0.0 to be accessible on LAN if needed
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)


