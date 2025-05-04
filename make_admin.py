"""
Script to make a user an admin.
"""
from app import app, db
from models import User

def make_admin(user_id=1):
    """
    Make a user an admin by user ID.
    By default, makes the first user (ID=1) an admin.
    """
    with app.app_context():
        user = User.query.get(user_id)
        if not user:
            print(f"Error: No user found with ID {user_id}")
            return False
            
        user.is_admin = True
        db.session.commit()
        print(f"Success: User '{user.username}' (ID: {user.id}) is now an admin.")
        return True

if __name__ == "__main__":
    make_admin()