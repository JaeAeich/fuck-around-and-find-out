# Keycloak Example with Flask

This is a simple Todo application demonstrating Role-Based Access Control (RBAC) and Authentication using Keycloak and Flask.


## Setup and Running


1. Start the services:
```bash
docker-compose up --build
```

2. Wait for all services to be ready (Keycloak, PostgreSQL, and Flask app)

## Test Users

The system comes with two predefined users:

- Admin User:
  - Username: alice
  - Password: alice123
  - Roles: admin, user

- Regular User:
  - Username: bob
  - Password: bob123
  - Role: user

## Testing the API

### 1. Get Access Token

For Alice (admin):
```bash
export TOKEN=$(curl -X POST \
  http://localhost:8080/realms/todo-app/protocol/openid-connect/token \
  -d "client_id=todo-client" \
  -d "client_secret=RVVHDhA5tWBRtHh51IUB2UuQ2mThXMNb" \
  -d "grant_type=password" \
  -d "username=alice" \
  -d "password=alice123" | jq -r .access_token)
```

For Bob (regular user):
```bash
export TOKEN=$(curl -X POST \
  http://localhost:8080/realms/todo-app/protocol/openid-connect/token \
  -d "client_id=todo-client" \
  -d "client_secret=RVVHDhA5tWBRtHh51IUB2UuQ2mThXMNb" \
  -d "grant_type=password" \
  -d "username=bob" \
  -d "password=bob123" | jq -r .access_token)
```

### 2. Test CRUD Operations

#### Create a Todo
```bash
curl -X POST \
  http://localhost:5000/todos \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test todo",
    "description": "This is a test todo"
  }'
```

#### Get All Todos
```bash
curl -X GET \
  http://localhost:5000/todos \
  -H "Authorization: Bearer $TOKEN"
```

#### Get Specific Todo
```bash
curl -X GET \
  http://localhost:5000/todos/1 \
  -H "Authorization: Bearer $TOKEN"
```

#### Update a Todo
```bash
curl -X PUT \
  http://localhost:5000/todos/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated todo",
    "description": "This is an updated todo",
    "completed": true
  }'
```

#### Delete a Todo
```bash
curl -X DELETE \
  http://localhost:5000/todos/1 \
  -H "Authorization: Bearer $TOKEN"
```

## Access Control Rules

1. Authentication is required for all endpoints
2. Only users with the 'user' role can create todos
3. Users can only see and modify their own todos
4. Admins can see and modify all todos

