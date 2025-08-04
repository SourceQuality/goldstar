# main.py
import os
import logging
from flask import Flask, request, redirect, session, render_template, url_for, flash
from urllib.parse import urlparse
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils
import psycopg2
import smtplib
from email.mime.text import MIMEText

# Configure logging to output to stdout, which will be visible in `docker logs`
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

app = Flask(__name__)
# It's crucial to set a secret key for session management.
# In a real app, this should be a long, random string stored securely.
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_very_secret_key_that_should_be_changed')

# --- Function Definitions ---

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    # Create users table to store user information
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Create gold_stars table to track stars given and received
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gold_stars (
            id SERIAL PRIMARY KEY,
            giver_email VARCHAR(255) REFERENCES users(email),
            receiver_email VARCHAR(255) REFERENCES users(email),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Database initialized successfully.")

def init_saml_auth(req):
    """
    Initializes the SAML authentication object by building the settings
    dynamically from environment variables.
    """
    settings = {
        # If 'strict' is True, then the Python Toolkit will reject unsigned
        # or unencrypted messages if it expects them signed or encrypted
        "strict": False,
        "debug": True, # Set to False in production
        "sp": {
            "entityId": os.environ.get('SAML_SP_ENTITY_ID', 'gold-star-app-local'),
            "assertionConsumerService": {
                "url": os.environ.get('SAML_SP_ACS_URL', 'http://localhost:5000/saml/acs'),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
            },
            # Optional but recommended for logout functionality
            "singleLogoutService": {
                "url": os.environ.get('SAML_SP_SLS_URL', 'http://localhost:5000/logout'),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
        },
        "idp": {
            "entityId": os.environ.get('SAML_IDP_ENTITY_ID'),
            "singleSignOnService": {
                "url": os.environ.get('SAML_IDP_SSO_URL'),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            # Optional if your IdP supports Single Logout
            "singleLogoutService": {
                 "url": os.environ.get('SAML_IDP_SLO_URL', ''),
                 "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
            },
            "x509cert": os.environ.get('SAML_IDP_X509_CERT')
        },
        # --- MODIFIED: Add security settings to support passwordless auth ---
        "security": {
            "requestedAuthnContext": False
        }
    }
    auth = OneLogin_Saml2_Auth(req, old_settings=settings)
    return auth

def prepare_flask_request(request):
    """Prepares a Flask request object for the SAML library."""
    url_data = urlparse(request.url)
    return {
        'https': 'on' if request.scheme == 'https' else 'off',
        'http_host': request.host,
        'server_port': url_data.port,
        'script_name': request.path,
        'get_data': request.args.copy(),
        'post_data': request.form.copy(),
        'query_string': request.query_string
    }

def send_notification_email(receiver_email, giver_name):
    """Sends an email notification to the star recipient with enhanced debugging."""
    logging.debug("Attempting to send notification email.")
    
    try:
        # --- Load SMTP Configuration ---
        smtp_server = os.environ.get('SMTP_SERVER')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_user = os.environ.get('SMTP_USER')
        smtp_password = os.environ.get('SMTP_PASSWORD')
        sender_email = os.environ.get('SMTP_SENDER_EMAIL', 'noreply@goldstar.com')

        # --- Log Configuration for Debugging ---
        logging.debug(f"SMTP Server: {smtp_server}")
        logging.debug(f"SMTP Port: {smtp_port}")
        logging.debug(f"SMTP User: {'SET' if smtp_user else 'NOT SET'}")
        # Do not log the password itself for security reasons.
        logging.debug(f"SMTP Password: {'SET' if smtp_password else 'NOT SET'}")
        logging.debug(f"Sender Email: {sender_email}")

        if not all([smtp_server, smtp_port, smtp_user, smtp_password, sender_email]):
            logging.warning("Email not sent: SMTP settings are not fully configured.")
            return

        # --- Construct Email Message ---
        subject = "You've Received a Gold Star! ⭐"
        body = f"Congratulations!\n\nYou have received a gold star from {giver_name}.\n\nKeep up the great work!\n\nThe Gold Star Team"
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = receiver_email

        # --- Send Email with SMTP Debugging ---
        logging.debug(f"Connecting to SMTP server at {smtp_server}:{smtp_port}")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            # Enable SMTP debug output to print the conversation with the server
            server.set_debuglevel(1)
            
            logging.debug("Starting TLS...")
            server.starttls()
            
            logging.debug(f"Logging in as {smtp_user}...")
            server.login(smtp_user, smtp_password)
            
            logging.debug(f"Sending email to {receiver_email} from {sender_email}")
            server.sendmail(sender_email, [receiver_email], msg.as_string())
            
            logging.info(f"Notification email successfully sent to {receiver_email}")

    except Exception as e:
        # Log the full exception details
        logging.error("Error sending email:", exc_info=True)


# --- Route Definitions ---

@app.route('/')
def index():
    """Main page, shows user info if logged in."""
    if 'samlUserdata' in session:
        user_data = session['samlUserdata']
        name_id = session['samlNameId']
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Fetch stars received
        cur.execute("SELECT COUNT(*) FROM gold_stars WHERE receiver_email = %s;", (name_id,))
        stars_received = cur.fetchone()[0]

        # Fetch all users for giving stars
        cur.execute("SELECT email, name FROM users WHERE email != %s;", (name_id,))
        all_users = cur.fetchall()

        cur.close()
        conn.close()

        return render_template('index.html', user=user_data, name_id=name_id, stars=stars_received, all_users=all_users)
    else:
        return redirect(url_for('login'))

@app.route('/login')
def login():
    """Initiates the SAML login process, forcing re-authentication."""
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    # By setting force_authn=True, we are requesting that the IdP force
    # the user to re-authenticate, even if they have an active session.
    return redirect(auth.login(force_authn=True))

@app.route('/saml/acs', methods=['POST'])
def saml_acs():
    """Assertion Consumer Service endpoint."""
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    auth.process_response()
    errors = auth.get_errors()

    if not errors:
        session['samlUserdata'] = auth.get_attributes()
        session['samlNameId'] = auth.get_nameid()
        session['samlSessionIndex'] = auth.get_session_index()
        
        # --- User Provisioning ---
        # On successful login, create or update the user in our database.
        name_id = session['samlNameId']
        user_attributes = session['samlUserdata']
        # Entra ID typically sends claims via a schema URL
        first_name = user_attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname', [''])[0]
        last_name = user_attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname', [''])[0]
        full_name = f"{first_name} {last_name}".strip()

        conn = get_db_connection()
        cur = conn.cursor()
        # Use ON CONFLICT to prevent errors if the user already exists (upsert)
        cur.execute("""
            INSERT INTO users (email, name) VALUES (%s, %s)
            ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name;
        """, (name_id, full_name))
        conn.commit()
        cur.close()
        conn.close()
        # --- End User Provisioning ---
        
        # The RelayState logic can cause a redirect loop if it points back to the
        # login page. After a successful SAML assertion, we should always
        # redirect the user to the main application page.
        return redirect(url_for('index'))
    else:
        return f"Error when processing SAML response: {', '.join(errors)}"

@app.route('/give_star', methods=['POST'])
def give_star():
    """Endpoint to give a star to a user."""
    if 'samlNameId' not in session:
        return redirect(url_for('login'))

    giver_email = session['samlNameId']
    receiver_email = request.form.get('receiver_email')

    if not receiver_email:
        flash('Please select a person to give a star to.', 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO gold_stars (giver_email, receiver_email) VALUES (%s, %s);", (giver_email, receiver_email))
    conn.commit()

    # Get giver's name for the notification
    cur.execute("SELECT name FROM users WHERE email = %s;", (giver_email,))
    giver_name = cur.fetchone()[0]
    
    cur.close()
    conn.close()

    # Send the notification email
    send_notification_email(receiver_email, giver_name)

    flash('Gold star awarded successfully!', 'success')
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """
    Handles the SAML Single Logout (SLO) process.
    This endpoint serves two purposes:
    1. Initiates the logout when a user clicks a "logout" link.
    2. Processes the LogoutResponse sent back by the Identity Provider (IdP).
    """
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    
    return_to = url_for('login')

    # Case 1: Processing a LogoutResponse from the IdP.
    # The IdP sends this after it has logged the user out of its own session.
    if 'SAMLResponse' in request.args:
        # The process_slo method validates the LogoutResponse.
        # We provide a callback function (`lambda: session.clear()`) that
        # the library will call to clear our local application session
        # after it has successfully validated the response.
        auth.process_slo(delete_session_cb=lambda: session.clear())
        errors = auth.get_errors()
        if not errors:
            # SLO was successful. The user is fully logged out.
            flash('You have been successfully logged out.', 'success')
            return redirect(return_to)
        else:
            # Log any errors that occurred during the SLO process.
            logging.error(f"Error processing SAML LogoutResponse: {', '.join(errors)}")
            flash(f"An error occurred during logout.", 'error')
            return redirect(return_to)

    # Case 2: A user from our app is initiating the logout.
    # We must not clear the session here. We need the session data to build
    # the LogoutRequest that we send to the IdP.
    name_id = session.get('samlNameId')
    session_index = session.get('samlSessionIndex')
    
    # If a Single Logout URL is configured, we initiate the SAML SLO flow.
    slo_url = auth.get_slo_url()
    if slo_url:
        # This redirects the user to the IdP's logout endpoint.
        # The IdP will then redirect back to this same '/logout' URL,
        # which will be handled by Case 1 above.
        return redirect(auth.logout(name_id=name_id, session_index=session_index))
    else:
        # If no SLO is configured, we can only perform a local logout.
        session.clear()
        flash('You have been logged out locally.', 'success')
        return redirect(return_to)


# --- Initialize the database after all functions are defined ---
# This ensures that init_db() can find get_db_connection().
init_db()

# When running in production (e.g., via Gunicorn), the __name__ will not be
# '__main__', so the app.run() block will not be executed. Gunicorn will
# directly use the 'app' object defined in this file.
if __name__ == "__main__":
    # This block is for local development only.
    # The FLASK_ENV environment variable is used to determine the mode.
    is_development = os.environ.get('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=5000, debug=is_development)
