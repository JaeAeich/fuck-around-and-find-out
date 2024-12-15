"""Ensure psql is running with the below config."""

import time
import psycopg2
import threading
from queue import Queue
from time import perf_counter, sleep


def create_db_connection_and_do_something(
    conn: psycopg2.extensions.connection, connection_pool: Queue = None
) -> None:
    """Simulates work with a DB connection and optionally returns it to the pool."""
    try:
        print(f"Connection established by {threading.current_thread().name}")
        sleep(1)  # Simulate some work
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Return the connection to the pool if pooling is used
        if connection_pool:
            connection_pool.put(conn)
        else:
            conn.close()


def create_without_pooling(connection_number: int) -> None:
    """Creates multiple threads to open connections directly to the DB."""
    threads = []

    for i in range(connection_number):
        try:
            conn = psycopg2.connect(
                database="db",
                user="postgres",
                host="localhost",
                password="password",
                port=5432,
            )
            t = threading.Thread(
                target=create_db_connection_and_do_something,
                args=(conn,),  # No connection pool used here
                name=f"Thread-{i+1}",
            )
            threads.append(t)
            t.start()
        except Exception as e:
            print(f"Failed to create connection: {e}")

    for i, t in enumerate(threads):
        print(f"Joining thread {i + 1}")
        t.join()


def create_with_blocking_queue(connection_number: int, pool_size: int) -> None:
    """Creates a thread-safe connection pool using a blocking queue."""
    connection_pool = Queue(maxsize=pool_size)

    # Initialize the pool with connections
    for _ in range(pool_size):
        connection_pool.put(
            psycopg2.connect(
                database="db",
                user="postgres",
                host="localhost",
                password="password",
                port=5432,
            )
        )

    threads = []

    for i in range(connection_number):
        # Get a connection from the pool (blocks if pool is empty)
        conn = connection_pool.get()

        # Start a thread to use the connection
        t = threading.Thread(
            target=create_db_connection_and_do_something,
            args=(conn, connection_pool),  # Pass connection and pool
            name=f"Thread-{i+1}",
        )
        threads.append(t)
        t.start()

    # Wait for all threads to finish
    for i, t in enumerate(threads):
        print(f"Joining thread {i + 1}")
        t.join()

    # Close all connections in the pool
    while not connection_pool.empty():
        conn = connection_pool.get()
        conn.close()
        print("Connection closed")


if __name__ == "__main__":
    CONNECTIONS = 500  # Number of total connections to test
    POOL_SIZE = 100  # Pool size for the pooling test

    s1 = time.perf_counter()
    print("\n=== Running Without Pooling ===")
    create_without_pooling(CONNECTIONS)
    e1 = time.perf_counter()

    s2 = perf_counter()
    print("\n=== Running With Blocking Queue Pooling ===")
    create_with_blocking_queue(CONNECTIONS, POOL_SIZE)
    e2 = perf_counter()

    print(e1 - s1)
    print(e2 - s2)
