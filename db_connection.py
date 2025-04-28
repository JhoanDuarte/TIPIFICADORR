import os, sys, pyodbc
from dotenv import load_dotenv

def obtener_ruta_recurso(nombre_archivo):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, nombre_archivo)
    return nombre_archivo

load_dotenv(dotenv_path=obtener_ruta_recurso('.env'))

def conectar_sql_server(env_database_var):
    server   = os.getenv('DB_SERVER')
    database = os.getenv(env_database_var)
    username = os.getenv('DB_USERNAME')
    password = os.getenv('DB_PASSWORD')
    driver   = '{ODBC Driver 17 for SQL Server}'
    try:
        conn = pyodbc.connect(
            f"DRIVER={driver};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password}"
        )
        return conn
    except Exception as e:
        print("Error al conectar:", e)
        return None
