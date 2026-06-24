from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from backend.database import db

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    
    users = db.relationship('User', backref='role', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee = db.relationship('Employee', backref='user', uselist=False, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade="all, delete-orphan")
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'role_id': self.role_id,
            'role_name': self.role.name if self.role else None,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'employee_id': self.employee.id if self.employee else None
        }

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    department_name = db.Column(db.String(100), unique=True, nullable=False)
    department_head_id = db.Column(db.Integer, db.ForeignKey('employees.id', use_alter=True, name='fk_dept_head_id'), nullable=True)
    description = db.Column(db.Text)
    budget = db.Column(db.Numeric(12, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employees = db.relationship('Employee', backref='department', foreign_keys='Employee.department_id', lazy=True)

    def to_dict(self):
        head = Employee.query.get(self.department_head_id) if self.department_head_id else None
        return {
            'id': self.id,
            'department_name': self.department_name,
            'department_head_id': self.department_head_id,
            'department_head_name': f"{head.first_name} {head.last_name}" if head else "Not Assigned",
            'description': self.description,
            'budget': float(self.budget) if self.budget else 0.0,
            'employee_count': len(self.employees) if self.employees else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile_number = db.Column(db.String(20))
    emergency_contact = db.Column(db.String(20))
    gender = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    blood_group = db.Column(db.String(10))
    marital_status = db.Column(db.String(20))
    address = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    designation = db.Column(db.String(100))
    salary = db.Column(db.Numeric(12, 2), default=0.00)
    joining_date = db.Column(db.Date)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    profile_photo = db.Column(db.String(255))
    aadhaar_number = db.Column(db.String(20))
    pan_number = db.Column(db.String(20))
    employment_type = db.Column(db.String(50)) # Full-Time, Part-Time, Contract, Intern
    active_status = db.Column(db.Boolean, default=True)

    # Relationships
    attendance_records = db.relationship('Attendance', backref='employee', lazy=True, cascade="all, delete-orphan")
    leave_requests = db.relationship('LeaveRequest', backref='employee', foreign_keys='LeaveRequest.employee_id', lazy=True, cascade="all, delete-orphan")
    payrolls = db.relationship('Payroll', backref='employee', lazy=True, cascade="all, delete-orphan")
    performance_reviews = db.relationship('PerformanceReview', backref='employee', foreign_keys='PerformanceReview.employee_id', lazy=True, cascade="all, delete-orphan")
    documents = db.relationship('Document', backref='employee', lazy=True, cascade="all, delete-orphan")
    subordinates = db.relationship('Employee', backref=db.backref('manager', remote_side=[id]), lazy=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        manager = Employee.query.get(self.manager_id) if self.manager_id else None
        return {
            'id': self.id,
            'user_id': self.user_id,
            'employee_id': self.employee_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'email': self.email,
            'mobile_number': self.mobile_number,
            'emergency_contact': self.emergency_contact,
            'gender': self.gender,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'blood_group': self.blood_group,
            'marital_status': self.marital_status,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'postal_code': self.postal_code,
            'department_id': self.department_id,
            'department_name': self.department.department_name if self.department else None,
            'designation': self.designation,
            'salary': float(self.salary) if self.salary else 0.0,
            'joining_date': self.joining_date.isoformat() if self.joining_date else None,
            'manager_id': self.manager_id,
            'manager_name': manager.full_name if manager else "None",
            'profile_photo': self.profile_photo,
            'aadhaar_number': self.aadhaar_number,
            'pan_number': self.pan_number,
            'employment_type': self.employment_type,
            'active_status': self.active_status,
            'role_name': self.user.role.name if self.user and self.user.role else None
        }

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.Time, nullable=False)
    check_out = db.Column(db.Time)
    working_hours = db.Column(db.Numeric(4, 2), default=0.00)
    overtime_hours = db.Column(db.Numeric(4, 2), default=0.00)
    status = db.Column(db.String(20), nullable=False) # Present, Absent, Half Day, Leave, Holiday

    def to_dict(self):
        emp = Employee.query.get(self.employee_id)
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': emp.full_name if emp else None,
            'employee_code': emp.employee_id if emp else None,
            'date': self.date.isoformat() if self.date else None,
            'check_in': self.check_in.strftime('%H:%M:%S') if self.check_in else None,
            'check_out': self.check_out.strftime('%H:%M:%S') if self.check_out else None,
            'working_hours': float(self.working_hours) if self.working_hours else 0.0,
            'overtime_hours': float(self.overtime_hours) if self.overtime_hours else 0.0,
            'status': self.status
        }

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False) # Casual Leave, Sick Leave, Paid Leave, Maternity Leave, Emergency Leave
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending') # Pending, Approved, Rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        emp = Employee.query.get(self.employee_id)
        approver = Employee.query.get(self.approved_by) if self.approved_by else None
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': emp.full_name if emp else None,
            'employee_code': emp.employee_id if emp else None,
            'leave_type': self.leave_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'duration_days': (self.end_date - self.start_date).days + 1,
            'reason': self.reason,
            'status': self.status,
            'approved_by': self.approved_by,
            'approved_by_name': approver.full_name if approver else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Payroll(db.Model):
    __tablename__ = 'payroll'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    basic_salary = db.Column(db.Numeric(12, 2), default=0.00)
    hra = db.Column(db.Numeric(12, 2), default=0.00)
    bonus = db.Column(db.Numeric(12, 2), default=0.00)
    incentives = db.Column(db.Numeric(12, 2), default=0.00)
    deductions = db.Column(db.Numeric(12, 2), default=0.00)
    tax = db.Column(db.Numeric(12, 2), default=0.00)
    net_salary = db.Column(db.Numeric(12, 2), default=0.00)
    payslip_path = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Pending') # Pending, Paid
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        emp = Employee.query.get(self.employee_id)
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': emp.full_name if emp else None,
            'employee_code': emp.employee_id if emp else None,
            'month': self.month,
            'year': self.year,
            'basic_salary': float(self.basic_salary) if self.basic_salary else 0.0,
            'hra': float(self.hra) if self.hra else 0.0,
            'bonus': float(self.bonus) if self.bonus else 0.0,
            'incentives': float(self.incentives) if self.incentives else 0.0,
            'deductions': float(self.deductions) if self.deductions else 0.0,
            'tax': float(self.tax) if self.tax else 0.0,
            'net_salary': float(self.net_salary) if self.net_salary else 0.0,
            'payslip_path': self.payslip_path,
            'status': self.status,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None
        }

class PerformanceReview(db.Model):
    __tablename__ = 'performance_reviews'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    review_period = db.Column(db.String(50), nullable=False) # Monthly, Quarterly, Annual
    rating = db.Column(db.Integer, nullable=False) # 1 to 5
    goal_achievement = db.Column(db.Numeric(5, 2), default=0.00) # Percentage
    manager_feedback = db.Column(db.Text)
    employee_feedback = db.Column(db.Text)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    reviewer = db.relationship('Employee', foreign_keys=[reviewer_id])

    def to_dict(self):
        emp = Employee.query.get(self.employee_id)
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': emp.full_name if emp else None,
            'employee_code': emp.employee_id if emp else None,
            'review_period': self.review_period,
            'rating': self.rating,
            'goal_achievement': float(self.goal_achievement) if self.goal_achievement else 0.0,
            'manager_feedback': self.manager_feedback,
            'employee_feedback': self.employee_feedback,
            'reviewer_id': self.reviewer_id,
            'reviewer_name': self.reviewer.full_name if self.reviewer else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    notification_type = db.Column(db.String(50)) # leave, payroll, system, info
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'notification_type': self.notification_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    document_name = db.Column(db.String(100), nullable=False)
    document_type = db.Column(db.String(50), nullable=False) # Resume, Certificate, Offer Letter, ID Proof, Experience Letter
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'document_name': self.document_name,
            'document_type': self.document_type,
            'file_path': self.file_path,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        user = User.query.get(self.user_id) if self.user_id else None
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_email': user.email if user else 'Anonymous',
            'action': self.action,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
