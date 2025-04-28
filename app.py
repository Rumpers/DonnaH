import os
import logging
import secrets
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
login_manager.session_protection = "strong"

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
import json
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
    
    logger.debug("Registration form submitted")
    
    # Log all form data to troubleshoot
    form_data = dict(request.form)
    # Remove password from logs for security
    if 'password' in form_data:
        form_data['password'] = '********'
    if 'confirm_password' in form_data:
        form_data['confirm_password'] = '********'
    logger.debug(f"All form data: {form_data}")
    
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    logger.debug(f"Form data: username={username}, email={email}")
    
    # Validate form data
    if not all([username, email, password, confirm_password]):
        logger.warning("Missing required fields in registration form")
        flash('All fields are required.', 'danger')
        return redirect(url_for('auth'))
    
    if password != confirm_password:
        logger.warning("Passwords do not match in registration form")
        flash('Passwords do not match.', 'danger')
        return redirect(url_for('auth'))
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        logger.info(f"Email {email} already registered")
        flash('Email already registered. Please login instead.', 'warning')
        return redirect(url_for('auth'))
    
    try:
        # Create new user
        new_user = User(
            username=username, 
            email=email, 
            password_hash=generate_password_hash(password)
        )
        
        logger.debug(f"Created new user object: {new_user}")
        
        db.session.add(new_user)
        db.session.commit()
        logger.debug(f"User committed to database with ID: {new_user.id}")
        
        # Log the user in
        login_successful = login_user(new_user)
        logger.debug(f"login_user result: {login_successful}")
        
        session['user_id'] = new_user.id
        logger.debug(f"Session user_id set to: {session.get('user_id')}")
        
        logger.info(f"User {username} (ID: {new_user.id}) registered successfully")
        flash('Registration successful! Welcome to OpenManus Assistant.', 'success')
        
        # Debug current_user after login
        logger.debug(f"current_user.is_authenticated: {current_user.is_authenticated}")
        logger.debug(f"current_user.id: {current_user.id if current_user.is_authenticated else 'Not authenticated'}")
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        db.session.rollback()
        flash(f'An error occurred during registration: {str(e)}', 'danger')
        return redirect(url_for('auth'))

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
    
    # Get memory and document counts
    memory_count = MemoryEntry.query.filter_by(user_id=current_user.id).count()
    document_count = Document.query.filter_by(user_id=current_user.id).count()
    
    # Get the Replit domain for Google OAuth redirect URI
    replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
    
    return render_template(
        'dashboard.html', 
        memory_count=memory_count, 
        document_count=document_count,
        replit_domain=replit_domain
    )

@app.route('/start_bot', methods=['POST'])
@login_required
def start_bot():
    try:
        telegram_token = os.environ.get("TELEGRAM_TOKEN")
        if not telegram_token:
            flash('Telegram token not configured. Using demo mode.', 'warning')
            # In demo mode, we will simulate the bot
            flash('Telegram bot initialized in demo mode. Some features may be limited.', 'info')
            return redirect(url_for('dashboard'))
        
        is_registered = telegram_bot.initialize_bot(telegram_token)
        if is_registered:
            flash('Telegram bot registered successfully. The bot is ready to handle commands but may not actively poll for updates in this environment.', 'success')
        else:
            flash('Failed to register Telegram bot. Check logs for details.', 'danger')
    except Exception as e:
        logger.error(f"Error registering Telegram bot: {e}")
        flash(f'Error registering Telegram bot: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/debug_users')
def debug_users():
    from models import User
    try:
        users = User.query.all()
        user_data = [
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'created_at': str(user.created_at) if hasattr(user, 'created_at') else None
            }
            for user in users
        ]
        return jsonify({"user_count": len(users), "users": user_data})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/try_login')
def try_login():
    """Helper route to automatically log in as the first user"""
    from models import User
    try:
        user = User.query.first()
        if not user:
            return jsonify({"error": "No users found in database"})
        
        # Log the user in
        login_successful = login_user(user)
        session['user_id'] = user.id
        logger.info(f"Auto-login successful for user {user.username} (ID: {user.id})")
        logger.debug(f"login_user result: {login_successful}")
        logger.debug(f"Session user_id: {session.get('user_id')}")
        logger.debug(f"current_user.is_authenticated: {current_user.is_authenticated}")
        
        flash(f'Auto-login successful! Welcome back, {user.username}.', 'success')
        return redirect(url_for('dashboard'))
    except Exception as e:
        logger.error(f"Error during auto-login: {str(e)}")
        return jsonify({"error": str(e)})
        
@app.route('/dashboard_direct')
def dashboard_direct():
    """A version of the dashboard without the @login_required decorator for testing"""
    from models import MemoryEntry, Document, User
    
    try:
        # Get the first user for testing
        user = User.query.first()
        if not user:
            flash('No users found in database', 'danger')
            return redirect(url_for('auth'))
            
        # Get memory and document counts
        memory_count = MemoryEntry.query.filter_by(user_id=user.id).count()
        document_count = Document.query.filter_by(user_id=user.id).count()
        
        # Get the Replit domain for Google OAuth redirect URI
        replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
        
        # Set a flag to indicate this is a direct access (bypass login check)
        is_direct_access = True
        
        return render_template(
            'dashboard.html', 
            memory_count=memory_count, 
            document_count=document_count,
            replit_domain=replit_domain,
            is_direct_access=is_direct_access,
            current_user=user  # Pass the user directly
        )
    except Exception as e:
        logger.error(f"Error accessing dashboard directly: {str(e)}")
        return jsonify({"error": str(e)})

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
        
        # Check if Telegram token is available and register the bot
        telegram_token = os.environ.get("TELEGRAM_TOKEN")
        if telegram_token:
            try:
                # Just register the bot without trying to start polling
                # This will allow commands to work but won't actively fetch updates
                # For full functionality, the user should set up webhooks
                is_registered = telegram_bot.initialize_bot(telegram_token)
                if is_registered:
                    logger.info("Telegram bot registered successfully at startup")
                else:
                    logger.error("Failed to register Telegram bot at startup")
            except Exception as e:
                logger.error(f"Error registering Telegram bot: {e}")
        
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing services: {e}")

@app.route('/inspect_users')
def inspect_users():
    from models import User
    users = User.query.all()
    for user in users:
        print(f'User ID: {user.id}, Username: {user.username}, Email: {user.email}')
    return "User information printed to console."

@app.route('/setup_telegram_webhook', methods=['POST'])
def setup_telegram_webhook():
    """Set up the Telegram webhook."""
    try:
        telegram_token = os.environ.get("TELEGRAM_TOKEN")
        replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
        
        if not telegram_token:
            flash('Telegram token not configured. Cannot set up webhook.', 'danger')
            return redirect(url_for('dashboard'))
            
        if not replit_domain:
            flash('Replit domain not available. Cannot set up webhook.', 'danger')
            return redirect(url_for('dashboard'))
            
        # Initialize bot if not already initialized
        is_registered = telegram_bot.initialize_bot(telegram_token)
        if not is_registered:
            flash('Failed to initialize Telegram bot. Check logs for details.', 'danger')
            return redirect(url_for('dashboard'))
            
        # Set up webhook
        webhook_url = f"https://{replit_domain}/telegram_webhook"
        success = telegram_bot.setup_webhook(webhook_url)
        
        if success:
            flash(f'Telegram webhook set up successfully at {webhook_url}', 'success')
        else:
            flash('Failed to set up webhook. Check logs for details.', 'danger')
            
    except Exception as e:
        logger.error(f"Error setting up webhook: {str(e)}")
        flash(f'Error setting up webhook: {str(e)}', 'danger')
        
    return redirect(url_for('dashboard'))
    
@app.route('/remove_telegram_webhook', methods=['POST'])
def remove_telegram_webhook():
    """Remove the Telegram webhook."""
    try:
        telegram_token = os.environ.get("TELEGRAM_TOKEN")
        
        if not telegram_token:
            flash('Telegram token not configured. Cannot remove webhook.', 'danger')
            return redirect(url_for('dashboard'))
            
        # Initialize bot if not already initialized
        is_registered = telegram_bot.initialize_bot(telegram_token)
        if not is_registered:
            flash('Failed to initialize Telegram bot. Check logs for details.', 'danger')
            return redirect(url_for('dashboard'))
            
        # Remove webhook
        success = telegram_bot.remove_webhook()
        
        if success:
            flash('Telegram webhook removed successfully', 'success')
        else:
            flash('Failed to remove webhook. Check logs for details.', 'danger')
            
    except Exception as e:
        logger.error(f"Error removing webhook: {str(e)}")
        flash(f'Error removing webhook: {str(e)}', 'danger')
        
    return redirect(url_for('dashboard'))
    
@app.route('/telegram_webhook', methods=['POST'])
async def telegram_webhook():
    """
    Handle Telegram webhook requests.
    This route receives updates from Telegram when a user interacts with the bot.
    """
    try:
        # Get the update data from the request
        update_data = json.loads(request.data)
        logger.debug(f"Received update from Telegram: {update_data}")
        
        # Process the update asynchronously
        await telegram_bot.process_update(update_data)
        
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error processing Telegram update: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
