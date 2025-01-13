# Sharding

Database is sharded, ie pasrts of same data is spread across
multiple databses, here 3 db are used, each has a table to store
data about user, if user as id 1, its in db1 so on and so forth.

```bash
docker compose up -d --build
```

Then fire post command to create users:

```bash
curl -X POST http://localhost:8080/users -H "Content-Type: application/json" -d '{"id":"1", name": "John Doe", "email": "john@example.com"}'

```
