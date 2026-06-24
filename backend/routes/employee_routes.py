import os
import csv
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from werkzeug.utils import secure_filename
from openpyxl import load_workbook
from backend.database import db
from backend.models import Employee, Department, LeaveRequest, Attendance, Payroll, EmployeeDocument, PerformanceReview
from backend.auth import login_required, role_required, token_required, api_role_required
from backend.services.audit_service import log_action
from datetime import datetime, date

employee_bp = Blueprint('employee', __name__)

def generate_employee_id():
    """Generates next sequential employee code: EMP1001, EMP1002..."""
    count = db.session.query(Employee).count()
    return f"EMP{1001 + count}"

# ----------------- Web Views -----------------

@employee_bp.route('/employees')
@login_required
def list_view():
    departments = Department.query.all()
    managers = Employee.query.filter(Employee.designation.ilike('%manager%') | Employee.designation.ilike('%lead%')).all()
    return render_template('employees.html', departments=departments, managers=managers)

@employee_bp.route('/employees/<int:emp_id>')
@login_required
def detail_view(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    departments = Department.query.all()
    managers = Employee.query.filter(Employee.id != emp_id).all()
    
    # Details for child tabs
    attendance = Attendance.query.filter_by(employee_id=emp_id).order_by(Attendance.date.desc()).all()
    leaves = LeaveRequest.query.filter_by(employee_id=emp_id).order_by(LeaveRequest.start_date.desc()).all()
    payroll = Payroll.query.filter_by(employee_id=emp_id).order_by(Payroll.year.desc(), Payroll.month.desc()).all()
    documents = EmployeeDocument.query.filter_by(employee_id=emp_id).order_by(EmployeeDocument.id.desc()).all()
    reviews = PerformanceReview.query.filter_by(employee_id=emp_id).order_by(PerformanceReview.created_at.desc()).all()
    
    return render_template(
        'employee_detail.html',
        employee=emp,
        departments=departments,
        managers=managers,
        attendance=attendance,
        leaves=leaves,
        payroll=payroll,
        documents=documents,
        reviews=reviews
    )

# ----------------- REST APIs -----------------

@employee_bp.route('/api/employees', methods=['GET'])
@token_required
def api_list_employees():
    """Paginated list of employees with search and filters"""
    query = Employee.query
    
    # Filters
    search = request.args.get('search')
    dept_id = request.args.get('department_id')
    status = request.args.get('status')
    gender = request.args.get('gender')
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            db.or_(
                Employee.full_name.ilike(search_filter),
                Employee.email.ilike(search_filter),
                Employee.employee_id.ilike(search_filter),
                Employee.designation.ilike(search_filter)
            )
        )
    if dept_id:
        query = query.filter(Employee.department_id == int(dept_id))
    if status:
        query = query.filter(Employee.status.ilike(status))
    if gender:
        query = query.filter(Employee.gender.ilike(gender))
        
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'employees': [emp.to_dict() for emp in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': paginated.page
    }), 200

@employee_bp.route('/api/employees/<int:emp_id>', methods=['GET'])
@token_required
def api_get_employee(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    return jsonify(emp.to_dict()), 200

@employee_bp.route('/api/employees', methods=['POST'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_create_employee():
    """Create a new employee record"""
    data = request.form.to_dict() if request.form else request.get_json() or {}
    
    email = data.get('email')
    if not email:
        return jsonify({'message': 'Email is required'}), 400
        
    if Employee.query.filter_by(email=email).first():
        return jsonify({'message': 'Employee with this email already exists'}), 400

    # Handle image upload
    profile_photo_path = 'uploads/profiles/default.png'
    if 'profile_photo' in request.files:
        file = request.files['profile_photo']
        if file and file.filename != '':
            filename = secure_filename(f"{uuid_name()}_{file.filename}")
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles')
            os.makedirs(upload_dir, exist_ok=True)
            file.save(os.path.join(upload_dir, filename))
            profile_photo_path = f"uploads/profiles/{filename}"

    # Determine full_name from inputs
    full_name = data.get('full_name')
    if not full_name:
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip() or "New Employee"

    # Create Employee
    emp_code = generate_employee_id()
    dob = datetime.strptime(data.get('date_of_birth'), '%Y-%m-%d').date() if data.get('date_of_birth') else None
    
    joining_str = data.get('joining_date')
    if joining_str:
        joining = datetime.strptime(joining_str, '%Y-%m-%d').date()
    else:
        joining = date.today()

    status_str = 'Active'
    if 'status' in data:
        status_str = data['status']
    elif 'active_status' in data:
        active_bool = str(data['active_status']).lower() in ['true', '1', 'on']
        status_str = 'Active' if active_bool else 'Inactive'

    mgr_id = data.get('reporting_manager_id') or data.get('manager_id')
    if mgr_id and str(mgr_id).lower() not in ['none', 'null', '']:
        reporting_manager_id = int(mgr_id)
    else:
        reporting_manager_id = None

    new_emp = Employee(
        employee_id=emp_code,
        full_name=full_name,
        email=email,
        phone_number=data.get('phone_number') or data.get('mobile_number'),
        gender=data.get('gender'),
        date_of_birth=dob,
        department_id=int(data.get('department_id')) if data.get('department_id') else 1,
        designation=data.get('designation'),
        salary=float(data.get('salary', 0.0) or 0.0),
        joining_date=joining,
        reporting_manager_id=reporting_manager_id,
        address=data.get('address'),
        emergency_contact=data.get('emergency_contact'),
        profile_photo=profile_photo_path,
        status=status_str
    )
    
    db.session.add(new_emp)
    db.session.commit()
    
    log_action(f"Created Employee record {emp_code}", request.user_id)
    return jsonify(new_emp.to_dict()), 201

@employee_bp.route('/api/employees/<int:emp_id>', methods=['PUT'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_update_employee(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    data = request.form.to_dict() if request.form else request.get_json() or {}
    
    # Update fields
    if 'full_name' in data:
        emp.full_name = data['full_name']
    elif 'first_name' in data or 'last_name' in data:
        first_name = data.get('first_name', '') or (emp.full_name.split(' ')[0] if emp.full_name else '')
        last_name = data.get('last_name', '') or (emp.full_name.split(' ')[1] if emp.full_name and len(emp.full_name.split(' ')) > 1 else '')
        emp.full_name = f"{first_name} {last_name}".strip()
        
    if 'email' in data: emp.email = data['email']
    if 'phone_number' in data: emp.phone_number = data['phone_number']
    elif 'mobile_number' in data: emp.phone_number = data['mobile_number']
    
    if 'gender' in data: emp.gender = data['gender']
    if 'address' in data: emp.address = data['address']
    if 'emergency_contact' in data: emp.emergency_contact = data['emergency_contact']
    if 'designation' in data: emp.designation = data['designation']
    
    if 'department_id' in data and data['department_id']: 
        emp.department_id = int(data['department_id'])
        
    if 'reporting_manager_id' in data:
        mgr_id = data['reporting_manager_id']
        emp.reporting_manager_id = int(mgr_id) if mgr_id and str(mgr_id).lower() not in ['none', 'null', ''] else None
    elif 'manager_id' in data:
        mgr_id = data['manager_id']
        emp.reporting_manager_id = int(mgr_id) if mgr_id and str(mgr_id).lower() not in ['none', 'null', ''] else None
        
    if 'salary' in data: 
        emp.salary = float(data['salary'])
        
    if 'status' in data:
        emp.status = data['status']
    elif 'active_status' in data:
        status_val = str(data['active_status']).lower() in ['true', '1', 'on']
        emp.status = 'Active' if status_val else 'Inactive'
            
    if 'date_of_birth' in data and data['date_of_birth']:
        emp.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
    if 'joining_date' in data and data['joining_date']:
        emp.joining_date = datetime.strptime(data['joining_date'], '%Y-%m-%d').date()

    # Image upload
    if 'profile_photo' in request.files:
        file = request.files['profile_photo']
        if file and file.filename != '':
            filename = secure_filename(f"{uuid_name()}_{file.filename}")
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'profiles')
            os.makedirs(upload_dir, exist_ok=True)
            file.save(os.path.join(upload_dir, filename))
            emp.profile_photo = f"uploads/profiles/{filename}"

    db.session.commit()
    log_action(f"Updated Employee profile {emp.employee_id}", request.user_id)
    return jsonify(emp.to_dict()), 200

@employee_bp.route('/api/employees/<int:emp_id>', methods=['DELETE'])
@token_required
@api_role_required('Super Admin')
def api_delete_employee(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    code = emp.employee_id
    db.session.delete(emp)
    db.session.commit()
    log_action(f"Deleted Employee {code}", request.user_id)
    return jsonify({'message': 'Employee deleted successfully'}), 200

@employee_bp.route('/api/employees/bulk-delete', methods=['POST'])
@token_required
@api_role_required('Super Admin')
def api_bulk_delete():
    data = request.get_json() or {}
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'message': 'No IDs provided'}), 400
        
    employees = Employee.query.filter(Employee.id.in_(ids)).all()
    count = 0
    for emp in employees:
        db.session.delete(emp)
        count += 1
        
    db.session.commit()
    log_action(f"Bulk deleted {count} employees", request.user_id)
    return jsonify({'message': f'Successfully deleted {count} employees'}), 200

@employee_bp.route('/api/employees/import', methods=['POST'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_bulk_import():
    """Bulk import employees from CSV or XLSX sheets"""
    if 'file' not in request.files:
        return jsonify({'message': 'No file uploaded'}), 400
        
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'message': 'No file selected'}), 400
        
    ext = file.filename.rsplit('.', 1)[-1].lower()
    imported_count = 0
    
    try:
        temp_path = os.path.join(current_app.root_path, 'static', 'uploads', f"temp_import_{uuid_name()}.{ext}")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        file.save(temp_path)

        rows = []
        if ext == 'csv':
            with open(temp_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        elif ext in ['xlsx', 'xls']:
            wb = load_workbook(temp_path)
            sheet = wb.active
            headers = [cell.value for cell in sheet[1]]
            for r in range(2, sheet.max_row + 1):
                row_val = [sheet.cell(row=r, column=c).value for c in range(1, len(headers) + 1)]
                if any(row_val):
                    rows.append(dict(zip(headers, row_val)))
        
        for r in rows:
            email = r.get('email')
            if not email or Employee.query.filter_by(email=email).first():
                continue
                
            # Parse optional dates
            dob = None
            if r.get('date_of_birth'):
                try:
                    dob = datetime.strptime(str(r.get('date_of_birth')), '%Y-%m-%d').date()
                except Exception:
                    pass
            
            joining = date.today()
            if r.get('joining_date'):
                try:
                    joining = datetime.strptime(str(r.get('joining_date')), '%Y-%m-%d').date()
                except Exception:
                    pass

            # Find department or map to first
            dept_name = r.get('department')
            dept_id = None
            if dept_name:
                dept = Department.query.filter(Department.department_name.ilike(dept_name)).first()
                if dept:
                    dept_id = dept.id

            full_name = r.get('full_name')
            if not full_name:
                first_name = r.get('first_name', '')
                last_name = r.get('last_name', '')
                full_name = f"{first_name} {last_name}".strip() or "Imported Employee"

            emp = Employee(
                employee_id=generate_employee_id(),
                full_name=full_name,
                email=email,
                phone_number=r.get('phone_number') or r.get('mobile_number'),
                gender=r.get('gender'),
                date_of_birth=dob,
                joining_date=joining,
                department_id=dept_id or 1,
                designation=r.get('designation', 'Associate'),
                salary=float(r.get('salary', 0.0) or 0.0),
                profile_photo='uploads/profiles/default.png',
                status='Active'
            )
            db.session.add(emp)
            db.session.flush()
            imported_count += 1

        db.session.commit()
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        log_action(f"Imported {imported_count} employees via sheet upload", request.user_id)
        return jsonify({'message': f'Successfully imported {imported_count} employees'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error parsing sheet: {str(e)}'}), 500

def uuid_name():
    import uuid
    return str(uuid.uuid4())[:8]
