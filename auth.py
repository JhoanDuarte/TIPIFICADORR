# auth.py
from db_connection import conectar_sql_server

# Conexión global
_conn = conectar_sql_server('DB_DATABASE')
if _conn is None:
    raise RuntimeError("No se pudo conectar a la base de datos.")

def authenticate_user_by_doc(num_doc: str, password: str):
    cursor = _conn.cursor()
    cursor.execute(
        "SELECT ID, FIRST_NAME, LAST_NAME, PASSWORD, STATUS_ID FROM USERS WHERE NUM_DOC = ?",
        (num_doc,),
    )
    row = cursor.fetchone()
    cursor.close()
    if not row:
        return None
    user_id, first_name, last_name, stored_password, status_id = row
    if stored_password == password:
        return (user_id, first_name, last_name, status_id)
    return None
