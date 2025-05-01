import psycopg2
from pymongo import MongoClient
import os

class SQLConnector:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST"),
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD")
        )

    def query(self, query, params=None):
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            result = cur.fetchall()
        return result

class MongoDBConnector:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client[os.getenv("MONGO_DB")]

    def find(self, collection, query):
        return list(self.db[collection].find(query))

if __name__ == '__main__':
    sql_conn = SQLConnector()
    result = sql_conn.query("SELECT * FROM tenders LIMIT 10;")
    print(result)