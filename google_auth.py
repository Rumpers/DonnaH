import json
import os

import requests
from flask import Blueprint, redirect, request, url_for, flash, session
from flask_login import login_required, login_user, current_user
from oauthlib.oauth2 import WebApplicationClient

from app import db
from models import User

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# For the Google OAuth redirect URI
# 1. We need to use the correct authorized redirect URI from the API console
# 2. For a Replit environment, we'll need to ask the user to add the correct URI to the API console
REPLIT_DEV_DOMAIN = os.environ.get("REPLIT_DEV_DOMAIN", "")

# Print debugging information about the redirect URI
print(f"REPLIT_DEV_DOMAIN: {REPLIT_DEV_DOMAIN}")
replit_redirect_uri = f"https://{REPLIT_DEV_DOMAIN}/google_login/callback" if REPLIT_DEV_DOMAIN else None
print(f"Replit Redirect URI: {replit_redirect_uri}")

client = WebApplicationClient(GOOGLE_CLIENT_ID)

google_auth = Blueprint("google_auth", __name__)


@google_auth.route("/google_login")
@login_required
def login():
    """
    Google OAuth login route - initiates the OAuth flow.
    User must be logged in to connect their Google account.
    """
    # Get Google's provider config
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Create the OAuth request URL with proper scopes
    # Check if we have a Replit domain to use as redirect URI
    replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
    if replit_domain:
        redirect_uri = f"https://{replit_domain}/google_login/callback"
    else:
        # Fallback to localhost if not running on Replit
        redirect_uri = "http://localhost"
    
    print(f"Using redirect URI: {redirect_uri}")
    
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=redirect_uri,
        scope=[
            "openid", 
            "email", 
            "profile",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/drive"
        ],
    )
    
    # Store the current user's ID in the session to associate the Google credentials
    # with the correct user after the OAuth flow completes
    session['user_id_for_google_auth'] = current_user.id
    
    return redirect(request_uri)


@google_auth.route("/google_login/callback")
def callback():
    """Handle the OAuth callback from Google"""
    # Get the authorization code from the callback
    code = request.args.get("code")
    if not code:
        flash("Authentication failed: No authorization code received", "danger")
        return redirect(url_for("dashboard"))
    
    # Get Google's provider configuration
    google_provider_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare the token exchange request
    # Must use the same redirect URI as in the authorization request
    replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
    if replit_domain:
        redirect_uri = f"https://{replit_domain}/google_login/callback"
    else:
        # Fallback to localhost if not running on Replit
        redirect_uri = "http://localhost"
        
    print(f"Token exchange using redirect URI: {redirect_uri}")
    
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=redirect_uri,
        code=code,
    )
    
    # Exchange the authorization code for tokens
    # Use basic auth by adding client_id and client_secret to the body instead
    body_with_auth = body + f"&client_id={GOOGLE_CLIENT_ID}&client_secret={GOOGLE_CLIENT_SECRET}"
    
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body_with_auth
    )

    # Parse the token response
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Get the user's information from Google
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    userinfo = userinfo_response.json()

    # Verify the user's email
    if not userinfo.get("email_verified"):
        flash("User email not verified by Google", "danger")
        return redirect(url_for("dashboard"))

    # Get the user's Google email and name
    google_email = userinfo["email"]
    google_name = userinfo.get("given_name", "")

    # Retrieve the user ID from session
    user_id = session.get('user_id_for_google_auth')
    
    if not user_id:
        flash("Authentication failed: Session expired", "danger")
        return redirect(url_for("dashboard"))
    
    # Clear the session variable
    session.pop('user_id_for_google_auth', None)
    
    # Get the user from database
    user = User.query.get(user_id)
    
    if not user:
        flash("Authentication failed: User not found", "danger")
        return redirect(url_for("dashboard"))
    
    # Store the token information in the user's record
    user.google_credentials = json.dumps(token_response.json())
    db.session.commit()
    
    flash(f"Successfully connected Google account: {google_email}", "success")
    return redirect(url_for("dashboard"))


@google_auth.route("/google_disconnect")
@login_required
def disconnect():
    """Disconnect Google account from user profile"""
    if current_user.google_credentials:
        current_user.google_credentials = None
        db.session.commit()
        flash("Google account disconnected successfully", "success")
    else:
        flash("No Google account connected", "warning")
    
    return redirect(url_for("dashboard"))