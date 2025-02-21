# Todo API with Casbin Authorization

A Flask-based Todo API with role-based access control (RBAC) using Casbin.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `policy.csv` file with the following content:
```csv
p, admin, todos, read
p, admin, todos, write
p, admin, todos, delete
p, user, todos, read
p, user, todos, write
g, alice, admin
g, bob, user
g, carol, user
```

This policy defines:
- Admins can read, write, and delete todos
- Regular users can read and write todos
- Alice is assigned the admin role
- Bob and Carol are assigned the user role

## Authentication

The API uses a simple header-based authentication. Pass the user in the `X-User` header:
```
X-User: alice
```

## Authorization

Casbin enforces permissions based on:
- Subject (user)
- Object (resource)
- Action (permission)

The `auth_model.conf` uses RBAC (Role-Based Access Control) with:
- Role definition: Users can be assigned roles
- Policy effect: Permissions are allowed if any matching policy rule exists
- Matchers: Checks if the user has the required role and permission for the resource

## API Endpoints

### Get Todos
```bash
# As admin (sees all todos)
curl -H "X-User: alice" http://localhost:5000/todos

# As regular user (sees only their todos)
curl -H "X-User: bob" http://localhost:5000/todos
```

### Create Todo
```bash
curl -X POST \
  -H "X-User: bob" \
  -H "Content-Type: application/json" \
  -d '{"title": "New task"}' \
  http://localhost:5000/todos
```

### Delete Todo
```bash
# As admin (can delete any todo)
curl -X DELETE -H "X-User: alice" http://localhost:5000/todos/1

# As owner (can only delete own todos)
curl -X DELETE -H "X-User: bob" http://localhost:5000/todos/2
```

## Access Control Rules

1. Authentication:
   - All endpoints require a valid user in X-User header

2. Authorization:
   - Admins can see all todos
   - Regular users can only see their own todos
   - Regular users can create todos (automatically owned by them)
   - Regular users can only delete their own todos
   - Admins can delete any todo

## Error Responses

- 401 Unauthorized: Missing or invalid user
- 403 Forbidden: User doesn't have required permission
- 404 Not Found: Todo doesn't exist
