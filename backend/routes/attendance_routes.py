from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.database import db
from backend.models import Attendance, Employee
from backend.auth import login_required, role_required, token_required
from backend.services.audit_service import log_action
from datetime import datetime, date, time

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/attendance')
@login_required
def attendance_view():
    return render_template('attendance.html')

# ----------------- REST APIs -----------------

@attendance_bp.route('/api/attendance', methods=['GET'])
@token_required
def api_get_attendance():
    """Retrieve attendance history for dashboard calendars and logs"""
    employee_id = request.args.get('employee_id')
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    query = Attendance.query
    
    # Non-admins can only see their own attendance
    if request.user_role == 'Employee':
        query = query.filter(Attendance.employee_id == request.employee_id)
    elif employee_id:
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
def api_check_in():
    """Perform employee daily check-in"""
    emp_id = request.employee_id
    if not emp_id:
        return jsonify({'message': 'Logged in user is not associated with an Employee profile'}), 400
        
    today = date.today()
    now_time = datetime.now().time()
    
    # Check if already checked in today
    record = Attendance.query.filter_by(employee_id=emp_id, date=today).first()
    if record:
        return jsonify({'message': 'Already checked in today!'}), 400
        
    # Heuristic: If checking in after 13:00 (1 PM), mark as Half Day
    status = 'Present'
    if now_time.hour >= 13:
        status = 'Half Day'
        
    new_record = Attendance(
        employee_id=emp_id,
        date=today,
        check_in=now_time,
        status=status,
        working_hours=0.0,
        overtime_hours=0.0
    )
    
    db.session.add(new_record)
    db.session.commit()
    
    log_action(f"Checked In for {today.isoformat()}", request.user_id)
    return jsonify(new_record.to_dict()), 201

@attendance_bp.route('/api/attendance/check-out', methods=['POST'])
@token_required
def api_check_out():
    """Perform employee daily check-out, calculating work/overtime hours"""
    emp_id = request.employee_id
    if not emp_id:
        return jsonify({'message': 'Logged in user is not associated with an Employee profile'}), 400
        
    today = date.today()
    record = Attendance.query.filter_by(employee_id=emp_id, date=today).first()
    
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
        
    # Re-evaluate status if work hours are very short
    status = record.status
    if working_h + overtime_h < 4.0:
        status = 'Half Day'
    elif working_h + overtime_h >= 4.0 and record.status == 'Half Day':
        # Upgraded to present if total working time allows
        status = 'Present'
        
    record.check_out = now_time
    record.working_hours = working_h
    record.overtime_hours = overtime_h
    record.status = status
    
    db.session.commit()
    
    log_action(f"Checked Out for {today.isoformat()}. Hours: {working_h + overtime_h}", request.user_id)
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
    
    active_emps = Employee.query.filter_by(active_status=True).count()
    not_marked = max(0, active_emps - (present_cnt + half_day_cnt + leave_cnt + absent_cnt))
    
    return jsonify({
        'date': today.isoformat(),
        'present': present_cnt,
        'half_day': half_day_cnt,
        'on_leave': leave_cnt,
        'absent': absent_cnt,
        'not_marked': not_marked
    }), 200
