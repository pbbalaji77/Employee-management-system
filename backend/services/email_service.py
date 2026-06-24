import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Path to log emails if SMTP fails or is in mock mode
MOCK_EMAIL_FILE = os.path.join('static', 'uploads', 'sent_emails.txt')

def send_email(subject, recipient_email, html_content):
    """
    General helper to send emails via SMTP. Falls back to writing to file for local testing.
    """
    # Ensure upload directory exists
    os.makedirs(os.path.dirname(MOCK_EMAIL_FILE), exist_ok=True)

    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = os.getenv('SMTP_PORT', '2525')
    smtp_user = os.getenv('SMTP_USERNAME')
    smtp_password = os.getenv('SMTP_PASSWORD')
    smtp_from = os.getenv('SMTP_FROM_EMAIL', 'noreply@enterprise-ems.com')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = smtp_from
    msg['To'] = recipient_email
    msg.attach(MIMEText(html_content, 'html'))

    # If it is mock credentials, skip SMTP
    if not smtp_server or 'mock' in smtp_server.lower() or not smtp_user or 'mock' in smtp_user.lower():
        _log_to_mock_file(recipient_email, subject, html_content)
        return True

    try:
        # Try sending via SMTP
        with smtplib.SMTP(smtp_server, int(smtp_port), timeout=5) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, recipient_email, msg.as_string())
        return True
    except Exception as e:
        print(f"SMTP failed, logging email to file: {str(e)}")
        _log_to_mock_file(recipient_email, subject, html_content)
        return False

def _log_to_mock_file(to, subject, body):
    """
    Log email details to local file for development verification.
    """
    try:
        with open(MOCK_EMAIL_FILE, 'a', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write(f"TIMESTAMP : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"TO        : {to}\n")
            f.write(f"SUBJECT   : {subject}\n")
            f.write("CONTENT   :\n")
            f.write(body)
            f.write("\n" + "=" * 60 + "\n\n")
    except Exception as e:
        print(f"Failed to log email to mock file: {e}")

def send_welcome_email(employee_name, email, temp_password):
    subject = "Welcome to Enterprise EMS - Account Activated"
    html = f"""
    <h2>Welcome {employee_name},</h2>
    <p>Your official employee portal account has been created successfully.</p>
    <p>You can login using the following credentials:</p>
    <ul>
        <li><b>URL:</b> http://localhost:5000/login</li>
        <li><b>Username/Email:</b> {email}</li>
        <li><b>Temporary Password:</b> {temp_password}</li>
    </ul>
    <p>Please change your password immediately after logging in for security.</p>
    <br>
    <p>Best regards,<br>Enterprise HR Team</p>
    """
    return send_email(subject, email, html)

def send_leave_status_email(employee_email, employee_name, leave_type, start_date, end_date, status, manager_name, reason=None):
    subject = f"Leave Request {status} - Enterprise EMS"
    html = f"""
    <h2>Hello {employee_name},</h2>
    <p>Your leave request has been reviewed by your Manager ({manager_name}).</p>
    <ul>
        <li><b>Leave Type:</b> {leave_type}</li>
        <li><b>Duration:</b> {start_date} to {end_date}</li>
        <li><b>Status:</b> <b style="color: {'green' if status == 'Approved' else 'red'};">{status}</b></li>
    </ul>
    """
    if reason:
        html += f"<p><b>Comments:</b> {reason}</p>"
    html += "<br><p>Best regards,<br>System Notification Agent</p>"
    return send_email(subject, employee_email, html)

def send_payroll_notification_email(employee_name, email, month, year, net_salary):
    subject = f"Payslip Generated for {month}/{year} - Enterprise EMS"
    html = f"""
    <h2>Hello {employee_name},</h2>
    <p>Your payslip for the period {month}/{year} has been generated and approved.</p>
    <ul>
        <li><b>Net Salary Disbursed:</b> INR {net_salary:.2f}</li>
    </ul>
    <p>You can download the PDF payslip directly from your Employee Portal under the "Payroll" tab.</p>
    <br>
    <p>Best regards,<br>Finance Department</p>
    """
    return send_email(subject, email, html)

def send_password_reset_email(email, reset_token):
    subject = "Password Reset Request - Enterprise EMS"
    reset_url = f"http://localhost:5000/reset_password?token={reset_token}"
    html = f"""
    <h2>Password Reset Request</h2>
    <p>We received a request to reset your account password. If you didn't make this request, simply ignore this email.</p>
    <p>Otherwise, click the link below to set a new password:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>This link is valid for 1 hour.</p>
    <br>
    <p>Best regards,<br>IT Security Team</p>
    """
    return send_email(subject, email, html)
