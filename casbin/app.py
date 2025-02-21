from flask import Flask, jsonify, request
from casbin import Enforcer
from functools import wraps

app = Flask(__name__)

# Initialize Casbin enforcer with model and policy
enforcer = Enforcer("auth_model.conf", "policy.csv")

# Sample database
users = {
    "alice": {"role": "admin"},
    "bob": {"role": "user"},
    "carol": {"role": "user"}
}

todos = [
    {"id": 1, "title": "Buy groceries", "owner": "alice"},
    {"id": 2, "title": "Write report", "owner": "bob"},
    {"id": 3, "title": "Team meeting", "owner": "carol"}
]

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get user from request header
        user = request.headers.get('X-User')
        if not user or user not in users:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def check_permission(user, resource, action):
    return enforcer.enforce(user, resource, action)

def require_permission(resource, action):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = request.headers.get('X-User')
            if not check_permission(user, resource, action):
                return jsonify({"error": "Forbidden"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

@app.route('/todos', methods=['GET'])
@require_auth
@require_permission('todos', 'read')
def get_todos():
    user = request.headers.get('X-User')
    # If user is admin, return all todos
    if users[user]['role'] == 'admin':
        return jsonify(todos)
    # If user is regular user, return only their todos
    user_todos = [todo for todo in todos if todo['owner'] == user]
    return jsonify(user_todos)

@app.route('/todos', methods=['POST'])
@require_auth
@require_permission('todos', 'write')
def create_todo():
    user = request.headers.get('X-User')
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({"error": "Invalid request"}), 400
    
    new_todo = {
        "id": len(todos) + 1,
        "title": data['title'],
        "owner": user
    }
    todos.append(new_todo)
    return jsonify(new_todo), 201

@app.route('/todos/<int:todo_id>', methods=['DELETE'])
@require_auth
@require_permission('todos', 'delete')
def delete_todo(todo_id):
    user = request.headers.get('X-User')
    todo = next((t for t in todos if t['id'] == todo_id), None)
    
    if not todo:
        return jsonify({"error": "Todo not found"}), 404
    
    # Only admin or owner can delete todo 
    if users[user]['role'] != 'admin' and todo['owner'] != user:
        return jsonify({"error": "Forbidden"}), 403
    
    todos.remove(todo)
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)
