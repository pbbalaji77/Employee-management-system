import re
from backend.database import db
from backend.models import Notification

def create_notification(user_id, title, message, notification_type='info'):
    """
    Utility helper to inject system notifications for users.
    """
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type
        )
        db.session.add(notif)
        db.session.commit()
        return notif
    except Exception as e:
        print(f"Error creating notification: {e}")
        db.session.rollback()
        return None

def validate_email(email):
    """
    Regex verification for email strings.
    """
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None
