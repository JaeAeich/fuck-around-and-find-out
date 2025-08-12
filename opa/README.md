# OPA

Create a policy that allows **admins** to view all payments.

```sh
curl -s -X POST http://localhost:8080/policies \
  -H 'Content-Type: application/json' \
  -d '{"name":"restaurant-authz","rego_code":"package restaurant.authz\n\ndefault allow = false\n\nallow if {\n input.user.role == \"admin\"\n input.path == \"/payments\"\n}"}'
```

## Test as Admin

```sh
curl -i -H 'x-user-role: admin' http://localhost:3000/payments
```

## Test as Viewer

```sh
curl -i -H 'x-user-role: viewer' http://localhost:3000/payments
```
