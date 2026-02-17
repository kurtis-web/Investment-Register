"""
Authentication module for Family Office Wealth OS.
Simple password-based authentication using streamlit-authenticator.
"""

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from pathlib import Path
import bcrypt
import os

# Config file path
AUTH_CONFIG_PATH = Path(__file__).parent.parent / "data" / "auth_config.yaml"


def get_password_hash(password: str) -> str:
    """Hash a password for storage."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_default_config():
    """Create default authentication config with a default user."""
    # Default password is 'wealthos2024' - CHANGE THIS AFTER FIRST LOGIN
    default_hash = get_password_hash("wealthos2024")

    config = {
        'cookie': {
            'expiry_days': 30,
            'key': 'wealth_os_auth_key_random_string_12345',
            'name': 'wealth_os_auth'
        },
        'credentials': {
            'usernames': {
                'admin': {
                    'email': 'admin@example.com',
                    'name': 'Administrator',
                    'password': default_hash
                }
            }
        },
        'preauthorized': {
            'emails': []
        }
    }

    # Ensure directory exists
    os.makedirs(os.path.dirname(AUTH_CONFIG_PATH), exist_ok=True)

    with open(AUTH_CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    # Restrict file permissions
    os.chmod(AUTH_CONFIG_PATH, 0o600)

    return config


def load_config():
    """Load authentication config, creating default if needed."""
    if not AUTH_CONFIG_PATH.exists():
        return create_default_config()

    with open(AUTH_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def save_config(config):
    """Save authentication config."""
    with open(AUTH_CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


def check_authentication():
    """
    Check if user is authenticated.
    Returns True if authenticated, False otherwise.
    Also handles login UI.
    """
    config = load_config()

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config.get('preauthorized', {})
    )

    # Custom login styling
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 2rem;
        background: #111;
        border-radius: 12px;
        border: 1px solid #333;
    }
    </style>
    """, unsafe_allow_html=True)

    name, authentication_status, username = authenticator.login('Login', 'main')

    if authentication_status is False:
        st.error('Username/password is incorrect')
        return False, None, authenticator

    if authentication_status is None:
        st.markdown("""
        <div style="text-align: center; margin-top: 50px;">
            <h1 style="color: #fff;">Family Office Wealth OS</h1>
            <p style="color: #888;">Please enter your credentials to continue</p>
        </div>
        """, unsafe_allow_html=True)
        return False, None, authenticator

    return True, username, authenticator


def show_logout(authenticator):
    """Show logout button in sidebar."""
    with st.sidebar:
        if st.button("Logout", use_container_width=True):
            authenticator.logout('Logout', 'sidebar')
            st.rerun()


def add_user(username: str, name: str, email: str, password: str):
    """Add a new user to the system."""
    config = load_config()

    if username in config['credentials']['usernames']:
        return False, "Username already exists"

    config['credentials']['usernames'][username] = {
        'email': email,
        'name': name,
        'password': get_password_hash(password)
    }

    save_config(config)
    return True, "User added successfully"


def change_password(username: str, new_password: str):
    """Change a user's password."""
    config = load_config()

    if username not in config['credentials']['usernames']:
        return False, "User not found"

    config['credentials']['usernames'][username]['password'] = get_password_hash(new_password)
    save_config(config)
    return True, "Password changed successfully"


def get_all_users():
    """Get list of all usernames."""
    config = load_config()
    return list(config['credentials']['usernames'].keys())
