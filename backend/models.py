from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from backend.database import db

class HRUser(db.Model):
    __tablename__ = 'hr_users'
    id = db.Model.metadata.tables.get('hr_users') # Helper reference
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    department_name = db.Column(db.String(100), unique=True, nullable=False)
    department_head_id = db.Column(db.Integer, db.ForeignKey('employees.id', use_alter=True, name='fk_dept_head_id_hr'), nullable=True)
    description = db.Column(db.Text)
    budget = db.Column(db.Numeric(12, 2), default=0.00)

    employees = db.relationship('Employee', backref='department', foreign_keys='Employee.department_id', lazy=True)

    def to_dict(self):
        head = Employee.query.get(self.department_head_id) if self.department_head_id else None
        return {
            'id': self.id,
            'department_name': self.department_name,
            'department_head_id': self.department_head_id,
            'department_head_name': head.full_name if head else "Unassigned",
            'description': self.description,
            'budget': float(self.budget) if self.budget else 0.0,
            'employee_count': len(self.employees) if self.employees else 0
        }

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20))
    gender = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    designation = db.Column(db.String(100))
    salary = db.Column(db.Numeric(12, 2), default=0.00) # Monthly salary
    joining_date = db.Column(db.Date)
    reporting_manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    address = db.Column(db.Text)
    emergency_contact = db.Column(db.String(20))
    profile_photo = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Active') # Active, Inactive

    # Relationships
    attendance_records = db.relationship('Attendance', backref='employee', lazy=True, cascade="all, delete-orphan")
    leave_requests = db.relationship('LeaveRequest', backref='employee', foreign_keys='LeaveRequest.employee_id', lazy=True, cascade="all, delete-orphan")
    payrolls = db.relationship('Payroll', backref='employee', lazy=True, cascade="all, delete-orphan")
    documents = db.relationship('EmployeeDocument', backref='employee', lazy=True, cascade="all, delete-orphan")
    performance_reviews = db.relationship('PerformanceReview', backref='employee', foreign_keys='PerformanceReview.employee_id', lazy=True, cascade="all, delete-orphan")
    subordinates = db.relationship('Employee', backref=db.backref('manager', remote_side=[id]), lazy=True)

    def to_dict(self):
        manager = Employee.query.get(self.reporting_manager_id) if self.reporting_manager_id else None
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'full_name': self.full_name,
            'email': self.email,
            'phone_number': self.phone_number,
            'gender': self.gender,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'department_id': self.department_id,
            'department_name': self.department.department_name if self.department else None,
            'designation': self.designation,
            'salary': float(self.salary) if self.salary else 0.0,
            'joining_date': self.joining_date.isoformat() if self.joining_date else None,
            'reporting_manager_id': self.reporting_manager_id,
            'manager_name': manager.full_name if manager else "None",
            'address': self.address,
            'emergency_contact': self.emergency_contact,
            'profile_photo': self.profile_photo or 'uploads/profiles/default.png',
            'status': self.status
        }

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.Time)
    check_out = db.Column(db.Time)
    status = db.Column(db.String(20), nullable=False) # Present, Absent, Half Day, Leave
    working_hours = db.Column(db.Numeric(4, 2), default=0.00)
    overtime_hours = db.Column(db.Numeric(4, 2), default=0.00)

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
    leave_type = db.Column(db.String(50), nullable=False) # Casual Leave, Sick Leave, Paid Leave, Emergency Leave
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending') # Pending, Approved, Rejected

    def to_dict(self):
        emp = Employee.query.get(self.employee_id)
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
            'status': self.status
        }

class Payroll(db.Model):
    __tablename__ = 'payroll'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    basic_salary = db.Column(db.Numeric(12, 2), default=0.00)
    allowances = db.Column(db.Numeric(12, 2), default=0.00)
    bonuses = db.Column(db.Numeric(12, 2), default=0.00)
    deductions = db.Column(db.Numeric(12, 2), default=0.00)
    net_salary = db.Column(db.Numeric(12, 2), default=0.00)
    payslip_path = db.Column(db.String(255))

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
            'allowances': float(self.allowances) if self.allowances else 0.0,
            'bonuses': float(self.bonuses) if self.bonuses else 0.0,
            'deductions': float(self.deductions) if self.deductions else 0.0,
            'net_salary': float(self.net_salary) if self.net_salary else 0.0,
            'payslip_path': self.payslip_path
        }

class EmployeeDocument(db.Model):
    __tablename__ = 'employee_documents'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    document_name = db.Column(db.String(100), nullable=False)
    document_type = db.Column(db.String(50), nullable=False) # Resume, Aadhaar, PAN Card, Certificates, Offer Letter, Experience Letter
    file_path = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'document_name': self.document_name,
            'document_type': self.document_type,
            'file_path': self.file_path
        }

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class PerformanceReview(db.Model):
    __tablename__ = 'performance_reviews'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    review_period = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    goal_achievement = db.Column(db.Float, default=0.0)
    manager_feedback = db.Column(db.Text)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    employee_feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        emp = Employee.query.get(self.employee_id)
        reviewer = Employee.query.get(self.reviewer_id) if self.reviewer_id else None
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'employee_name': emp.full_name if emp else None,
            'employee_code': emp.employee_id if emp else None,
            'review_period': self.review_period,
            'rating': self.rating,
            'goal_achievement': self.goal_achievement,
            'manager_feedback': self.manager_feedback,
            'reviewer_id': self.reviewer_id,
            'reviewer_name': reviewer.full_name if reviewer else "System Admin",
            'employee_feedback': self.employee_feedback,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('hr_users.id'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
