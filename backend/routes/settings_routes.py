import os
import shutil
import glob
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from backend.database import db
from backend.models import HRUser, AuditLog
from backend.auth import login_required, role_required, token_required, api_role_required
from backend.services.audit_service import log_action
from datetime import datetime

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
@login_required
def settings_view():
    db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
    backups = []
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
        backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
        if os.path.exists(backup_dir):
            files = glob.glob(os.path.join(backup_dir, '*.db'))
            for f in files:
                stat = os.stat(f)
                backups.append({
                    'filename': os.path.basename(f),
                    'size_kb': round(stat.st_size / 1024.0, 2),
                    'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
            backups.sort(key=lambda x: x['filename'], reverse=True)
            
    return render_template('settings.html', backups=backups)

@settings_bp.route('/api/settings/backup', methods=['POST'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_database_backup():
    """Create a backup of the SQLite database"""
    db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
    if not db_uri.startswith('sqlite:///'):
        return jsonify({'message': 'Backup is only supported for SQLite databases'}), 400
        
    try:
        db_path = db_uri.replace('sqlite:///', '')
        backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f"ems_backup_{timestamp}.db")
        
        shutil.copy2(db_path, backup_path)
        log_action(f"Created database backup ems_backup_{timestamp}.db", request.user_id)
        
        return jsonify({'message': 'Database backup created successfully', 'filename': f"ems_backup_{timestamp}.db"}), 201
    except Exception as e:
        return jsonify({'message': f'Backup failed: {str(e)}'}), 500

@settings_bp.route('/api/settings/restore', methods=['POST'])
@token_required
@api_role_required('Super Admin', 'HR Manager')
def api_database_restore():
    """Restore database from a backup file"""
    data = request.get_json() or {}
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'message': 'Backup filename is required'}), 400
        
    db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
    if not db_uri.startswith('sqlite:///'):
        return jsonify({'message': 'Restore is only supported for SQLite databases'}), 400
        
    try:
        db_path = db_uri.replace('sqlite:///', '')
        backup_path = os.path.join(os.path.dirname(db_path), 'backups', filename)
        
        if not os.path.exists(backup_path):
            return jsonify({'message': 'Backup file not found'}), 404
            
        db.session.remove()
        db.engine.dispose()
        
        shutil.copy2(backup_path, db_path)
        log_action(f"Restored database from backup {filename}", request.user_id)
        
        return jsonify({'message': 'Database restored successfully. Please refresh the page.'}), 200
    except Exception as e:
        return jsonify({'message': f'Restore failed: {str(e)}'}), 500
