from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from backend.database import db
from backend.models import User, Role, Employee, Department, Attendance, LeaveRequest, Payroll, AuditLog, Notification
from backend.auth import generate_jwt_token, login_required, role_required, token_required, decode_jwt_token
from backend.services.audit_service import log_action
from backend.services.email_service import send_password_reset_email
from datetime import datetime, date
import uuid

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard_view'))
    return redirect(url_for('auth.login_view'))

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup_view():
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard_view'))
        
    departments = Department.query.all()
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        gender = request.form.get('gender')
        mobile = request.form.get('mobile_number')
        dept_id = request.form.get('department_id')
        designation = request.form.get('designation', 'Associate')
        
        if not email or not password or not first_name or not last_name:
            flash('Please fill in all required fields.', 'danger')
            return render_template('signup.html', departments=departments)
            
        # Check if already exists
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('signup.html', departments=departments)
            
        # Get Employee role
        role = Role.query.filter_by(name='Employee').first()
        if not role:
            flash('System roles are not initialized.', 'danger')
            return render_template('signup.html', departments=departments)
            
        # Create User
        user = User(email=email, role_id=role.id, is_active=True, email_verified=False)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        # Import generate_employee_id
        from backend.routes.employee_routes import generate_employee_id
        emp_code = generate_employee_id()
        
        # Create Employee profile
        emp = Employee(
            user_id=user.id,
            employee_id=emp_code,
            first_name=first_name,
            last_name=last_name,
            email=email,
            gender=gender,
            mobile_number=mobile,
            department_id=int(dept_id) if dept_id else None,
            designation=designation,
            salary=50000.00, # default starting salary
            joining_date=date.today(),
            profile_photo='uploads/profiles/default.png',
            employment_type='Full-Time',
            active_status=True
        )
        db.session.add(emp)
        db.session.commit()
        
        log_action("Self-registered as a new Employee", user.id)
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('auth.login_view'))
        
    return render_template('signup.html', departments=departments)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login_view():
    if 'user_id' in session:
        return redirect(url_for('auth.dashboard_view'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account is deactivated.', 'danger')
                return render_template('login.html')
                
            session['user_id'] = user.id
            session['role_name'] = user.role.name
            session['email'] = user.email
            session['jwt_token'] = generate_jwt_token(user)
            if user.employee:
                session['employee_id'] = user.employee.id
                session['employee_code'] = user.employee.employee_id
                session['full_name'] = user.employee.full_name
                session['profile_photo'] = user.employee.profile_photo or 'uploads/profiles/default.png'
            else:
                session['employee_id'] = None
                session['full_name'] = "Super Admin"
                session['profile_photo'] = 'uploads/profiles/default.png'
                
            if remember:
                session.permanent = True
            else:
                session.permanent = False
                
            log_action("Logged in successfully", user.id)
            flash('Welcome to Enterprise EMS!', 'success')
            return redirect(url_for('auth.dashboard_view'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout_view():
    user_id = session.get('user_id')
    if user_id:
        log_action("Logged out", user_id)
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login_view'))

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password_view():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # Generate a temporary token for password reset
            reset_token = str(uuid.uuid4())
            session[f'reset_token_{reset_token}'] = user.id
            send_password_reset_email(user.email, reset_token)
            log_action("Requested password reset link", user.id)
        flash('If the email exists, a password reset link has been sent.', 'info')
        return redirect(url_for('auth.login_view'))
    return render_template('forgot_password.html')

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password_view():
    token = request.args.get('token') or request.form.get('token')
    if not token or f'reset_token_{token}' not in session:
        flash('Invalid or expired reset token.', 'danger')
        return redirect(url_for('auth.login_view'))
        
    user_id = session[f'reset_token_{token}']
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('reset_password.html', token=token)
            
        user.set_password(password)
        db.session.commit()
        
        session.pop(f'reset_token_{token}')
        log_action("Reset password successfully", user.id)
        flash('Your password has been reset successfully. Please login.', 'success')
        return redirect(url_for('auth.login_view'))
        
    return render_template('reset_password.html', token=token)

@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    user = User.query.get(session['user_id'])
    if not user.check_password(current_password):
        flash('Incorrect current password.', 'danger')
        return redirect(request.referrer)
        
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(request.referrer)
        
    user.set_password(new_password)
    db.session.commit()
    log_action("Changed password", user.id)
    flash('Password changed successfully.', 'success')
    return redirect(request.referrer)

@auth_bp.route('/dashboard')
@login_required
def dashboard_view():
    # Gather counts and metrics
    total_emp = Employee.query.count()
    active_emp = Employee.query.filter_by(active_status=True).count()
    inactive_emp = total_emp - active_emp
    dept_count = Department.query.count()
    
    # Today's attendance
    today = date.today()
    today_present = Attendance.query.filter_by(date=today, status='Present').count()
    today_absent = Attendance.query.filter_by(date=today, status='Absent').count()
    today_leave = Attendance.query.filter_by(date=today, status='Leave').count()
    
    # Pending leave requests
    pending_leaves = LeaveRequest.query.filter_by(status='Pending').count()
    
    # Gather lists for HR & Management view
    active_list = Employee.query.filter_by(active_status=True).all()
    inactive_list = Employee.query.filter_by(active_status=False).all()
    
    # Newly joined (within last 30 days)
    thirty_days_ago = date.today() - timedelta(days=30)
    new_list = Employee.query.filter(Employee.joining_date >= thirty_days_ago).all()
    
    # Calculate total annual CTC (Annual Salary sum)
    total_ctc = sum(float(emp.salary or 0.0) * 12 for emp in active_list)

    # Render dashboard based on role
    return render_template(
        'dashboard.html',
        total_employees=total_emp,
        active_employees=active_emp,
        inactive_employees=inactive_emp,
        departments_count=dept_count,
        today_present=today_present,
        today_absent=today_absent,
        today_leave=today_leave,
        pending_leaves=pending_leaves,
        active_list=active_list,
        inactive_list=inactive_list,
        new_list=new_list,
        total_ctc=total_ctc
    )

# ----------------- stateless REST API endpoints -----------------

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'message': 'Missing email or password'}), 400
        
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        if not user.is_active:
            return jsonify({'message': 'User account is deactivated'}), 403
            
        token = generate_jwt_token(user)
        log_action("Logged in via API", user.id)
        
        return jsonify({
            'token': token,
            'user': user.to_dict()
        }), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    # JWT is stateless, so client deletes token. We just log audit
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(" ")[1]
        decoded = decode_jwt_token(token)
        if not isinstance(decoded, str):
            log_action("Logged out via API", decoded.get('user_id'))
    return jsonify({'message': 'Logged out successfully'}), 200

@auth_bp.route('/api/notifications', methods=['GET'])
@token_required
def api_get_notifications():
    notifications = Notification.query.filter_by(user_id=request.user_id).order_by(Notification.created_at.desc()).all()
    return jsonify([n.to_dict() for n in notifications]), 200

@auth_bp.route('/api/notifications/<int:notif_id>/read', methods=['PUT'])
@token_required
def api_mark_notification_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, user_id=request.user_id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({'message': 'Notification marked as read'}), 200

@auth_bp.route('/api/dashboard/charts', methods=['GET'])
@token_required
def api_dashboard_charts():
    # 1. Department Distribution
    depts = Department.query.all()
    dept_names = [d.department_name for d in depts]
    dept_counts = [len(d.employees) for d in depts]

    # 2. Salary Distribution
    s_under_50 = Employee.query.filter(Employee.salary < 50000).count()
    s_50_80 = Employee.query.filter(Employee.salary >= 50000, Employee.salary < 80000).count()
    s_80_100 = Employee.query.filter(Employee.salary >= 80000, Employee.salary < 100000).count()
    s_100_150 = Employee.query.filter(Employee.salary >= 100000, Employee.salary < 150000).count()
    s_over_150 = Employee.query.filter(Employee.salary >= 150000).count()
    
    # 3. Gender Distribution
    males = Employee.query.filter(Employee.gender.ilike('male')).count()
    females = Employee.query.filter(Employee.gender.ilike('female')).count()
    others = Employee.query.filter(Employee.active_status == True).count() - (males + females)

    # 4. Hiring Trends (Past 6 months)
    # Simple month list helper
    today = date.today()
    hiring_labels = []
    hiring_values = []
    for i in range(5, -1, -1):
        target_date = today - timedelta(days=i*30)
        lbl = target_date.strftime("%B")
        hiring_labels.append(lbl)
        # Query count of joins in this month
        cnt = Employee.query.filter(
            func.strftime('%Y', Employee.joining_date) == str(target_date.year),
            func.strftime('%m', Employee.joining_date) == f"{target_date.month:02d}"
        ).count()
        hiring_values.append(cnt)

    return jsonify({
        'department': {
            'labels': dept_names,
            'values': dept_counts
        },
        'salary': {
            'labels': ['Under 50k', '50k - 80k', '80k - 100k', '100k - 150k', '150k+'],
            'values': [s_under_50, s_50_80, s_80_100, s_100_150, s_over_150]
        },
        'gender': {
            'labels': ['Male', 'Female', 'Other'],
            'values': [males, females, max(0, others)]
        },
        'hiring': {
            'labels': hiring_labels,
            'values': hiring_values
        }
    }), 200

