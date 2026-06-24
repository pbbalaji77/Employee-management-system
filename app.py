import os
from backend import create_app
from backend.database import db

app = create_app()

# Initialize tables inside app context for local development
with app.app_context():
    try:
        db.create_all()
        print("Database tables initialized successfully.")
    except Exception as e:
        print(f"Error initializing database tables: {e}")

if __name__ == '__main__':
    # Start local development server
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
