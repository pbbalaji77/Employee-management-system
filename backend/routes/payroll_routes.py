import os
from flask import Blueprint, render_template, request, send_file, jsonify, session, current_app
from backend.database import db
from backend.models import Payroll, Employee
from backend.auth import login_required, role_required, token_required, api_role_required
from backend.services.audit_service import log_action
from backend.services.pdf_service import generate_payslip_pdf
from backend.services.email_service import send_payroll_notification_email
from datetime import datetime

payroll_bp = Blueprint('payroll', __name__)

@payroll_bp.route('/payroll')
@login_required
@role_required('Super Admin', 'HR Manager')
def payroll_view():
    return render_template('payroll.html')

# ----------------- REST APIs -----------------

@payroll_bp.route('/api/payroll', methods=['GET'])
@token_required
def api_get_payroll():
    employee_id = request.args.get('employee_id')
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    query = Payroll.query
    
    if request.user_role == 'Employee':
        query = query.filter(Payroll.employee_id == request.employee_id)
    elif employee_id:
        query = query.filter(Payroll.employee_id == int(employee_id))
        
    if month:
        query = query.filter(Payroll.month == month)
    if year:
        query = query.filter(Payroll.year == year)
        
    records = query.order_by(Payroll.year.desc(), Payroll.month.desc()).all()
    return jsonify([r.to_dict() for r in records]), 200

@payroll_bp.route('/api/payroll/calculate', methods=['POST'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_calculate_payroll():
    """Calculate and generate a single employee's monthly payslip"""
    data = request.get_json() or {}
    emp_id = data.get('employee_id')
    month = data.get('month')
    year = data.get('year')
    
    if not emp_id or not month or not year:
        return jsonify({'message': 'Missing employee_id, month, or year'}), 400
        
    emp = Employee.query.get_or_404(emp_id)
    
    # Check if payroll already exists for this employee/month/year
    existing = Payroll.query.filter_by(employee_id=emp.id, month=month, year=year).first()
    if existing:
        return jsonify({'message': f'Payroll already generated for {month}/{year}'}), 400
        
    # Salary breakdown logic
    gross = float(emp.salary or 0.0)
    basic = gross * 0.50  # 50% Basic
    hra = gross * 0.20    # 20% HRA
    bonus = float(data.get('bonus', 0.0))
    incentives = float(data.get('incentives', 0.0))
    deductions = basic * 0.12 # 12% PF deduction on Basic
    tax = basic * 0.10        # 10% Tax withholding
    
    net_salary = basic + hra + bonus + incentives - deductions - tax
    
    record = Payroll(
        employee_id=emp.id,
        month=month,
        year=year,
        basic_salary=basic,
        hra=hra,
        bonus=bonus,
        incentives=incentives,
        deductions=deductions,
        tax=tax,
        net_salary=net_salary,
        status='Paid'
    )
    
    db.session.add(record)
    db.session.flush() # Get record.id
    
    # Generate PDF
    pdf_rel_path = generate_payslip_pdf(record, emp, os.path.join(current_app.root_path, 'static', 'uploads', 'payslips'))
    record.payslip_path = pdf_rel_path
    
    db.session.commit()
    
    # Send Notification Email
    send_payroll_notification_email(emp.full_name, emp.email, month, year, net_salary)
    log_action(f"Generated Payroll for {emp.employee_id} ({month}/{year})", request.user_id)
    
    return jsonify(record.to_dict()), 201

@payroll_bp.route('/api/payroll/generate-all', methods=['POST'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_generate_all_payroll():
    """Bulk generate payslips for all active employees for target month/year"""
    data = request.get_json() or {}
    month = data.get('month')
    year = data.get('year')
    
    if not month or not year:
        return jsonify({'message': 'Missing month or year'}), 400
        
    active_employees = Employee.query.filter_by(active_status=True).all()
    count = 0
    
    for emp in active_employees:
        # Check if already exists
        existing = Payroll.query.filter_by(employee_id=emp.id, month=month, year=year).first()
        if existing:
            continue
            
        gross = float(emp.salary or 0.0)
        basic = gross * 0.50
        hra = gross * 0.20
        bonus = 0.0
        incentives = 0.0
        deductions = basic * 0.12
        tax = basic * 0.10
        
        net_salary = basic + hra + bonus + incentives - deductions - tax
        
        record = Payroll(
            employee_id=emp.id,
            month=month,
            year=year,
            basic_salary=basic,
            hra=hra,
            bonus=bonus,
            incentives=incentives,
            deductions=deductions,
            tax=tax,
            net_salary=net_salary,
            status='Paid'
        )
        db.session.add(record)
        db.session.flush()
        
        pdf_rel_path = generate_payslip_pdf(record, emp, os.path.join(current_app.root_path, 'static', 'uploads', 'payslips'))
        record.payslip_path = pdf_rel_path
        
        send_payroll_notification_email(emp.full_name, emp.email, month, year, net_salary)
        count += 1
        
    db.session.commit()
    log_action(f"Bulk generated {count} payroll records for {month}/{year}", request.user_id)
    return jsonify({'message': f'Successfully generated payroll for {count} employees'}), 200

@payroll_bp.route('/api/payroll/download/<int:payroll_id>', methods=['GET'])
@token_required
def api_download_payslip(payroll_id):
    record = Payroll.query.get_or_404(payroll_id)
    
    # Restrict Employees to their own payslips
    if request.user_role == 'Employee' and request.employee_id != record.employee_id:
        return jsonify({'message': 'Access forbidden'}), 403
        
    if not record.payslip_path:
        return jsonify({'message': 'Payslip PDF file not generated yet'}), 404
        
    filepath = os.path.join(current_app.root_path, 'static', record.payslip_path)
    if not os.path.exists(filepath):
        return jsonify({'message': 'PDF file not found on disk'}), 404
        
    return send_file(filepath, as_attachment=True)
