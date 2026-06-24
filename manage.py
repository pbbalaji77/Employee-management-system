import os
import shutil
import sys
from datetime import datetime, date, time, timedelta
from app import app
from backend.database import db
from backend.models import HRUser, Department, Employee, Attendance, LeaveRequest, Payroll, PerformanceReview, AuditLog, Notification

def seed_database():
    """Seed database with HR Manager, sample departments, employees, and operations history"""
    print("Re-creating database tables...")
    db.drop_all()
    db.create_all()
    print("Seeding database...")
    
    # 1. Create HR User
    hr_user = HRUser(
        username='HR Manager',
        email='hr@enterprise.com'
    )
    hr_user.set_password('Hr@123')
    db.session.add(hr_user)
    db.session.flush()

    # 2. Create Departments
    departments = [
        ('Human Resources', 1200000.00, 'Responsible for sourcing, screening, and managing talent.'),
        ('Engineering', 4500000.00, 'Product design, coding, software maintenance, and deployment.'),
        ('Sales & Marketing', 2200000.00, 'Customer acquisition, lead generation, and corporate branding.'),
        ('Finance', 1500000.00, 'Accounting, tax audits, payroll processing, and budget control.')
    ]
    
    dept_objs = {}
    for name, budget, desc in departments:
        dept = Department(
            department_name=name,
            budget=budget,
            description=desc
        )
        db.session.add(dept)
        dept_objs[name] = dept
    db.session.flush()

    # 3. Create Employee Records
    employees_data = [
        ('EMP1001', 'Jane Doe', 'jane.doe@enterprise.com', 'HR Specialist', 'Human Resources', 80000.00, 'Female', None),
        ('EMP1002', 'Bob Smith', 'bob.smith@enterprise.com', 'Engineering Lead', 'Engineering', 120000.00, 'Male', None),
        ('EMP1003', 'John Doe', 'john.doe@enterprise.com', 'Software Engineer', 'Engineering', 90000.00, 'Male', 'EMP1002'),
    ]

    emp_objs = {}
    for emp_code, name, email, desg, dept_name, salary, gender, mgr_code in employees_data:
        # Resolve manager id
        mgr_id = None
        if mgr_code:
            mgr = Employee.query.filter_by(employee_id=mgr_code).first()
            if mgr:
                mgr_id = mgr.id
                
        emp = Employee(
            employee_id=emp_code,
            full_name=name,
            email=email,
            phone_number='9876543210',
            emergency_contact='9012345678',
            gender=gender,
            date_of_birth=date(1990, 5, 12),
            address='Flat 405, Block B, Tech Hub Appts, Bangalore',
            department_id=dept_objs[dept_name].id,
            designation=desg,
            salary=salary,
            joining_date=date(2024, 1, 15),
            reporting_manager_id=mgr_id,
            profile_photo='uploads/profiles/default.png',
            status='Active'
        )
        db.session.add(emp)
        db.session.flush()
        emp_objs[emp_code] = emp

    # Assign Department Heads
    dept_objs['Human Resources'].department_head_id = emp_objs['EMP1001'].id
    dept_objs['Engineering'].department_head_id = emp_objs['EMP1002'].id
    db.session.flush()

    # 4. Seed Attendance Logs (Previous 14 days)
    john = emp_objs['EMP1003']
    bob = emp_objs['EMP1002']
    jane = emp_objs['EMP1001']
    
    today = date.today()
    for i in range(1, 15):
        log_date = today - timedelta(days=i)
        if log_date.weekday() >= 5:
            # Weekend holiday
            continue
            
        # Jane (HR Specialist)
        db.session.add(Attendance(
            employee_id=jane.id, date=log_date,
            check_in=time(9, 5, 0), check_out=time(17, 30, 0),
            working_hours=8.0, overtime_hours=0.4, status='Present'
        ))
            
        # Bob (Lead)
        db.session.add(Attendance(
            employee_id=bob.id, date=log_date,
            check_in=time(8, 55, 0), check_out=time(18, 15, 0),
            working_hours=8.0, overtime_hours=1.3, status='Present'
        ))

        # John (Employee)
        if i == 5:
            # Sick leave
            db.session.add(Attendance(
                employee_id=john.id, date=log_date,
                check_in=None, check_out=None,
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

    # 5. Seed Leave Requests
    leave_reqs = [
        (john.id, 'Sick Leave', today - timedelta(days=5), today - timedelta(days=5), 'Had a bad flu', 'Approved'),
        (john.id, 'Casual Leave', today + timedelta(days=10), today + timedelta(days=11), 'Going out of town', 'Pending'),
        (john.id, 'Paid Leave', today - timedelta(days=30), today - timedelta(days=28), 'Family wedding', 'Approved')
    ]
    for e_id, l_type, start, end, reason, status in leave_reqs:
        db.session.add(LeaveRequest(
            employee_id=e_id, leave_type=l_type, start_date=start, end_date=end,
            reason=reason, status=status
        ))

    # 6. Seed Performance Review
    db.session.add(PerformanceReview(
        employee_id=john.id,
        review_period='Quarterly',
        rating=4,
        goal_achievement=95.5,
        manager_feedback='John is performing very well. He completed the backend API migration ahead of schedule.',
        employee_feedback='I enjoyed working on the migration.',
        reviewer_id=bob.id
    ))

    # 7. Seed Payroll (Calculations for last month)
    last_month_date = today - timedelta(days=30)
    month = last_month_date.month
    year = last_month_date.year
    
    staff = [jane, bob, john]
    for s in staff:
        basic = float(s.salary) * 0.60
        allowances = float(s.salary) * 0.40
        bonus = 1000.0 if s.id == john.id else 0.0
        deduct = basic * 0.22
        net = basic + allowances + bonus - deduct
        
        db.session.add(Payroll(
            employee_id=s.id, month=month, year=year,
            basic_salary=basic, allowances=allowances, bonuses=bonus,
            deductions=deduct, net_salary=net,
            payslip_path=f"uploads/payslips/payslip_{s.employee_id}_{year}_{month}.pdf"
        ))

    # 8. Audit Logs & System Init Alerts
    db.session.add(AuditLog(user_id=hr_user.id, action="System seeding successfully completed."))
    db.session.add(Notification(title="Welcome!", message="System is operational."))

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
