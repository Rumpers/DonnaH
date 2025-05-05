from flask import session
from app import app, db
from replit_auth import require_login, make_replit_blueprint
from flask_login import current_user

app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True