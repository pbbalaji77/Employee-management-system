from flask import Blueprint, request, jsonify, render_template, session
from backend.auth import token_required, login_required, role_required, api_role_required
from backend.services.ai_service import (
    ai_employee_search, 
    ai_dashboard_assistant, 
    ai_resume_screening, 
    ai_employee_insights
)

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/ai/search')
@login_required
def ai_search_view():
    return render_template('ai_search.html')

# ----------------- REST APIs -----------------

@ai_bp.route('/api/ai/search', methods=['GET'])
@token_required
def api_ai_search():
    query = request.args.get('query')
    if not query:
        return jsonify({'message': 'Query parameter is required'}), 400
        
    results = ai_employee_search(query)
    return jsonify(results), 200

@ai_bp.route('/api/ai/assistant', methods=['POST'])
@token_required
def api_ai_assistant():
    data = request.get_json() or {}
    message = data.get('message')
    if not message:
        return jsonify({'message': 'Message body is required'}), 400
        
    response = ai_dashboard_assistant(message)
    return jsonify({'response': response}), 200

@ai_bp.route('/api/ai/screen-resume', methods=['POST'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_screen_resume():
    """Upload a resume file and screen it using AI rules"""
    if 'file' not in request.files:
        return jsonify({'message': 'No file uploaded'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
        
    role = request.form.get('role', 'Software Engineer')
    
    try:
        # Extract text content safely from the file
        filename = file.filename
        content_bytes = file.read()
        
        # Safe ASCII decoding to extract visible texts for keyword matching
        resume_text = content_bytes.decode('utf-8', errors='ignore')
        if len(resume_text.strip()) < 20: # Fallback to ascii/latin1 decode
            resume_text = content_bytes.decode('latin-1', errors='ignore')
            
        report = ai_resume_screening(resume_text, target_role=role)
        report['filename'] = filename
        report['role'] = role
        
        return jsonify(report), 200
    except Exception as e:
        return jsonify({'message': f'Error reading resume file: {str(e)}'}), 500

@ai_bp.route('/api/ai/insights', methods=['GET'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_get_insights():
    """Get attrition risk predictions and insights for active employees"""
    insights = ai_employee_insights()
    return jsonify(insights), 200
