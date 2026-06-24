import os
import uuid
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from backend.database import db
from backend.models import Document, Employee
from backend.auth import token_required
from backend.services.audit_service import log_action

document_bp = Blueprint('document', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------- REST APIs -----------------

@document_bp.route('/api/documents', methods=['GET'])
@token_required
def api_list_documents():
    employee_id = request.args.get('employee_id')
    
    query = Document.query
    
    if request.user_role == 'Employee':
        query = query.filter(Document.employee_id == request.employee_id)
    elif employee_id:
        query = query.filter(Document.employee_id == int(employee_id))
        
    docs = query.order_by(Document.uploaded_at.desc()).all()
    return jsonify([d.to_dict() for d in docs]), 200

@document_bp.route('/api/documents', methods=['POST'])
@token_required
def api_upload_document():
    """Upload a file document for an employee"""
    emp_id = request.args.get('employee_id', request.employee_id, type=int)
    
    # Non-admins/HR cannot upload files for other employees
    if request.user_role == 'Employee' and request.employee_id != emp_id:
        return jsonify({'message': 'Access forbidden'}), 403
        
    if 'file' not in request.files:
        return jsonify({'message': 'No file part in request'}), 400
        
    file = request.files['file']
    doc_type = request.form.get('document_type') # Resume, Certificate, etc.
    
    if file.filename == '':
        return jsonify({'message': 'No file selected'}), 400
        
    if not doc_type:
        return jsonify({'message': 'Document type is required'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{uuid.uuid4().hex[:8]}_{file.filename}")
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'documents')
        os.makedirs(upload_dir, exist_ok=True)
        
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # Save to database
        db_path = f"uploads/documents/{filename}"
        doc = Document(
            employee_id=emp_id,
            document_name=file.filename,
            document_type=doc_type,
            file_path=db_path
        )
        
        db.session.add(doc)
        db.session.commit()
        
        log_action(f"Uploaded {doc_type}: {file.filename}", request.user_id)
        return jsonify(doc.to_dict()), 201
        
    return jsonify({'message': 'File type not allowed'}), 400

@document_bp.route('/api/documents/<int:doc_id>', methods=['GET'])
@token_required
def api_download_document(doc_id):
    """View/Download a document file"""
    doc = Document.query.get_or_404(doc_id)
    
    # Check permissions
    if request.user_role == 'Employee' and request.employee_id != doc.employee_id:
        return jsonify({'message': 'Access forbidden'}), 403
        
    filepath = os.path.join(current_app.root_path, 'static', doc.file_path)
    if not os.path.exists(filepath):
        return jsonify({'message': 'File not found on system'}), 404
        
    return send_file(filepath)

@document_bp.route('/api/documents/<int:doc_id>', methods=['DELETE'])
@token_required
def api_delete_document(doc_id):
    """Remove a document from the system and delete the disk file"""
    doc = Document.query.get_or_404(doc_id)
    
    # Check permissions
    if request.user_role == 'Employee' and request.employee_id != doc.employee_id:
        return jsonify({'message': 'Access forbidden'}), 403
        
    # Delete from disk
    filepath = os.path.join(current_app.root_path, 'static', doc.file_path)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"Error deleting file from disk: {e}")
            
    name = doc.document_name
    db.session.delete(doc)
    db.session.commit()
    
    log_action(f"Deleted document: {name}", request.user_id)
    return jsonify({'message': 'Document deleted successfully'}), 200
