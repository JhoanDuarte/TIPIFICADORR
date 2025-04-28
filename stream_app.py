# stream_app.py
import streamlit as st
from login_app import authenticate_user_by_doc
from db_connection import conectar_sql_server

# Conexión (si planeas usarla en tu dashboard)
conn = conectar_sql_server('DB_DATABASE')
if conn is None:
    st.error("Error: no se pudo conectar a la base de datos.")

# ------------------------------------------------
# Pantalla de login
# ------------------------------------------------
def login():
    st.title("Login - Tipificador Médica")
    doc = st.text_input("Documento")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Iniciar sesión"):
        user = authenticate_user_by_doc(doc, pwd)
        if user and user[3] == 5:
            # Guardamos en sesión y recargamos para mostrar el dashboard
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Credenciales inválidas o usuario inactivo.")

# ------------------------------------------------
# Dashboard tras login
# ------------------------------------------------
def dashboard():
    user = st.session_state.user
    st.sidebar.write(f"Usuario: {user[1]} {user[2]}")
    st.title("Dashboard - Tipificador Médica")
    # Aquí coloca tu lógica de carga de paquetes, tipificación, etc.
    st.write("Bienvenido al dashboard. Implementa aquí tus funciones.")

# ------------------------------------------------
# Punto de entrada
# ------------------------------------------------
def main():
    if 'user' not in st.session_state:
        login()
    else:
        dashboard()

if __name__ == "__main__":
    main()
