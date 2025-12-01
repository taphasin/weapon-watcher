import time
import os
import jwt
import sqlite3
import requests
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
from passlib.context import CryptContext
from contextlib import contextmanager

SECRET_KEY = "CHANGE_ME_SECRET"
JWT_ALGO = "HS256"
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Friend's AI stream (example: MJPEG stream)
AI_STREAM_URL = "http://ai-flask:6000/stream"

app = Flask(__name__)
CORS(app)

# Database setup
def init_db():
    """Initialize the SQLite database and create users table"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create default admin user if it doesn't exist
    cursor.execute('SELECT username FROM users WHERE username = ?', ('admin',))
    if not cursor.fetchone():
        admin_password_hash = pwd_ctx.hash("admin123")
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                      ('admin', admin_password_hash))
    
    conn.commit()
    conn.close()

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_user_by_username(username):
    """Get user by username"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        return cursor.fetchone()

def create_user(username, password):
    """Create a new user"""
    password_hash = pwd_ctx.hash(password)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                          (username, password_hash))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Username already exists

def delete_user(username):
    """Delete a user"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE username = ?', (username,))
        conn.commit()
        return cursor.rowcount > 0

# ---------- Auth ----------
@app.post("/login")
def login():
    data = request.json
    if not data or not data.get("username") or not data.get("password"):
        return {"error": "Missing credentials"}, 400

    user = get_user_by_username(data["username"])
    if not user or not pwd_ctx.verify(data["password"], user["password_hash"]):
        return {"error": "Invalid credentials"}, 401

    token = jwt.encode({
        "sub": data["username"], 
        "iat": time.time(),
        "exp": time.time() + 3600  # Token expires in 1 hour
    }, SECRET_KEY, algorithm=JWT_ALGO)
    
    return {"access_token": token, "username": data["username"]}

@app.post("/register")
def register():
    data = request.json
    if not data or not data.get("username") or not data.get("password"):
        return {"error": "Missing username or password"}, 400
    
    username = data["username"].strip()
    password = data["password"]
    
    # Validate input
    if len(username) < 3:
        return {"error": "Username must be at least 3 characters long"}, 400
    
    if len(password) < 6:
        return {"error": "Password must be at least 6 characters long"}, 400
    
    # Create user
    if create_user(username, password):
        return {"message": "User created successfully"}, 201
    else:
        return {"error": "Username already exists"}, 409

@app.post("/logout")
def logout():
    # For JWT tokens, logout is typically handled client-side by removing the token
    # Server-side logout would require token blacklisting, which is more complex
    return {"message": "Logged out successfully"}

@app.post("/change-password")
def change_password():
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return {"error": "Missing or invalid authorization header"}, 401
    
    token = token[7:]  # Remove 'Bearer ' prefix
    user_data = verify_token(token)
    if not user_data:
        return {"error": "Invalid token"}, 401
    
    data = request.json
    if not data or not data.get("current_password") or not data.get("new_password"):
        return {"error": "Missing current_password or new_password"}, 400
    
    current_password = data["current_password"]
    new_password = data["new_password"]
    
    # Validate new password length
    if len(new_password) < 6:
        return {"error": "New password must be at least 6 characters long"}, 400
    
    username = user_data.get('sub')
    user = get_user_by_username(username)
    
    if not user:
        return {"error": "User not found"}, 404
    
    # Verify current password
    if not pwd_ctx.verify(current_password, user["password_hash"]):
        return {"error": "Current password is incorrect"}, 400
    
    # Update password
    new_password_hash = pwd_ctx.hash(new_password)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET password_hash = ? WHERE username = ?',
                      (new_password_hash, username))
        conn.commit()
        
        if cursor.rowcount > 0:
            return {"message": "Password changed successfully"}
        else:
            return {"error": "Failed to update password"}, 500

@app.delete("/delete-account")
def delete_account():
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return {"error": "Missing or invalid authorization header"}, 401
    
    token = token[7:]  # Remove 'Bearer ' prefix
    user_data = verify_token(token)
    if not user_data:
        return {"error": "Invalid token"}, 401
    
    username = user_data.get('sub')
    if delete_user(username):
        return {"message": "Account deleted successfully"}
    else:
        return {"error": "Account not found"}, 404

@app.get("/user-info")
def user_info():
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return {"error": "Missing or invalid authorization header"}, 401
    
    token = token[7:]  # Remove 'Bearer ' prefix
    user_data = verify_token(token)
    if not user_data:
        return {"error": "Invalid token"}, 401
    
    user = get_user_by_username(user_data.get('sub'))
    if user:
        return {
            "username": user["username"],
            "created_at": user["created_at"]
        }
    else:
        return {"error": "User not found"}, 404

def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        return None
    except Exception:
        return None

# ---------- Proxy stream ----------
@app.get("/video")
def video():
    # Optional bypass for testing
    if os.getenv("BYPASS_VIDEO_AUTH", "false").lower() in ("1", "true", "yes"):  
        token_valid = True
    else:
        # Prefer Authorization header
        auth_header = request.headers.get('Authorization', '')
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
        # Fallback to query param
        if not token:
            token = request.args.get("token")
        token_valid = bool(token and verify_token(token))

    if not token_valid:
        return {"error": "Unauthorized"}, 401

    r = requests.get(AI_STREAM_URL, stream=True)
    return Response(r.iter_content(chunk_size=1024),
                    content_type=r.headers.get("Content-Type", "multipart/x-mixed-replace; boundary=frame"))

# Initialize database when the app starts
init_db()

if __name__ == "__main__":
    # In production you should run this with a WSGI server (e.g. gunicorn).
    # Debug is disabled by default for safer deployment.
    app.run(host="0.0.0.0", port=5000, debug=False)