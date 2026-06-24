from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.database import db
from backend.models import Department, Employee
from backend.auth import login_required, role_required, token_required, api_role_required
from backend.services.audit_service import log_action

department_bp = Blueprint('department', __name__)

@department_bp.route('/departments')
@login_required
@role_required('Super Admin', 'HR Manager')
def list_view():
    employees = Employee.query.all()
    return render_template('departments.html', employees=employees)

# ----------------- REST APIs -----------------

@department_bp.route('/api/departments', methods=['GET'])
@token_required
def api_list_departments():
    depts = Department.query.all()
    return jsonify([d.to_dict() for d in depts]), 200

@department_bp.route('/api/departments/<int:dept_id>', methods=['GET'])
@token_required
def api_get_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    return jsonify(dept.to_dict()), 200

@department_bp.route('/api/departments', methods=['POST'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_create_department():
    data = request.get_json() or {}
    name = data.get('department_name')
    if not name:
        return jsonify({'message': 'Department Name is required'}), 400
        
    if Department.query.filter_by(department_name=name).first():
        return jsonify({'message': 'Department already exists'}), 400
        
    dept = Department(
        department_name=name,
        department_head_id=data.get('department_head_id') if data.get('department_head_id') else None,
        description=data.get('description'),
        budget=float(data.get('budget', 0.0))
    )
    db.session.add(dept)
    db.session.commit()
    
    log_action(f"Created Department {name}", request.user_id)
    return jsonify(dept.to_dict()), 201

@department_bp.route('/api/departments/<int:dept_id>', methods=['PUT'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_update_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    data = request.get_json() or {}
    
    if 'department_name' in data:
        existing = Department.query.filter_by(department_name=data['department_name']).first()
        if existing and existing.id != dept_id:
            return jsonify({'message': 'Department name already exists'}), 400
        dept.department_name = data['department_name']
        
    if 'department_head_id' in data:
        dept.department_head_id = int(data['department_head_id']) if data['department_head_id'] else None
    if 'description' in data:
        dept.description = data['description']
    if 'budget' in data:
        dept.budget = float(data['budget'])
        
    db.session.commit()
    log_action(f"Updated Department {dept.department_name}", request.user_id)
    return jsonify(dept.to_dict()), 200

@department_bp.route('/api/departments/<int:dept_id>', methods=['DELETE'])
@token_required
@api_role_required('Super Admin')
def api_delete_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    name = dept.department_name
    
    # Check if there are employees assigned to it
    if len(dept.employees) > 0:
        return jsonify({'message': 'Cannot delete department. There are active employees assigned to it.'}), 400
        
    db.session.delete(dept)
    db.session.commit()
    log_action(f"Deleted Department {name}", request.user_id)
    return jsonify({'message': 'Department deleted successfully'}), 200
