from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.database import db
from backend.models import Attendance, Employee
from backend.auth import login_required, role_required, token_required, api_role_required
from backend.services.audit_service import log_action
from datetime import datetime, date, time

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/attendance')
@login_required
def attendance_view():
    employees = Employee.query.filter_by(status='Active').order_by(Employee.full_name).all()
    return render_template('attendance.html', employees=employees)

# ----------------- REST APIs -----------------

@attendance_bp.route('/api/attendance', methods=['GET'])
@token_required
def api_get_attendance():
    """Retrieve attendance history for dashboard calendars and logs"""
    employee_id = request.args.get('employee_id')
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    query = Attendance.query
    
    if employee_id:
        query = query.filter(Attendance.employee_id == int(employee_id))
        
    if month and year:
        # Simple extraction using start/end date range
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        query = query.filter(Attendance.date >= start_date, Attendance.date < end_date)
        
    records = query.order_by(Attendance.date.desc()).all()
    return jsonify([r.to_dict() for r in records]), 200

@attendance_bp.route('/api/attendance/check-in', methods=['POST'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_check_in():
    """Perform employee daily check-in (recorded by HR)"""
    data = request.get_json() or {}
    emp_id = data.get('employee_id')
    
    if not emp_id:
        return jsonify({'message': 'employee_id is required'}), 400
        
    emp = Employee.query.get_or_404(emp_id)
    today = date.today()
    now_time = datetime.now().time()
    
    # Check if already checked in today
    record = Attendance.query.filter_by(employee_id=emp.id, date=today).first()
    if record:
        return jsonify({'message': 'Already checked in today!'}), 400
        
    # Heuristic: If checking in after 13:00 (1 PM), mark as Half Day
    status = 'Present'
    if now_time.hour >= 13:
        status = 'Half Day'
        
    new_record = Attendance(
        employee_id=emp.id,
        date=today,
        check_in=now_time,
        status=status,
        working_hours=0.0,
        overtime_hours=0.0
    )
    
    db.session.add(new_record)
    db.session.commit()
    
    log_action(f"Recorded Check-In for Employee {emp.employee_id}", request.user_id)
    return jsonify(new_record.to_dict()), 201

@attendance_bp.route('/api/attendance/check-out', methods=['POST'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_check_out():
    """Perform employee daily check-out, calculating work/overtime hours"""
    data = request.get_json() or {}
    emp_id = data.get('employee_id')
    
    if not emp_id:
        return jsonify({'message': 'employee_id is required'}), 400
        
    emp = Employee.query.get_or_404(emp_id)
    today = date.today()
    record = Attendance.query.filter_by(employee_id=emp.id, date=today).first()
    
    if not record:
        return jsonify({'message': 'No check-in record found for today. Check in first.'}), 400
        
    if record.check_out:
        return jsonify({'message': 'Already checked out today.'}), 400
        
    now = datetime.now()
    now_time = now.time()
    
    # Compute working hours
    checkin_dt = datetime.combine(today, record.check_in)
    checkout_dt = datetime.combine(today, now_time)
    diff = (checkout_dt - checkin_dt).total_seconds() / 3600.0
    working_h = round(diff, 2)
    
    # Overtime logic (assuming standard 8 hour workday)
    overtime_h = 0.0
    if working_h > 8.0:
        overtime_h = round(working_h - 8.0, 2)
        working_h = 8.0
        
    status = record.status
    if working_h + overtime_h < 4.0:
        status = 'Half Day'
    elif working_h + overtime_h >= 4.0 and record.status == 'Half Day':
        status = 'Present'
        
    record.check_out = now_time
    record.working_hours = working_h
    record.overtime_hours = overtime_h
    record.status = status
    
    db.session.commit()
    
    log_action(f"Recorded Check-Out for Employee {emp.employee_id}. Hours: {working_h + overtime_h}", request.user_id)
    return jsonify(record.to_dict()), 200

@attendance_bp.route('/api/attendance/summary', methods=['GET'])
@token_required
def api_attendance_summary():
    """Retrieve key aggregate statistics for the dashboard/report charts"""
    today = date.today()
    present_cnt = Attendance.query.filter_by(date=today, status='Present').count()
    half_day_cnt = Attendance.query.filter_by(date=today, status='Half Day').count()
    leave_cnt = Attendance.query.filter_by(date=today, status='Leave').count()
    absent_cnt = Attendance.query.filter_by(date=today, status='Absent').count()
    
    active_emps = Employee.query.filter_by(status='Active').count()
    not_marked = max(0, active_emps - (present_cnt + half_day_cnt + leave_cnt + absent_cnt))
    
    return jsonify({
        'date': today.isoformat(),
        'present': present_cnt,
        'half_day': half_day_cnt,
        'on_leave': leave_cnt,
        'absent': absent_cnt,
        'not_marked': not_marked
    }), 200

@attendance_bp.route('/api/attendance/mark', methods=['POST'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_mark_attendance():
    """Manually mark or update employee attendance for a specific date (recorded by HR)"""
    data = request.get_json() or {}
    emp_id = data.get('employee_id')
    date_str = data.get('date')
    status = data.get('status')
    
    if not emp_id or not date_str or not status:
        return jsonify({'message': 'employee_id, date, and status are required'}), 400
        
    emp = Employee.query.get_or_404(emp_id)
    
    try:
        log_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'message': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
    if status not in ['Present', 'Absent', 'Half Day', 'Leave']:
        return jsonify({'message': 'Invalid status. Choose Present, Absent, Half Day, or Leave'}), 400

    # Check if record already exists for this date and employee
    record = Attendance.query.filter_by(employee_id=emp.id, date=log_date).first()
    
    check_in_time = None
    check_out_time = None
    working_h = 0.0
    overtime_h = 0.0
    
    if status in ['Present', 'Half Day']:
        check_in_str = data.get('check_in') or '09:00'
        check_out_str = data.get('check_out') or '17:00'
        
        try:
            check_in_time = datetime.strptime(check_in_str, '%H:%M').time()
            check_out_time = datetime.strptime(check_out_str, '%H:%M').time()
        except ValueError:
            return jsonify({'message': 'Invalid time format. Use HH:MM'}), 400
            
        # Compute working hours
        checkin_dt = datetime.combine(log_date, check_in_time)
        checkout_dt = datetime.combine(log_date, check_out_time)
        if checkout_dt < checkin_dt:
            return jsonify({'message': 'Check out time must be after check in time'}), 400
            
        diff = (checkout_dt - checkin_dt).total_seconds() / 3600.0
        working_h = round(diff, 2)
        
        # Overtime logic (assuming standard 8 hour workday)
        if working_h > 8.0:
            overtime_h = round(working_h - 8.0, 2)
            working_h = 8.0
            
    if record:
        # Update existing record
        record.status = status
        record.check_in = check_in_time
        record.check_out = check_out_time
        record.working_hours = working_h
        record.overtime_hours = overtime_h
    else:
        # Create new record
        record = Attendance(
            employee_id=emp.id,
            date=log_date,
            check_in=check_in_time,
            check_out=check_out_time,
            working_hours=working_h,
            overtime_hours=overtime_h,
            status=status
        )
        db.session.add(record)
        
    db.session.commit()
    
    log_action(f"Manually marked {status} for Employee {emp.employee_id} on {date_str}", request.user_id)
    return jsonify(record.to_dict()), 200

@attendance_bp.route('/api/attendance/<int:record_id>', methods=['DELETE'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_delete_attendance(record_id):
    """Delete an attendance record"""
    record = Attendance.query.get_or_404(record_id)
    emp_code = record.employee.employee_id if record.employee else 'Unknown'
    date_str = record.date.isoformat()
    
    db.session.delete(record)
    db.session.commit()
    
    log_action(f"Deleted attendance record for Employee {emp_code} on {date_str}", request.user_id)
    return jsonify({'message': 'Attendance record deleted successfully'}), 200
