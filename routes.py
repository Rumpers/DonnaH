import os
from flask import session
from app import app, db
from replit_auth import require_login, make_replit_blueprint
from flask_login import current_user

app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

# Make session permanent and set a secure cookie
@app.before_request
def make_session_permanent():
    session.permanent = True
    # Set a session key if not already set
    if 'SESSION_SECRET' not in os.environ:
        # If no secret key is set in environment, warn but continue
        app.logger.warning("SESSION_SECRET environment variable not set!")
    app.logger.debug("Session setup complete")