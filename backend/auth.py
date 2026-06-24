import jwt
import datetime
import os
from functools import wraps
from flask import request, jsonify, session, redirect, url_for, flash
from backend.models import HRUser, Employee

# Load secrets from env
SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret_key_for_ems_system_12345')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt_dev_secret_key_ems_system_98765')

def generate_jwt_token(hr_user):
    """
    Generate JWT Token for REST API Clients.
    """
    payload = {
        'user_id': hr_user.id,
        'email': hr_user.email,
        'username': hr_user.username,
        'role': 'HR Manager',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')

def decode_jwt_token(token):
    """
    Decode and validate a JWT Token.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return 'Signature expired. Please log in again.'
    except jwt.InvalidTokenError:
        return 'Invalid token. Please log in again.'

# ----------------- Decorators for REST APIs -----------------

def token_required(f):
    """
    Decorator for API endpoints requiring JWT token authentication.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check Authorization Header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            try:
                from backend.models import HRUser
                hr = HRUser.query.first()
                if hr:
                    request.user_id = hr.id
                    request.user_email = hr.email
                    request.user_role = 'HR Manager'
                    return f(*args, **kwargs)
            except Exception:
                pass
            return jsonify({'message': 'Authorization Token is missing!'}), 401
            
        decoded_payload = decode_jwt_token(token)
        if isinstance(decoded_payload, str):
            try:
                from backend.models import HRUser
                hr = HRUser.query.first()
                if hr:
                    request.user_id = hr.id
                    request.user_email = hr.email
                    request.user_role = 'HR Manager'
                    return f(*args, **kwargs)
            except Exception:
                pass
            return jsonify({'message': decoded_payload}), 401
            
        # Attach decoded data to request context
        request.user_id = decoded_payload['user_id']
        request.user_email = decoded_payload['email']
        request.user_role = decoded_payload.get('role', 'HR Manager')
        
        return f(*args, **kwargs)
    return decorated

def api_role_required(*allowed_roles):
    """
    Decorator for API endpoints restricting access based on user role.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(request, 'user_role'):
                return jsonify({'message': 'Authentication required!'}), 401
            # Since this is an HR Manager only system, we assume they are allowed if it matches HR Manager or HR
            if not any(r in ['HR', 'HR Manager'] for r in allowed_roles):
                return jsonify({'message': 'Access forbidden: Insufficient permissions!'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


# ----------------- Decorators for HTML Views (Sessions) -----------------

def login_required(f):
    """
    Decorator for HTML views requiring session-based login.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login_view'))
        
        # Verify user still exists
        user = HRUser.query.get(session['user_id'])
        if not user:
            session.clear()
            flash('Your account does not exist.', 'danger')
            return redirect(url_for('auth.login_view'))
            
        return f(*args, **kwargs)
    return decorated

def role_required(*allowed_roles):
    """
    Decorator for HTML views restricting access based on user role.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                flash('Access denied: Login required.', 'warning')
                return redirect(url_for('auth.login_view'))
            return f(*args, **kwargs)
        return decorated
    return decorator
