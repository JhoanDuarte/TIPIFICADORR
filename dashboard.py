# streamlit_dashboard.py

import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import datetime
import io
from db_connection import conectar_sql_server
from login_app import authenticate_user_by_doc

# ---------------------------------------------------------
# Configuración de la página
# ---------------------------------------------------------
st.set_page_config(
    page_title="Tipificador Médica",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# Conexión a la base de datos
# ---------------------------------------------------------
conn = conectar_sql_server('DB_DATABASE')
if conn is None:
    st.error("❌ No se pudo conectar a la base de datos.")
    st.stop()

# ---------------------------------------------------------
# DEFINICIÓN DE ROLES Y MENÚ
# ---------------------------------------------------------
MENU_BY_ROLE = {
    1: [
        "Cargar Paquete",
        "Crear Usuario",
        "Ver Progreso",
        "Modificar Estado Usuario",
        "Exportar Tipificación"
    ],
    2: ["Iniciar Tipificación"]
}

# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------
def login_page():
    st.markdown(
        """
        <div style="text-align:center; margin-top:100px;">
          <h1>🔒 Inicia sesión</h1>
        </div>
        """, unsafe_allow_html=True
    )
    doc = st.text_input("Documento", placeholder="12345678")
    pwd = st.text_input("Contraseña", type="password", placeholder="••••••")
    if st.button("Entrar"):
        user = authenticate_user_by_doc(doc, pwd)
        if user and user[3] == 5:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("❌ Documento/contraseña incorrectos o usuario inactivo.")

# ---------------------------------------------------------
# KPI PARA CABECERA
# ---------------------------------------------------------
def _get_pending_count():
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ASIGNACION_TIPIFICACION WHERE STATUS_ID=1")
    v = cur.fetchone()[0]; cur.close(); return v

def _get_active_users():
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM USERS WHERE STATUS_ID=5")
    v = cur.fetchone()[0]; cur.close(); return v

def _get_total_tips():
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM TIPIFICACION")
    v = cur.fetchone()[0]; cur.close(); return v

# ---------------------------------------------------------
# FUNCIONES WEB
# ---------------------------------------------------------
def cargar_paquete_web():
    st.header("📤 Cargar Paquete")
    uploaded = st.file_uploader("Selecciona archivo Excel o CSV", type=["xlsx","xls","csv"])
    if uploaded:
        df = pd.read_excel(uploaded) if uploaded.name.endswith(("xls","xlsx")) else pd.read_csv(uploaded)
        st.dataframe(df, use_container_width=True)
        if st.button("Insertar en BD"):
            with st.spinner("Insertando..."):
                cur = conn.cursor()
                cur.execute("SELECT MAX(NUM_PAQUETE) FROM ASIGNACION_TIPIFICACION WHERE STATUS_ID=1")
                num = cur.fetchone()[0] or 0
                pkg = num + 1
                cur.execute("SET IDENTITY_INSERT ASIGNACION_TIPIFICACION ON;")
                inserted = 0
                for idx, row in df.iterrows():
                    try:
                        cur.execute(
                            """
                            INSERT INTO ASIGNACION_TIPIFICACION
                              (RADICADO, NIT, RAZON_SOCIAL, FACTURA, VALOR_FACTURA,
                               FECHA_FACTURA, FECHA_RADICACION, TIPO_DOC_ID, NUM_DOC,
                               ESTADO_FACTURA, IMAGEN, RADICADO_IMAGEN, LINEA,
                               ID_ASIGNACION, ESTADO_PYS, OBSERVACION_PYS, LINEA_PYS,
                               RANGOS, DEF, STATUS_ID, NUM_PAQUETE)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                            """,
                            int(row["RADICADO"]), int(row["NIT"]), str(row["RAZON_SOCIAL"]),
                            str(row["FACTURA"]), int(row["VALOR_FACTURA"]),
                            row["FECHA FACTURA"], row["FECHA RADICACION"],
                            str(row["TIPO DOC"]), int(row["NUM DOC"]),
                            row.get("ESTADO_FACTURA", None), row.get("IMAGEN", None),
                            row.get("RADICADO_IMAGEN", None), row.get("LINEA", None),
                            row.get("ID ASIGNACION", None), row.get("ESTADO PYS", None),
                            row.get("OBSERVACION PYS", None), row.get("LINEA PYS", None),
                            row.get("RANGOS", None), row.get("Def", None),
                            1, pkg
                        )
                        inserted += 1
                    except Exception as e:
                        st.warning(f"Fila {idx}: {e}")
                cur.execute("SET IDENTITY_INSERT ASIGNACION_TIPIFICACION OFF;")
                conn.commit()
                st.success(f"✅ Insertadas {inserted} filas. Paquete #{pkg}")

def crear_usuario_web():
    st.header("➕ Crear Usuario")

    # 1) Carga de catálogos
    cur = conn.cursor()
    cur.execute("SELECT ID, NAME FROM TIPO_DOC");     tipos    = cur.fetchall()
    cur.execute("SELECT ID, NAME FROM STATUS WHERE ID IN (5,6)"); statuses = cur.fetchall()
    cur.execute("SELECT ID, NAME FROM ROL");           roles    = cur.fetchall()
    cur.close()

    # 2) Centrar el formulario usando 3 columnas
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # 3) Formulario con clear_on_submit para vaciar campos tras enviar
        with st.form("form_usuario", clear_on_submit=True):
            fn         = st.text_input("Nombres").strip().upper()
            ln         = st.text_input("Apellidos").strip().upper()
            tipo       = st.selectbox("Tipo Doc",    [n for _, n in tipos])
            num        = st.text_input("N° Documento").strip()
            pwd        = st.text_input("Contraseña", type="password").strip()
            status     = st.selectbox("Status",      [n for _, n in statuses])
            sel_roles  = st.multiselect("Roles",     [n for _, n in roles])

            submitted = st.form_submit_button("💾 Guardar Usuario")

        # 4) Lógica al enviar
        if submitted:
            try:
                map_td = {n: i for i, n in tipos}
                map_st = {n: i for i, n in statuses}
                map_rl = {n: i for i, n in roles}
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO USERS
                      (FIRST_NAME, LAST_NAME, TYPE_DOC_ID, NUM_DOC, PASSWORD, STATUS_ID)
                    OUTPUT INSERTED.ID
                    VALUES (?,?,?,?,?,?)
                    """,
                    fn, ln, map_td[tipo], int(num), pwd, map_st[status]
                )
                new_id = cur.fetchone()[0]
                for r in sel_roles:
                    cur.execute(
                        "INSERT INTO USER_ROLES (USER_ID, ROL_ID) VALUES (?,?)",
                        new_id, map_rl[r]
                    )
                conn.commit()
                st.success(f"👤 Usuario creado con ID {new_id}")
            except Exception as e:
                st.error(f"❌ Error: {e}")


def ver_progreso_web():
    st.header("📊 Ver Progreso de Paquetes")
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT NUM_PAQUETE FROM ASIGNACION_TIPIFICACION ORDER BY NUM_PAQUETE")
    paquetes = [r[0] for r in cur.fetchall()]
    cur.close()
    pkg = st.selectbox("Paquete", paquetes)
    if st.button("Mostrar"):
        df1 = pd.read_sql_query(
            """
            SELECT s.NAME AS ESTADO, COUNT(*) AS CNT
              FROM ASIGNACION_TIPIFICACION at
              JOIN STATUS s ON at.STATUS_ID=s.ID
             WHERE at.NUM_PAQUETE=?
             GROUP BY s.NAME
             ORDER BY s.NAME
            """, conn, params=[int(pkg)]
        )
        st.subheader("Por Estado"); st.table(df1)
        df2 = pd.read_sql_query(
            """
            SELECT u.ID,
                   u.FIRST_NAME+' '+u.LAST_NAME AS USUARIO,
                   SUM(CASE WHEN at.STATUS_ID=2 THEN 1 ELSE 0 END) PENDIENTES,
                   SUM(CASE WHEN at.STATUS_ID=3 THEN 1 ELSE 0 END) PROCESADOS,
                   SUM(CASE WHEN at.STATUS_ID=4 THEN 1 ELSE 0 END) CON_OBS
              FROM TIPIFICACION t
              JOIN USERS u ON t.USER_ID=u.ID
              JOIN ASIGNACION_TIPIFICACION at ON at.RADICADO=t.ASIGNACION_ID
             WHERE at.NUM_PAQUETE=?
             GROUP BY u.ID, u.FIRST_NAME, u.LAST_NAME
             ORDER BY USUARIO
            """, conn, params=[int(pkg)]
        )
        st.subheader("Por Usuario"); st.table(df2)

def iniciar_tipificacion_web():
    st.header("▶️ Iniciar Tipificación")

    # 1) Obtener paquete y campos parametrizados
    df_pkg = pd.read_sql_query("SELECT MAX(NUM_PAQUETE) AS num FROM PAQUETE_CAMPOS", conn)
    raw_pkg = df_pkg["num"].iloc[0]
    pkg = int(raw_pkg) if pd.notna(raw_pkg) else 0

    campos = pd.read_sql_query(
        "SELECT campo FROM PAQUETE_CAMPOS WHERE NUM_PAQUETE = ?",
        conn, params=[pkg]
    )["campo"].tolist()

    # 2) Catálogos para selectores
    dx_opts = (
        pd.read_sql_query("SELECT CODIGO FROM TBL_CIE10", conn)["CODIGO"]
        .astype(str).tolist()
        if "DIAGNOSTICO" in campos else []
    )
    cs_opts = (
        pd.read_sql_query("SELECT PRO_MAP_MAPIISS FROM TBL_HOMOLOGACION_MAPIS", conn)["PRO_MAP_MAPIISS"]
        .astype(str).tolist()
        if "CODIGO_SERVICIO" in campos else []
    )

    # 3) Traer UNA vez la asignación pendiente
    if "tip_asign" not in st.session_state:
        rec = pd.read_sql_query(
            """
            SELECT TOP 1 RADICADO, NIT, FACTURA
              FROM ASIGNACION_TIPIFICACION
             WHERE STATUS_ID = 1 AND NUM_PAQUETE = ?
             ORDER BY NEWID()
            """,
            conn, params=[pkg]
        )
        if rec.empty:
            st.info("✔️ No hay asignaciones pendientes.")
            return
        st.session_state.tip_asign = {
            "rad": int(rec.at[0, "RADICADO"]),
            "nit": rec.at[0, "NIT"],
            "fac": rec.at[0, "FACTURA"],
            "pkg": pkg
        }
        st.session_state.tip_en_curso = False

    info = st.session_state.tip_asign
    st.markdown(f"**Paquete #{info['pkg']}**  •  Radicado: `{info['rad']}`  •  NIT: `{info['nit']}`  •  Factura: `{info['fac']}`")

    # 4) Marcar en curso solo la primera vez
    if not st.session_state.tip_en_curso:
        cur = conn.cursor()
        cur.execute("UPDATE ASIGNACION_TIPIFICACION SET STATUS_ID = 2 WHERE RADICADO = ?", (info["rad"],))
        conn.commit()
        st.session_state.tip_en_curso = True

    # 5) Formulario dinámico
    with st.form("tip_form"):
        inputs = {}

        # 5.1 Campos fijos
        if "FECHA_SERVICIO" in campos:
            inputs["FECHA_SERVICIO"] = st.date_input("📅 Fecha Servicio", max_value=datetime.date.today(), format="DD/MM/YYYY")
        if "TIPO_DOC_ID" in campos:
            td_opts = pd.read_sql_query("SELECT NAME FROM TIPO_DOC", conn)["NAME"].tolist()
            inputs["TIPO_DOC_ID"] = st.selectbox("🆔 Tipo Documento", td_opts)
        if "NUM_DOC" in campos:
            inputs["NUM_DOC"] = st.number_input("🔢 Num Documento", min_value=0, step=1)
        if "DIAGNOSTICO" in campos:
            inputs["DIAGNOSTICO"] = st.selectbox("💡 Diagnóstico", dx_opts)

        # 5.2 Número de servicios justo después de Diagnóstico
        max_serv = 10
        n = 0
        if any(c in campos for c in ("AUTORIZACION","CODIGO_SERVICIO","CANTIDAD","VLR_UNITARIO","COPAGO")):
            n = st.slider("🔢 Número de servicios a tipificar", 1, max_serv, key="nserv")

        # 5.3 Bloques de detalle según el slider
        detalle = []
        for i in range(1, n+1):
            st.markdown(f"--- **Servicio #{i}** ---")
            d = {}
            if "AUTORIZACION" in campos:
                d["AUTORIZACION"] = st.text_input(f"📝 Autorización #{i}", key=f"auth_{i}")
            if "CODIGO_SERVICIO" in campos:
                d["CODIGO_SERVICIO"] = st.selectbox(f"🔧 Código Servicio #{i}", cs_opts, key=f"cs_{i}")
            if "CANTIDAD" in campos:
                d["CANTIDAD"] = st.number_input(f"📦 Cantidad #{i}", key=f"qty_{i}", min_value=0, step=1)
            if "VLR_UNITARIO" in campos:
                d["VLR_UNITARIO"] = st.number_input(f"💲 Valor Unitario #{i}", key=f"vlru_{i}", min_value=0.0)
            if "COPAGO" in campos:
                d["COPAGO"] = st.number_input(f"💵 Copago #{i}", key=f"copago_{i}", min_value=0.0)
            if "OBSERVACION" in campos:
                d["OBSERVACION"] = st.text_area(f"✏️ Observación #{i}", key=f"obs_{i}")
            detalle.append(d)

        # 5.4 Botones
        col1, col2 = st.columns(2)
        btn_next = col1.form_submit_button("💾 Guardar y siguiente")
        btn_exit = col2.form_submit_button("🚪 Guardar y salir")

    # 6) Si no pulsó nada, salimos
    if not (btn_next or btn_exit):
        return

    # 7) Validaciones
    errores = []
    # Fecha no futura
    if "FECHA_SERVICIO" in inputs and inputs["FECHA_SERVICIO"] > datetime.date.today():
        errores.append("❌ La Fecha Servicio no puede ser futura.")
    # Autorización de 9 dígitos
    for idx, d in enumerate(detalle, start=1):
        auth = d.get("AUTORIZACION","").strip()
        if auth and len(auth) != 9:
            errores.append(f"❌ Autorización #{idx} debe tener 9 dígitos.")
    # Si no hay NINGUNA observación, los campos obligatorios
    any_obs = any(d.get("OBSERVACION","").strip() for d in detalle)
    if not any_obs:
        for idx, d in enumerate(detalle, start=1):
            for fld in ("AUTORIZACION","CODIGO_SERVICIO","CANTIDAD","VLR_UNITARIO"):
                if fld in campos and not d.get(fld):
                    errores.append(f"❌ {fld} del servicio #{idx} es obligatorio.")
    if errores:
        for e in errores:
            st.error(e)
        return

    # 8) Guardar en la base de datos
    cur2 = conn.cursor()
    try:
        # 8.1 Insertar cabecera
        fecha_val = inputs.get("FECHA_SERVICIO")
        if isinstance(fecha_val, datetime.date):
            fecha_val = datetime.datetime.combine(fecha_val, datetime.time())
        tipo_id = None
        if inputs.get("TIPO_DOC_ID"):
            tipo_id = cur2.execute(
                "SELECT ID FROM TIPO_DOC WHERE NAME = ?", (inputs["TIPO_DOC_ID"],)
            ).fetchone()[0]
        num_doc_i = inputs.get("NUM_DOC")
        diag = inputs.get("DIAGNOSTICO") or None

        cur2.execute("""
            INSERT INTO TIPIFICACION
              (ASIGNACION_ID, FECHA_SERVICIO, TIPO_DOC_ID, NUM_DOC, DIAGNOSTICO, USER_ID)
            OUTPUT INSERTED.ID
            VALUES (?, ?, ?, ?, ?, ?)
        """, (info["rad"], fecha_val, tipo_id, num_doc_i, diag, st.session_state.user[0]))
        tip_id = cur2.fetchone()[0]

        # 8.2 Insertar detalles
        tiene_obs = False
        for d in detalle:
            obs = d.get("OBSERVACION") or None
            if obs:
                tiene_obs = True
            cur2.execute("""
                INSERT INTO TIPIFICACION_DETALLES
                  (TIPIFICACION_ID, AUTORIZACION, CODIGO_SERVICIO,
                   CANTIDAD, VLR_UNITARIO, COPAGO, OBSERVACION)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                tip_id,
                int(d.get("AUTORIZACION")) if d.get("AUTORIZACION") else None,
                d.get("CODIGO_SERVICIO"),
                d.get("CANTIDAD"),
                d.get("VLR_UNITARIO"),
                d.get("COPAGO"),
                obs
            ))

        # 8.3 Marcar finalizado
        nuevo_st = 4 if tiene_obs else 3
        cur2.execute(
            "UPDATE ASIGNACION_TIPIFICACION SET STATUS_ID = ? WHERE RADICADO = ?",
            (nuevo_st, info["rad"])
        )

        conn.commit()
    except Exception as e:
        conn.rollback()
        st.error("❌ Error al guardar: " + str(e))
        return

    st.success("✅ Tipificación guardada correctamente.")

    # 9) Limpiar estado
    for k in ("tip_asign","tip_en_curso","nserv"):
        st.session_state.pop(k, None)
    # 10) Si “salir”, desloguear
    if btn_exit:
        st.session_state.pop("user", None)
    # 11) Recargar para mostrar login o siguiente asignación
    st.rerun()
    
def modificar_estado_usuario_web():
    st.header("✏️ Modificar Estado de Usuario")

    # — 1) Formulario de búsqueda —
    with st.form("buscar_usuario"):
        # Cargo catálogo de tipos de documento
        tipos_df = pd.read_sql_query("SELECT ID, NAME FROM TIPO_DOC", conn)
        tipos_df["NAME_UP"] = tipos_df["NAME"].str.upper()
        tipo_sel = st.selectbox("Tipo Doc", tipos_df["NAME_UP"], key="mod_tipo")
        num_sel  = st.text_input("Num Doc", key="mod_num")
        btn_buscar = st.form_submit_button("🔍 Buscar")

    # — 2) Al pulsar “Buscar” guardo en session_state —
    if btn_buscar:
        try:
            tipo_id = int(tipos_df.loc[tipos_df["NAME_UP"] == tipo_sel, "ID"].iloc[0])
            rec = pd.read_sql_query(
                """
                SELECT u.ID, u.FIRST_NAME, u.LAST_NAME,
                       u.STATUS_ID, s.NAME AS STATUS
                  FROM USERS u
                  JOIN STATUS s ON u.STATUS_ID = s.ID
                 WHERE u.TYPE_DOC_ID = ? AND u.NUM_DOC = ?
                   AND u.STATUS_ID IN (5,6)
                """,
                conn,
                params=[tipo_id, int(num_sel)]
            )
        except Exception as e:
            st.error(f"Error al buscar usuario: {e}")
            return

        if rec.empty:
            st.info("No se encontró ningún usuario en estado PENDIENTE o RECHAZADO.")
            return

        # almaceno los datos en session_state
        st.session_state.mod_user = {
            "id": int(rec.at[0, "ID"]),
            "first": rec.at[0, "FIRST_NAME"],
            "last":  rec.at[0, "LAST_NAME"],
            "status": rec.at[0, "STATUS"]
        }

    # — 3) Si ya tengo mod_user, muestro el panel de actualización —
    if "mod_user" in st.session_state:
        mu = st.session_state.mod_user

        st.markdown(f"**Usuario:** {mu['first']} {mu['last']}  •  **ID:** {mu['id']}")
        st.markdown(f"**Estado actual:** {mu['status'].upper()}")

        # Cargar posibles estados
        estados_df = pd.read_sql_query(
            "SELECT ID, NAME FROM STATUS WHERE ID IN (5,6)", conn
        )
        estados_df["NAME_UP"] = estados_df["NAME"].str.upper()

        new_status = st.selectbox(
            "Nuevo Estado",
            estados_df["NAME_UP"],
            key="mod_new_status"
        )

        # Botones de acción
        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("✅ Actualizar Estado"):
                new_id = int(
                    estados_df.loc[estados_df["NAME_UP"] == new_status, "ID"].iloc[0]
                )
                cur = conn.cursor()
                cur.execute(
                    "UPDATE USERS SET STATUS_ID = ? WHERE ID = ?",
                    (new_id, mu["id"])
                )
                conn.commit()
                st.success("Estado actualizado correctamente.")
                # limpio el estado para volver al principio
                del st.session_state.mod_user

        with col2:
            if st.button("↩️ Volver a buscar"):
                del st.session_state.mod_user
                
def logout():
    st.session_state.pop("user", None)


def exportar_paquete_web():
    st.header("⬇️ Exportar Tipificación")
    paquetes = pd.read_sql_query(
        "SELECT DISTINCT NUM_PAQUETE FROM ASIGNACION_TIPIFICACION ORDER BY NUM_PAQUETE",
        conn
    )['NUM_PAQUETE'].tolist()
    pkg = st.selectbox("Paquete", paquetes)
    fmt = st.selectbox("Formato", ["CSV","TXT"])
    if st.button("Exportar"):
        sep = "," if fmt=="CSV" else ";"
        df = pd.read_sql_query(
            """
            SELECT
              a.RADICADO,
              CONVERT(varchar(10),t.FECHA_SERVICIO,103) FECHA,
              d.AUTORIZACION, d.CODIGO_SERVICIO,
              CONVERT(int,d.CANTIDAD) CANTIDAD,
              CONVERT(int,d.VLR_UNITARIO) VLR_UNITARIO,
              t.DIAGNOSTICO,
              CONVERT(varchar(10),GETDATE(),103) CreatedOn,
              u2.NUM_DOC ModifiedBy,
              td.NAME TipoDocumento,
              a.NUM_DOC NumeroDocumento,
              CONVERT(int,d.COPAGO) COPAGO
            FROM ASIGNACION_TIPIFICACION a
            JOIN TIPIFICACION t    ON t.ASIGNACION_ID = a.RADICADO
            JOIN TIPIFICACION_DETALLES d ON d.TIPIFICACION_ID = t.ID
            JOIN USERS u2          ON u2.ID = t.USER_ID
            JOIN TIPO_DOC td       ON td.ID = t.TIPO_DOC_ID
            WHERE a.NUM_PAQUETE=?
            ORDER BY a.RADICADO, t.FECHA_SERVICIO
            """, conn, params=[int(pkg)]
        )
        buf = io.StringIO()
        df.to_csv(buf, sep=sep, index=False)
        st.download_button("📥 Descargar", buf.getvalue(), file_name=f"paquete_{pkg}.{fmt.lower()}")
# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------
def dashboard_page():
    user = st.session_state.user

    # Sidebar: rol + menú + cerrar sesión
    with st.sidebar:
        # Nombre centrado
        st.markdown(
            f"<div style='text-align: center; margin-bottom: 1rem; justify-content: center; font-size: 25px; -webkit-text-stroke-width: 1px'>"
            f"{user[1]} {user[2]}"
            f"</div>",
            unsafe_allow_html=True
        )

        # Roles
        cur = conn.cursor()
        cur.execute(
            "SELECT R.ID, R.NAME FROM USER_ROLES UR JOIN ROL R ON UR.ROL_ID=R.ID WHERE UR.USER_ID=?",
            (user[0],)
        )
        roles = cur.fetchall()
        cur.close()
        if not roles:
            st.warning("Sin roles asignados")
            return

        role_map = {name: rid for rid, name in roles}
        selected_role = option_menu(
            "Selecciona tu rol",
            options=list(role_map.keys()),
            icons=["person-circle"] * len(roles),
            menu_icon="gear",
            default_index=0,
            orientation="vertical",
        )
        rid = role_map[selected_role]

        # Menú de acciones
        menu_items = MENU_BY_ROLE.get(rid, [])
        selected_action = option_menu(
            "Menú",
            options=menu_items,
            icons=[
                "cloud-upload","person-plus","bar-chart-line",
                "pencil","download","play-btn"
            ][:len(menu_items)],
            menu_icon="app",
            default_index=0,
            orientation="vertical",
        )
        
        # Botón de cerrar sesión, centrado
    st.markdown("")  # un separador en blanco opcional
    st.sidebar.button(
        "🚪 Cerrar sesión",
        on_click=logout,
        key="logout_btn"
    )
    # KPI en la cabecera
    st.markdown("<h2 style='text-align:center; margin-top:1rem;'>📋 Dashboard Tipificador Médica</h2>", unsafe_allow_html=True)
    st.markdown("<hr style='border:1px solid #ddd'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Pendientes", _get_pending_count())
    c2.metric("Usuarios activos", _get_active_users())
    c3.metric("Total tipificaciones", _get_total_tips())
    st.markdown("<hr style='border:1px solid #ddd'>", unsafe_allow_html=True)

    # Enrutamiento
    if selected_action == "Cargar Paquete":
        cargar_paquete_web()
    elif selected_action == "Crear Usuario":
        crear_usuario_web()
    elif selected_action == "Ver Progreso":
        ver_progreso_web()
    elif selected_action == "Modificar Estado Usuario":
        modificar_estado_usuario_web()
    elif selected_action == "Exportar Tipificación":
        exportar_paquete_web()
    elif selected_action == "Iniciar Tipificación":
        iniciar_tipificacion_web()


def main():
    if "user" not in st.session_state:
        login_page()
    else:
        dashboard_page()

if __name__ == "__main__":
    main()
