import os
from flask import Flask, session
from dotenv import load_dotenv
from backend.database import db

# Load environment variables
load_dotenv()

def create_app(config_name=None):
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )

    # Configuration loading
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key_for_ems_system_12345')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///database/ems.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216)) # 16 MB

    # Parse and override database path if SQLite to make sure parent folder exists
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if db_uri.startswith('sqlite:///') and db_uri != 'sqlite:///:memory:':
        db_path = db_uri.replace('sqlite:///', '')
        # Check if relative or absolute path, then make directory
        if not os.path.isabs(db_path):
            # Resolve relative to root workspace
            db_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), db_path))
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Initialize extensions
    db.init_app(app)



    # Context processors to share variables in HTML views
    @app.context_processor
    def inject_global_data():
        unread = 0
        if 'user_id' in session:
            try:
                from backend.models import Notification
                unread = Notification.query.filter_by(is_read=False).count()
            except Exception:
                pass
        return {
            'unread_notifications_count': unread
        }

    # Register Blueprints
    from backend.routes.auth_routes import auth_bp
    from backend.routes.employee_routes import employee_bp
    from backend.routes.department_routes import department_bp
    from backend.routes.attendance_routes import attendance_bp
    from backend.routes.leave_routes import leave_bp
    from backend.routes.payroll_routes import payroll_bp
    from backend.routes.performance_routes import performance_bp
    from backend.routes.document_routes import document_bp
    from backend.routes.report_routes import report_bp
    from backend.routes.ai_routes import ai_bp
    from backend.routes.settings_routes import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(department_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(leave_bp)
    app.register_blueprint(payroll_bp)
    app.register_blueprint(performance_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(settings_bp)

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        from flask import render_template
        return render_template('login.html'), 404

    return app
