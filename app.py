import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///manus_assistant.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the SQLAlchemy extension
db.init_app(app)

# Import service functions after app is created to avoid circular imports
import telegram_bot  # Import but don't initialize
from google_services import initialize_google_services
from manus_integration import initialize_manus
from memory_system import initialize_memory_system
from google_auth import google_auth  # Import the Google OAuth blueprint

# Register blueprints
app.register_blueprint(google_auth)

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth', methods=['GET'])
def auth():
    return render_template('auth.html')

@app.route('/login', methods=['POST'])
def login():
    from models import User
    
    email = request.form.get('email')
    password = request.form.get('password')
    
    user = User.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        session['user_id'] = user.id
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid email or password. Please try again.', 'danger')
        return redirect(url_for('auth'))

@app.route('/register', methods=['POST'])
def register():
    from models import User
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate form data
    if not all([username, email, password, confirm_password]):
        flash('All fields are required.', 'danger')
        return redirect(url_for('auth'))
    
    if password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('auth'))
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('Email already registered. Please login instead.', 'warning')
        return redirect(url_for('auth'))
    
    # Create new user
    new_user = User(
        username=username, 
        email=email, 
        password_hash=generate_password_hash(password)
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    # Log the user in
    login_user(new_user)
    session['user_id'] = new_user.id
    flash('Registration successful! Welcome to OpenManus Assistant.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    logout_user()
    if 'user_id' in session:
        session.pop('user_id')
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    from models import MemoryEntry, Document
    return render_template('dashboard.html', MemoryEntry=MemoryEntry, Document=Document)

@app.route('/start_bot', methods=['POST'])
@login_required
def start_bot():
    
    try:
        telegram_token = os.environ.get("TELEGRAM_TOKEN")
        if not telegram_token:
            flash('Telegram token not configured. Using demo mode.', 'warning')
            # In demo mode, we will simulate the bot
            flash('Telegram bot started in demo mode. Some features may be limited.', 'info')
            return redirect(url_for('dashboard'))
        
        telegram_bot.initialize_bot(telegram_token)
        flash('Telegram bot started successfully', 'success')
    except Exception as e:
        logger.error(f"Error starting Telegram bot: {e}")
        flash(f'Error starting Telegram bot: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

# Initialize database
with app.app_context():
    # Import models
    import models
    
    # Create database tables
    db.create_all()
    
    # Initialize services
    try:
        # Initialize Google services
        initialize_google_services()
        
        # Initialize OpenManus framework
        initialize_manus()
        
        # Initialize memory system
        initialize_memory_system()
        
        # Check if Telegram token is available and start the bot automatically
        telegram_token = os.environ.get("TELEGRAM_TOKEN")
        if telegram_token:
            try:
                telegram_bot.initialize_bot(telegram_token)
                logger.info("Telegram bot started automatically on application startup")
            except Exception as e:
                logger.error(f"Error starting Telegram bot: {e}")
        
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing services: {e}")
