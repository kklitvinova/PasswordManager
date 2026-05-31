import os
import json
import bcrypt

USERS_FILE = 'users.json'

def load_users() -> dict:
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users: dict):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def register_user(username: str, password: str) -> bool:
    users = load_users()
    if username in users:
        return False  # already exists
    # Hash password with bcrypt
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users[username] = {'password_hash': hashed}
    save_users(users)
    return True

def verify_user(username: str, password: str) -> bool:
    users = load_users()
    if username not in users:
        return False
    stored = users[username]['password_hash'].encode()
    return bcrypt.checkpw(password.encode(), stored)

def get_user_file(username: str) -> str:
    # Each user has their own CSV file
    return f'passwords_{username}.csv'