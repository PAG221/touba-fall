import mysql.connector
import os

def get_db():
    try:
        host = os.getenv("MYSQLHOST")
        user = os.getenv("MYSQLUSER")
        password = os.getenv("MYSQLPASSWORD")
        database = os.getenv("MYSQLDATABASE")
        port = os.getenv("MYSQLPORT")

        print("DEBUG DB:")
        print("HOST:", host)
        print("USER:", user)
        print("DB:", database)
        print("PORT:", port)

        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=int(port)
        )

        print("✅ Connexion réussie")
        return conn

    except Exception as e:
        print("❌ ERREUR DB:", e)
        return None
