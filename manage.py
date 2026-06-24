import os
import shutil
import sys
from datetime import datetime, date, time, timedelta
from app import app
from backend.database import db
from backend.models import Role, User, Department, Employee, Attendance, LeaveRequest, Payroll, PerformanceReview, AuditLog, Notification

def seed_database():
    """Seed database with roles, sample departments, employees, and operations history"""
    print("Seeding database...")
    
    # 1. Create Roles
    roles = {
        'Super Admin': 'Full system administration capabilities.',
        'HR Manager': 'Employee directory, departments, leaves, attendance, and payroll management.',
        'Team Lead': 'View team roster, review leave requests, and write performance appraisals.',
        'Employee': 'View own profile, check-in/out, request leaves, and download payslips.'
    }
    
    role_objs = {}
    for name, desc in roles.items():
        role = Role.query.filter_by(name=name).first()
        if not role:
            role = Role(name=name, description=desc)
            db.session.add(role)
        role_objs[name] = role
    db.session.flush()

    # 2. Create Users
    users_data = [
        ('admin@enterprise.com', 'Admin@123', 'Super Admin'),
        ('hr@enterprise.com', 'Hr@123', 'HR Manager'),
        ('lead@enterprise.com', 'Lead@123', 'Team Lead'),
        ('emp@enterprise.com', 'Emp@123', 'Employee'),
    ]
    
    user_objs = {}
    for email, passwd, role_name in users_data:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(
                email=email,
                role_id=role_objs[role_name].id,
                is_active=True,
                email_verified=True
            )
            user.set_password(passwd)
            db.session.add(user)
        user_objs[role_name] = user
    db.session.flush()

    # 3. Create Departments
    departments = [
        ('Human Resources', 1200000.00, 'Responsible for sourcing, screening, and managing talent.'),
        ('Engineering', 4500000.00, 'Product design, coding, software maintenance, and deployment.'),
        ('Sales & Marketing', 2200000.00, 'Customer acquisition, lead generation, and corporate branding.'),
        ('Finance', 1500000.00, 'Accounting, tax audits, payroll processing, and budget control.')
    ]
    
    dept_objs = {}
    for name, budget, desc in departments:
        dept = Department.query.filter_by(department_name=name).first()
        if not dept:
            dept = Department(
                department_name=name,
                budget=budget,
                description=desc
            )
            db.session.add(dept)
        dept_objs[name] = dept
    db.session.flush()

    # 4. Create Employee Records
    employees_data = [
        ('hr@enterprise.com', 'EMP1001', 'Jane', 'Doe', 'HR Specialist', 'Human Resources', 80000.00, 'Male', None),
        ('lead@enterprise.com', 'EMP1002', 'Bob', 'Smith', 'Engineering Lead', 'Engineering', 120000.00, 'Male', None),
        ('emp@enterprise.com', 'EMP1003', 'John', 'Doe', 'Software Engineer', 'Engineering', 90000.00, 'Male', 'EMP1002'),
    ]

    emp_objs = {}
    for email, emp_code, first, last, desg, dept_name, salary, gender, mgr_code in employees_data:
        emp = Employee.query.filter_by(email=email).first()
        if not emp:
            # Resolve manager id
            mgr_id = None
            if mgr_code:
                mgr = Employee.query.filter_by(employee_id=mgr_code).first()
                if mgr:
                    mgr_id = mgr.id
                    
            # Resolve user_id mapping
            u_id = None
            if email == 'hr@enterprise.com': u_id = user_objs['HR Manager'].id
            elif email == 'lead@enterprise.com': u_id = user_objs['Team Lead'].id
            elif email == 'emp@enterprise.com': u_id = user_objs['Employee'].id

            emp = Employee(
                user_id=u_id,
                employee_id=emp_code,
                first_name=first,
                last_name=last,
                email=email,
                mobile_number='9876543210',
                emergency_contact='9012345678',
                gender=gender,
                date_of_birth=date(1990, 5, 12),
                blood_group='O+',
                marital_status='Married',
                address='Flat 405, Block B, Tech Hub Appts',
                city='Bangalore',
                state='Karnataka',
                country='India',
                postal_code='560103',
                department_id=dept_objs[dept_name].id,
                designation=desg,
                salary=salary,
                joining_date=date(2024, 1, 15),
                manager_id=mgr_id,
                profile_photo='uploads/profiles/default.png',
                employment_type='Full-Time',
                active_status=True
            )
            db.session.add(emp)
        emp_objs[emp_code] = emp
    db.session.flush()

    # Assign Department Heads
    dept_objs['Human Resources'].department_head_id = emp_objs['EMP1001'].id
    dept_objs['Engineering'].department_head_id = emp_objs['EMP1002'].id
    db.session.flush()

    # 5. Seed Attendance Logs (Previous 14 days)
    john = emp_objs['EMP1003']
    bob = emp_objs['EMP1002']
    jane = emp_objs['EMP1001']
    
    today = date.today()
    for i in range(1, 15):
        log_date = today - timedelta(days=i)
        if log_date.weekday() >= 5:
            # Weekend holiday
            continue
            
        # Jane (HR Manager)
        if not Attendance.query.filter_by(employee_id=jane.id, date=log_date).first():
            db.session.add(Attendance(
                employee_id=jane.id, date=log_date,
                check_in=time(9, 5, 0), check_out=time(17, 30, 0),
                working_hours=8.0, overtime_hours=0.4, status='Present'
            ))
            
        # Bob (Lead)
        if not Attendance.query.filter_by(employee_id=bob.id, date=log_date).first():
            db.session.add(Attendance(
                employee_id=bob.id, date=log_date,
                check_in=time(8, 55, 0), check_out=time(18, 15, 0),
                working_hours=8.0, overtime_hours=1.3, status='Present'
            ))

        # John (Employee)
        if not Attendance.query.filter_by(employee_id=john.id, date=log_date).first():
            # Standard present day, one day sick leave, one half day
            if i == 5:
                # Sick leave
                db.session.add(Attendance(
                    employee_id=john.id, date=log_date,
                    check_in=time(9, 0, 0), check_out=time(9, 0, 0),
                    working_hours=0.0, overtime_hours=0.0, status='Leave'
                ))
            elif i == 9:
                # Half Day
                db.session.add(Attendance(
                    employee_id=john.id, date=log_date,
                    check_in=time(13, 0, 0), check_out=time(17, 0, 0),
                    working_hours=4.0, overtime_hours=0.0, status='Half Day'
                ))
            else:
                db.session.add(Attendance(
                    employee_id=john.id, date=log_date,
                    check_in=time(9, 10, 0), check_out=time(17, 45, 0),
                    working_hours=8.0, overtime_hours=0.5, status='Present'
                ))

    # 6. Seed Leave Requests
    leave_reqs = [
        (john.id, 'Sick Leave', today - timedelta(days=5), today - timedelta(days=5), 'Had a bad flu', 'Approved', bob.id),
        (john.id, 'Casual Leave', today + timedelta(days=10), today + timedelta(days=11), 'Going out of town', 'Pending', None),
        (john.id, 'Paid Leave', today - timedelta(days=30), today - timedelta(days=28), 'Family wedding', 'Approved', bob.id)
    ]
    for e_id, l_type, start, end, reason, status, app_by in leave_reqs:
        existing = LeaveRequest.query.filter_by(employee_id=e_id, start_date=start).first()
        if not existing:
            db.session.add(LeaveRequest(
                employee_id=e_id, leave_type=l_type, start_date=start, end_date=end,
                reason=reason, status=status, approved_by=app_by
            ))

    # 7. Seed Performance Review
    if not PerformanceReview.query.filter_by(employee_id=john.id).first():
        db.session.add(PerformanceReview(
            employee_id=john.id,
            review_period='Quarterly',
            rating=4,
            goal_achievement=95.5,
            manager_feedback='John is performing very well. He completed the backend API migration ahead of schedule.',
            employee_feedback='I enjoyed working on the migration. Hoping to lead some projects in the next quarter.',
            reviewer_id=bob.id
        ))

    # 8. Seed Payroll (Calculations for last month)
    last_month_date = today - timedelta(days=30)
    month = last_month_date.month
    year = last_month_date.year
    
    staff = [jane, bob, john]
    for s in staff:
        existing = Payroll.query.filter_by(employee_id=s.id, month=month, year=year).first()
        if not existing:
            basic = float(s.salary) * 0.50
            hra = float(s.salary) * 0.20
            bonus = 1000.0 if s.id == john.id else 0.0
            tax = basic * 0.10
            deduct = basic * 0.12
            net = basic + hra + bonus - tax - deduct
            
            db.session.add(Payroll(
                employee_id=s.id, month=month, year=year,
                basic_salary=basic, hra=hra, bonus=bonus, incentives=0.0,
                deductions=deduct, tax=tax, net_salary=net, status='Paid',
                payslip_path=f"uploads/payslips/payslip_{s.employee_id}_{year}_{month}.pdf" # Mock PDF path
            ))

    # 9. Audit Logs & System Init Alerts
    db.session.add(AuditLog(user_id=1, action="System seeding successfully completed."))
    db.session.add(Notification(user_id=user_objs['HR Manager'].id, title="Welcome!", message="System is operational.", notification_type="system"))

    db.session.commit()
    print("Database seeding completed successfully.")

def backup_db(backup_filename='database_backup.db'):
    """Backup the development SQLite database file"""
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if not db_uri.startswith('sqlite:///'):
        print("Backup is only supported for local SQLite development database.")
        return
        
    db_file = db_uri.replace('sqlite:///', '')
    if not os.path.exists(db_file):
        print(f"Database file '{db_file}' not found. Nothing to backup.")
        return
        
    shutil.copy2(db_file, backup_filename)
    print(f"Database backed up successfully to '{backup_filename}'.")

def restore_db(backup_filename='database_backup.db'):
    """Restore the development SQLite database file from a backup"""
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if not db_uri.startswith('sqlite:///'):
        print("Restore is only supported for local SQLite development database.")
        return
        
    db_file = db_uri.replace('sqlite:///', '')
    if not os.path.exists(backup_filename):
        print(f"Backup file '{backup_filename}' not found. Cannot restore.")
        return
        
    shutil.copy2(backup_filename, db_file)
    print(f"Database restored successfully from '{backup_filename}'.")

if __name__ == '__main__':
    with app.app_context():
        if len(sys.argv) > 1:
            cmd = sys.argv[1]
            if cmd == 'seed':
                seed_database()
            elif cmd == 'backup':
                backup_db()
            elif cmd == 'restore':
                restore_db()
            else:
                print("Unknown command. Use: seed, backup, or restore.")
        else:
            print("Please specify a command: seed, backup, or restore.")
