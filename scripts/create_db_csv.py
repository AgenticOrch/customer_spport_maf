import csv
import sqlite3
import os

def csv_to_sqlite(csv_path, folder_path, db_name, table_name):
    """
    Converts CSV into SQLite DB stored inside a specific folder.

    Args:
        csv_path (str): Path to the CSV file
        folder_path (str): Folder where the SQLite DB will be stored
        db_name (str): SQLite database file name (e.g., 'sales.db')
        table_name (str): Name of the SQLite table to create
    """

    # Ensure the folder exists
    os.makedirs(folder_path, exist_ok=True)

    # Full DB path
    sqlite_path = os.path.join(folder_path, db_name)

    # Check CSV exists
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Read CSV data
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        rows = list(reader)

    # Create SQLite DB
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()

    # Drop table if exists
    cur.execute(f"DROP TABLE IF EXISTS {table_name}")

    # Create table dynamically from headers
    columns = ", ".join([f"'{col}' TEXT" for col in headers])
    create_query = f"CREATE TABLE {table_name} ({columns});"
    cur.execute(create_query)

    # Insert data
    placeholders = ", ".join(["?"] * len(headers))
    insert_query = f"INSERT INTO {table_name} VALUES ({placeholders})"
    cur.executemany(insert_query, rows)

    conn.commit()
    conn.close()

    print(f"SQLite DB created at: {sqlite_path}")
    print(f"Table '{table_name}' successfully populated.")

    return sqlite_path


# Example usage:
if __name__ == "__main__":
    csv_to_sqlite(
        csv_path="/Users/rahul/Downloads/restaurant_orders.csv",
        folder_path="Databases",      # folder to store DBs
        db_name="orders.db",           # database file name
        table_name="order_table"      # table name
    )