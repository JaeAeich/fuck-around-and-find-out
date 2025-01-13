from flask import Flask, request, jsonify
import psycopg2
import os

app = Flask(__name__)

# Define database connections
db_topology = {
    "shard1": {
        "host": os.getenv("DB_1_URL", "db-1"),
        "port": 5432,
        "dbname": "shard1",
        "user": "user1",
        "password": "password1",
    },
    "shard2": {
        "host": os.getenv("DB_2_URL", "db-2"),
        "port": 5432,
        "dbname": "shard2",
        "user": "user2",
        "password": "password2",
    },
    "shard3": {
        "host": os.getenv("DB_3_URL", "db-3"),
        "port": 5432,
        "dbname": "shard3",
        "user": "user3",
        "password": "password3",
    },
}


def get_shard(user_id):
    """Determine the shard based on user ID (simple modulus sharding)."""
    shard_key = int(user_id) % len(db_topology)
    return list(db_topology.values())[shard_key]


def connect_to_db(shard):
    """Connect to a specific shard."""
    try:
        conn = psycopg2.connect(**shard)
        return conn
    except Exception as e:
        return str(e)


@app.route("/")
def hello():
    return "Hello, Sharded World!"


@app.route("/create_user", methods=["POST"])
def create_user():
    """Create a user and insert it into the appropriate shard."""
    data = request.json
    user_id = data.get("id")
    name = data.get("name")
    email = data.get("email")

    if not all([user_id, name, email]):
        return jsonify({"error": "Missing user data"}), 400

    shard = get_shard(user_id)
    conn = connect_to_db(shard)

    if isinstance(conn, str):
        return jsonify({"error": f"Database connection error: {conn}"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (id, name, email) VALUES (%s, %s, %s)",
                (user_id, name, email),
            )
            conn.commit()
        return jsonify({"message": "User created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/get_user/<int:user_id>")
def get_user(user_id):
    """Retrieve a user from the appropriate shard."""
    shard = get_shard(user_id)
    conn = connect_to_db(shard)

    if isinstance(conn, str):
        return jsonify({"error": f"Database connection error: {conn}"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, email FROM users WHERE id = %s", (user_id,)
            )
            user = cursor.fetchone()

        if user:
            return jsonify({"id": user[0], "name": user[1], "email": user[2]})
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
