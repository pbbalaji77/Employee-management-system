from flask import Blueprint, render_template, request, jsonify, session
from backend.database import db
from backend.models import PerformanceReview, Employee
from backend.auth import login_required, role_required, token_required, api_role_required
from backend.services.audit_service import log_action

performance_bp = Blueprint('performance', __name__)

@performance_bp.route('/performance')
@login_required
def performance_view():
    employees = Employee.query.all()
    return render_template('performance.html', employees=employees)

# ----------------- REST APIs -----------------

@performance_bp.route('/api/performance', methods=['GET'])
@token_required
def api_list_reviews():
    employee_id = request.args.get('employee_id')
    period = request.args.get('period')
    
    query = PerformanceReview.query
    
    if request.user_role == 'Employee':
        query = query.filter(PerformanceReview.employee_id == request.employee_id)
    elif employee_id:
        query = query.filter(PerformanceReview.employee_id == int(employee_id))
        
    if period:
        query = query.filter(PerformanceReview.review_period == period)
        
    records = query.order_by(PerformanceReview.created_at.desc()).all()
    return jsonify([r.to_dict() for r in records]), 200

@performance_bp.route('/api/performance', methods=['POST'])
@token_required
@api_role_required('Super Admin', 'HR Manager', 'Team Lead')
def api_create_review():
    """Submit a manager appraisal review for an employee"""
    data = request.get_json() or {}
    emp_id = data.get('employee_id')
    rating = data.get('rating')
    goal_pct = data.get('goal_achievement')
    period = data.get('review_period')
    feedback = data.get('manager_feedback')
    
    if not emp_id or not rating or not period:
        return jsonify({'message': 'Missing employee_id, rating, or review_period'}), 400
        
    emp = Employee.query.get_or_404(emp_id)
    reviewer_id = request.employee_id if request.employee_id else 1
    
    review = PerformanceReview(
        employee_id=emp.id,
        review_period=period,
        rating=int(rating),
        goal_achievement=float(goal_pct or 0.0),
        manager_feedback=feedback,
        reviewer_id=reviewer_id
    )
    
    db.session.add(review)
    db.session.commit()
    
    log_action(f"Submitted Performance appraisal for {emp.employee_id}", request.user_id)
    return jsonify(review.to_dict()), 201

@performance_bp.route('/api/performance/<int:review_id>/feedback', methods=['PUT'])
@token_required
def api_append_employee_feedback(review_id):
    """Allows an employee to write their response feedback on a review"""
    review = PerformanceReview.query.get_or_404(review_id)
    
    # Check authorization (employee responding to their own review)
    if request.user_role == 'Employee' and request.employee_id != review.employee_id:
        return jsonify({'message': 'Access forbidden'}), 403
        
    data = request.get_json() or {}
    feedback = data.get('employee_feedback')
    if not feedback:
        return jsonify({'message': 'Feedback content is required'}), 400
        
    review.employee_feedback = feedback
    db.session.commit()
    
    log_action(f"Appended self performance response feedback for review {review_id}", request.user_id)
    return jsonify(review.to_dict()), 200
