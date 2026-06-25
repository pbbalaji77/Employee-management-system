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

def free_port(port):
    import subprocess
    import os
    try:
        # Find PIDs using Windows netstat
        cmd = "netstat -ano"
        output = subprocess.check_output(cmd, shell=True).decode()
        pids = set()
        current_pid = os.getpid()
        
        for line in output.strip().split('\n'):
            if "LISTENING" in line and f":{port}" in line:
                parts = line.strip().split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit():
                        pid_num = int(pid)
                        if pid_num != current_pid:
                            pids.add(pid_num)
        
        for pid in pids:
            print(f"Port {port} is occupied by PID {pid}. Terminating it to prevent conflict...")
            subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
    except Exception:
        pass

if __name__ == '__main__':
    # Start local development server
    port = int(os.getenv('PORT', 5000))
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        free_port(port)
    app.run(host='0.0.0.0', port=port, debug=True)
