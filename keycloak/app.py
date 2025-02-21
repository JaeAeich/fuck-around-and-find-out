from flask import Flask, jsonify, request, g
from functools import wraps
import os
import jwt
from jwt.exceptions import InvalidTokenError
import requests
from datetime import datetime
import json

app = Flask(__name__)

# Configuration
KEYCLOAK_URL = os.getenv('KEYCLOAK_URL', 'http://localhost:8080')
KEYCLOAK_REALM = os.getenv('KEYCLOAK_REALM', 'todo-app')
KEYCLOAK_CLIENT_ID = os.getenv('KEYCLOAK_CLIENT_ID', 'todo-client')
KEYCLOAK_CLIENT_SECRET = os.getenv('KEYCLOAK_CLIENT_SECRET')

# Cache for the public key
PUBLIC_KEY = None

# In-memory database for demonstration
todos = []

class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

def get_public_key():
    """Get Keycloak's public key for token verification"""
    global PUBLIC_KEY
    
    if PUBLIC_KEY is None:
        try:
            # Get the public key from Keycloak
            url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
            response = requests.get(url)
            response.raise_for_status()
            
            # Extract the public key
            public_key = response.json()['public_key']
            PUBLIC_KEY = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
            
        except Exception as e:
            app.logger.error(f"Error fetching public key: {str(e)}")
            raise AuthError({"code": "public_key_error",
                           "description": str(e)}, 500)
    
    return PUBLIC_KEY

def requires_auth(f):
    """Authentication decorator"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', None)
        if not auth_header:
            raise AuthError({"code": "authorization_header_missing",
                           "description": "Authorization header is required"}, 401)

        try:
            # Extract token
            token_parts = auth_header.split()
            if token_parts[0].lower() != 'bearer' or len(token_parts) != 2:
                raise AuthError({"code": "invalid_header",
                               "description": "Invalid authorization header"}, 401)
            
            token = token_parts[1]
            
            # Get public key for verification
            public_key = get_public_key()
            
            # Verify token
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                audience=KEYCLOAK_CLIENT_ID,
                options={
                    'verify_aud': False,  # Temporarily disable audience verification
                    'verify_exp': True,   # Keep expiration verification
                    'verify_iss': False,  # Temporarily disable issuer verification
                }
            )
            
            # Store user info in Flask's g object
            g.user = {
                'sub': decoded['sub'],
                'username': decoded.get('preferred_username', ''),
                'roles': decoded.get('realm_access', {}).get('roles', [])
            }
            
            app.logger.debug(f"Decoded token: {decoded}")
            app.logger.debug(f"User info: {g.user}")
            
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            raise AuthError({"code": "token_expired",
                           "description": "Token has expired"}, 401)
        except jwt.InvalidTokenError as e:
            app.logger.error(f"Token validation error: {str(e)}")
            raise AuthError({"code": "invalid_token",
                           "description": str(e)}, 401)
        except Exception as e:
            app.logger.error(f"Auth error: {str(e)}")
            raise AuthError({"code": "invalid_token",
                           "description": str(e)}, 401)
            
    return decorated

def requires_role(required_role):
    """Authorization decorator"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, 'user') or 'roles' not in g.user:
                raise AuthError({"code": "no_user_context",
                               "description": "No authenticated user context found"}, 401)
                
            if required_role not in g.user['roles']:
                raise AuthError({"code": "insufficient_permissions",
                               "description": f"Required role '{required_role}' not found"}, 403)
                
            return f(*args, **kwargs)
        return decorated
    return decorator

# CRUD Operations

@app.route('/todos', methods=['GET'])
@requires_auth
def get_todos():
    """Get todos - admins see all, users see only their own"""
    if 'admin' in g.user['roles']:
        return jsonify(todos)
    
    user_todos = [todo for todo in todos if todo['owner'] == g.user['username']]
    return jsonify(user_todos)

@app.route('/todos/<int:todo_id>', methods=['GET'])
@requires_auth
def get_todo(todo_id):
    """Get a specific todo"""
    todo = next((t for t in todos if t['id'] == todo_id), None)
    
    if not todo:
        return jsonify({"error": "Todo not found"}), 404
        
    if 'admin' not in g.user['roles'] and todo['owner'] != g.user['username']:
        raise AuthError({"code": "insufficient_permissions",
                        "description": "Cannot access other users' todos"}, 403)
    
    return jsonify(todo)

@app.route('/todos', methods=['POST'])
@requires_auth
@requires_role('user')
def create_todo():
    """Create a new todo"""
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({"error": "Title is required"}), 400
    
    new_todo = {
        "id": len(todos) + 1,
        "title": data['title'],
        "description": data.get('description', ''),
        "owner": g.user['username'],
        "created_at": datetime.utcnow().isoformat(),
        "completed": False
    }
    
    todos.append(new_todo)
    return jsonify(new_todo), 201

@app.route('/todos/<int:todo_id>', methods=['PUT'])
@requires_auth
def update_todo(todo_id):
    """Update a todo"""
    todo = next((t for t in todos if t['id'] == todo_id), None)
    
    if not todo:
        return jsonify({"error": "Todo not found"}), 404
        
    if 'admin' not in g.user['roles'] and todo['owner'] != g.user['username']:
        raise AuthError({"code": "insufficient_permissions",
                        "description": "Cannot update other users' todos"}, 403)
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No update data provided"}), 400
    
    # Update allowed fields
    todo['title'] = data.get('title', todo['title'])
    todo['description'] = data.get('description', todo['description'])
    todo['completed'] = data.get('completed', todo['completed'])
    
    return jsonify(todo)

@app.route('/todos/<int:todo_id>', methods=['DELETE'])
@requires_auth
def delete_todo(todo_id):
    """Delete a todo"""
    todo = next((t for t in todos if t['id'] == todo_id), None)
    
    if not todo:
        return jsonify({"error": "Todo not found"}), 404
        
    if 'admin' not in g.user['roles'] and todo['owner'] != g.user['username']:
        raise AuthError({"code": "insufficient_permissions",
                        "description": "Cannot delete other users' todos"}, 403)
    
    todos.remove(todo)
    return '', 204

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
