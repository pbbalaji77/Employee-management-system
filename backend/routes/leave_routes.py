from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.database import db
from backend.models import LeaveRequest, Employee, Attendance
from backend.auth import login_required, role_required, token_required, api_role_required
from backend.services.audit_service import log_action
from backend.services.email_service import send_leave_status_email
from datetime import datetime, date, timedelta

leave_bp = Blueprint('leave', __name__)

# Standard annual allowances for leave types
LEAVE_LIMITS = {
    'Casual Leave': 12,
    'Sick Leave': 10,
    'Paid Leave': 15,
    'Maternity Leave': 90,
    'Emergency Leave': 5
}

def calculate_leave_balances(employee_id):
    """Calculate remaining balances dynamically for an employee"""
    today = date.today()
    
    # Query approved leaves for the current year
    start_of_year = date(today.year, 1, 1)
    end_of_year = date(today.year, 12, 31)
    
    approved_leaves = LeaveRequest.query.filter(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.status == 'Approved',
        LeaveRequest.start_date >= start_of_year,
        LeaveRequest.end_date <= end_of_year
    ).all()
    
    # Calculate days taken per type
    taken = {k: 0 for k in LEAVE_LIMITS.keys()}
    for req in approved_leaves:
        if req.leave_type in taken:
            days = (req.end_date - req.start_date).days + 1
            taken[req.leave_type] += days
            
    # Calculate remaining
    balances = {}
    for l_type, limit in LEAVE_LIMITS.items():
        balances[l_type] = {
            'limit': limit,
            'taken': taken[l_type],
            'remaining': max(0, limit - taken[l_type])
        }
    return balances

# ----------------- Web Views -----------------

@leave_bp.route('/leaves')
@login_required
def list_view():
    emp_id = session.get('employee_id')
    balances = calculate_leave_balances(emp_id) if emp_id else {}
    return render_template('leaves.html', balances=balances)

# ----------------- REST APIs -----------------

@leave_bp.route('/api/leaves', methods=['GET'])
@token_required
def api_list_leaves():
    """List leave requests. Employees see their own, Leads/HR see pending/all"""
    status = request.args.get('status')
    
    query = LeaveRequest.query
    
    if request.user_role == 'Employee':
        query = query.filter(LeaveRequest.employee_id == request.employee_id)
    elif request.user_role == 'Team Lead':
        # Team Leads can see requests of employees they manage
        sub_ids = [e.id for e in Employee.query.filter_by(manager_id=request.employee_id).all()]
        query = query.filter(db.or_(LeaveRequest.employee_id == request.employee_id, LeaveRequest.employee_id.in_(sub_ids)))
        
    if status:
        query = query.filter(LeaveRequest.status == status)
        
    records = query.order_by(LeaveRequest.created_at.desc()).all()
    return jsonify([r.to_dict() for r in records]), 200

@leave_bp.route('/api/leaves/balances', methods=['GET'])
@token_required
def api_get_balances():
    emp_id = request.args.get('employee_id', request.employee_id, type=int)
    # Check permissions
    if request.user_role == 'Employee' and request.employee_id != emp_id:
        return jsonify({'message': 'Access forbidden'}), 403
        
    balances = calculate_leave_balances(emp_id)
    return jsonify(balances), 200

@leave_bp.route('/api/leaves', methods=['POST'])
@token_required
def api_apply_leave():
    """Submit a new leave application"""
    emp_id = request.employee_id
    if not emp_id:
        return jsonify({'message': 'Logged in user is not an Employee profile'}), 400
        
    data = request.get_json() or {}
    l_type = data.get('leave_type')
    start_str = data.get('start_date')
    end_str = data.get('end_date')
    reason = data.get('reason')
    
    if not l_type or not start_str or not end_str:
        return jsonify({'message': 'Missing required fields'}), 400
        
    try:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'message': 'Invalid date format (use YYYY-MM-DD)'}), 400
        
    if start_date > end_date:
        return jsonify({'message': 'Start date cannot be after end date'}), 400
        
    if start_date < date.today():
        return jsonify({'message': 'Cannot apply leave for past dates'}), 400
        
    # Check leave balance limit
    req_days = (end_date - start_date).days + 1
    balances = calculate_leave_balances(emp_id)
    if l_type not in balances:
        return jsonify({'message': 'Invalid leave type'}), 400
        
    remaining = balances[l_type]['remaining']
    if req_days > remaining:
        return jsonify({'message': f'Insufficient leave balance. Requested: {req_days} days, Remaining: {remaining} days.'}), 400
        
    # Create Request
    req = LeaveRequest(
        employee_id=emp_id,
        leave_type=l_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status='Pending'
    )
    db.session.add(req)
    db.session.commit()
    
    log_action(f"Applied for {l_type} ({req_days} days)", request.user_id)
    return jsonify(req.to_dict()), 201

@leave_bp.route('/api/leaves/<int:leave_id>/action', methods=['POST'])
@token_required
@api_role_required('Super Admin', 'HR Manager', 'Team Lead')
def api_leave_action(leave_id):
    """Approve or Reject a leave application"""
    req = LeaveRequest.query.get_or_404(leave_id)
    if req.status != 'Pending':
        return jsonify({'message': 'Leave request already processed'}), 400
        
    data = request.get_json() or {}
    action = data.get('action') # Approved or Rejected
    feedback = data.get('feedback')
    
    if action not in ['Approved', 'Rejected']:
        return jsonify({'message': 'Action must be Approved or Rejected'}), 400
        
    req.status = action
    req.approved_by = request.employee_id
    
    # If approved, write 'Leave' status into attendance logs for all days in the range
    if action == 'Approved':
        curr_d = req.start_date
        while curr_d <= req.end_date:
            # Check if attendance record already exists. If yes, update. If no, create.
            att = Attendance.query.filter_by(employee_id=req.employee_id, date=curr_d).first()
            if not att:
                att = Attendance(
                    employee_id=req.employee_id,
                    date=curr_d,
                    check_in=datetime.now().time(), # placeholder
                    check_out=datetime.now().time(),
                    working_hours=0.0,
                    overtime_hours=0.0,
                    status='Leave'
                )
                db.session.add(att)
            else:
                att.status = 'Leave'
            curr_d += timedelta(days=1)
            
    db.session.commit()
    
    # Notify employee via email
    send_leave_status_email(
        req.employee.email,
        req.employee.full_name,
        req.leave_type,
        req.start_date.isoformat(),
        req.end_date.isoformat(),
        action,
        request.user_email,
        feedback
    )
    
    log_action(f"Leave request {leave_id} marked as {action}", request.user_id)
    return jsonify(req.to_dict()), 200
