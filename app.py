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
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

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

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth')
def auth():
    return render_template('auth.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in first', 'warning')
        return redirect(url_for('auth'))
    return render_template('dashboard.html')

@app.route('/start_bot', methods=['POST'])
def start_bot():
    if 'user_id' not in session:
        flash('Please log in first', 'warning')
        return redirect(url_for('auth'))
    
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
        
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing services: {e}")
