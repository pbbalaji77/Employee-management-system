from flask import request
from backend.database import db
from backend.models import AuditLog

def log_action(action, user_id=None):
    """
    Log an administrative or user action to the audit logs.
    """
    try:
        ip = request.remote_addr if request else "System"
        ua = request.user_agent.string if request and request.user_agent else "System"
        
        # If user_id is not passed, check if session has it (implemented in route/auth handlers)
        if not user_id:
            from flask import session
            user_id = session.get('user_id')
            
        log = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=ip,
            user_agent=ua
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Error writing audit log: {str(e)}")
        db.session.rollback()
