from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Create test user
    new_user = User(
        username='testuser', 
        email='test@example.com', 
        password_hash=generate_password_hash('password123')
    )
    db.session.add(new_user)
    db.session.commit()
    print('Test user created with ID:', new_user.id)