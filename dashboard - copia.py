
# — Librerías estándar —
import datetime
import re
import tkinter as tk
from tkinter import messagebox, filedialog, ttk

# — Terceros —
import pandas as pd
import bcrypt
import customtkinter as ctk          # <-- sólo esto para CustomTkinter
from PIL import Image
import requests
import cairosvg
from io import BytesIO

# — Módulos propios —
import subprocess, sys, os
from db_connection import conectar_sql_server


def safe_destroy(win):
    # cancela todos los after del intérprete
    try:
        for aid in win.tk.call('after', 'info'):
            try:
                win.tk.call('after', 'cancel', aid)
            except Exception:
                pass
    except Exception:
        pass
    win.destroy()



# Tu tema y apariencia
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

def load_icon_from_url(url, size):
    resp = requests.get(url)
    resp.raise_for_status()
    # convierte SVG bytes a PNG bytes
    png_bytes = cairosvg.svg2png(bytestring=resp.content,
                                 output_width=size[0],
                                 output_height=size[1])
    img = Image.open(BytesIO(png_bytes))
    return ctk.CTkImage(light_image=img, dark_image=img, size=size)


def cargar_paquete(root, conn):
    import traceback
    import pandas as pd
    from tkinter import filedialog, messagebox

    # 1) Calcular siguiente NUM_PAQUETE
    cur = conn.cursor()
    try:
        cur.execute("SELECT MAX(NUM_PAQUETE) FROM ASIGNACION_TIPIFICACION WHERE STATUS_ID = 1")
        ultimo = cur.fetchone()[0] or 0
    except Exception:
        traceback.print_exc()
        ultimo = 0
    NUM_PAQUETE = ultimo + 1

    # 2) Seleccionar archivo
    path = filedialog.askopenfilename(
        parent=root,
        title="Selecciona el archivo de paquete",
        filetypes=[("Excel/CSV", "*.xlsx *.xls *.csv"), ("Todos", "*.*")]
    )
    if not path:
        return

    # 3) Leer con pandas
    try:
        if path.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(path)
        else:
            df = pd.read_csv(path)
    except Exception:
        messagebox.showerror("Error lectura", "No se pudo leer el archivo. Verifica formato.")
        return

    total = len(df)
    if total == 0:
        messagebox.showinfo("Sin datos", "El archivo está vacío.")
        return

    inserted = 0

    # 4) Permitir insertar RADICADO manualmente
    cur.execute("SET IDENTITY_INSERT ASIGNACION_TIPIFICACION ON;")

    # 5) Insertar filas (incluyendo RADICADO)
    for idx, row in df.iterrows():
        try:
            # Leer y sanitizar RADICADO
            radicado       = int(row["RADICADO"])
            # Sanitizar campos obligatorios
            nit            = int(row["NIT"])
            razon          = str(row["RAZON_SOCIAL"])
            factura        = str(row["FACTURA"])
            valor_factura  = int(row["VALOR_FACTURA"])
            fecha_factura  = row["FECHA FACTURA"]
            fecha_rad      = row["FECHA RADICACION"]
            tipo_doc_id    = str(row["TIPO DOC"])
            num_doc        = int(row["NUM DOC"])
            estado_factura = str(row.get("ESTADO_FACTURA", "")).strip() or None
            imagen         = str(row.get("IMAGEN", "")).strip() or None

            # Sanitizar opcionales
            def s(col):
                v = row.get(col)
                return None if pd.isna(v) else str(v)

            rad_img   = s("RADICADO_IMAGEN")
            linea     = s("LINEA")
            id_asig   = s("ID ASIGNACION")
            est_pys   = s("ESTADO PYS")
            obs_pys   = s("OBSERVACION PYS")
            linea_pys = s("LINEA PYS")
            rangos    = s("RANGOS")
            def_col   = s("Def")

            cur.execute(
                """
                INSERT INTO ASIGNACION_TIPIFICACION
                  (RADICADO,
                   NIT, RAZON_SOCIAL, FACTURA, VALOR_FACTURA,
                   FECHA_FACTURA, FECHA_RADICACION, TIPO_DOC_ID,
                   NUM_DOC, ESTADO_FACTURA, IMAGEN, RADICADO_IMAGEN,
                   LINEA, ID_ASIGNACION, ESTADO_PYS, OBSERVACION_PYS,
                   LINEA_PYS, RANGOS, DEF, STATUS_ID, NUM_PAQUETE)
                VALUES
                  (?,       ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                radicado,
                nit, razon, factura, valor_factura,
                fecha_factura, fecha_rad, tipo_doc_id,
                num_doc, estado_factura, imagen,
                rad_img, linea, id_asig, est_pys,
                obs_pys, linea_pys, rangos, def_col,
                NUM_PAQUETE
            )
            inserted += 1

        except Exception:
            print(f"Error insertando fila {idx}:")
            traceback.print_exc()

    # 6) Desactivar IDENTITY_INSERT y cerrar cursor
    cur.execute("SET IDENTITY_INSERT ASIGNACION_TIPIFICACION OFF;")
    conn.commit()
    cur.close()

    messagebox.showinfo(
        "Carga completa",
        f"Total filas: {total}\nInsertadas: {inserted}\nPaquete: {NUM_PAQUETE}"
    )

    # 7) Popup para seleccionar campos a mostrar
    sel = ctk.CTkToplevel(root)
    sel.title(f"Paquete {NUM_PAQUETE}: Selecciona campos")
    campos = [
        "FECHA_SERVICIO", "TIPO_DOC_ID", "NUM_DOC", "DIAGNOSTICO",
        "AUTORIZACION", "CODIGO_SERVICIO", "CANTIDAD", "VLR_UNITARIO",
        "COPAGO", "OBSERVACION"
    ]
    vars_chk = {}
    for campo in campos:
        vars_chk[campo] = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(sel, text=campo, variable=vars_chk[campo])\
            .pack(anchor="w", padx=20, pady=2)

    def guardar_campos():
        cur2 = conn.cursor()
        for campo, var in vars_chk.items():
            if var.get():
                cur2.execute(
                    "INSERT INTO PAQUETE_CAMPOS (NUM_PAQUETE, campo) VALUES (?, ?)",
                    NUM_PAQUETE, campo
                )
        conn.commit()
        cur2.close()
        sel.destroy()
        messagebox.showinfo("Guardado", f"Campos del paquete {NUM_PAQUETE} guardados.")

    ctk.CTkButton(sel, text="Guardar", command=guardar_campos).pack(pady=10)

def crear_usuario(root, conn):
    # Funciones de validación
    def only_letters(P):
        # Permite solo letras, espacios o cadena vacía
        return P == "" or all(c.isalpha() or c.isspace() for c in P)

    def only_digits(P):
        # Permite solo dígitos o cadena vacía
        return P == "" or P.isdigit()

    # Registramos las validaciones en Tcl
    vcmd_letters = (root.register(only_letters), '%P')
    vcmd_digits  = (root.register(only_digits),  '%P')

    # Crear ventana secundaria
    top = ctk.CTkToplevel(root)
    top.title("Crear Usuario")
    top.geometry("500x600")
    top.resizable(False, False)

    # Recuperar catálogos
    cur = conn.cursor()
    cur.execute("SELECT ID, NAME FROM TIPO_DOC")
    tipos = cur.fetchall()
    cur.execute("SELECT ID, NAME FROM STATUS WHERE ID IN (?, ?)", (5, 6))
    statuses = cur.fetchall()
    cur.execute("SELECT ID, NAME FROM ROL")
    roles = cur.fetchall()
    cur.close()

    tipo_map   = {name: tid for tid, name in tipos}
    status_map = {name: sid for sid, name in statuses}

    # Variables
    fn_var   = tk.StringVar()
    ln_var   = tk.StringVar()
    doc_var  = tk.StringVar()
    pwd_var  = tk.StringVar()
    tipo_var = tk.StringVar(value=tipos[0][1])
    stat_var = tk.StringVar(value=statuses[0][1])

    # Centrar el frame dentro del Toplevel
    top.grid_rowconfigure(0, weight=1)
    top.grid_columnconfigure(0, weight=1)
    frm = ctk.CTkFrame(top, corner_radius=8)
    frm.grid(row=0, column=0, padx=20, pady=20)

    # Campos de texto y combos
    labels = [
        ("Nombres:", fn_var, "entry"),
        ("Apellidos:", ln_var, "entry"),
        ("Tipo Doc:", tipo_var, "combo", [n for _, n in tipos]),
        ("N° Documento:", doc_var, "entry"),
        ("Contraseña:", pwd_var, "entry_pass"),
        ("Status:", stat_var, "combo", [n for _, n in statuses])
    ]
    for i, (text, var, kind, *opt) in enumerate(labels):
        ctk.CTkLabel(frm, text=text).grid(row=i, column=0, sticky="w", pady=(10,0))

        if kind == "entry":
            widget = ctk.CTkEntry(
                frm,
                textvariable=var,
                width=300,
                takefocus=True,
                validate="key",
                validatecommand=vcmd_letters
            )
            # Sólo al perder foco forzamos mayúsculas
            widget.bind("<FocusOut>", lambda e, v=var: v.set(v.get().upper()))

        elif kind == "entry_pass":
            widget = ctk.CTkEntry(
                frm,
                textvariable=var,
                show="*",
                width=300,
                takefocus=True
            )
            widget.bind("<FocusOut>", lambda e, v=var: v.set(v.get().upper()))

        elif kind == "combo":
            widget = ctk.CTkComboBox(
                frm,
                values=opt[0],
                variable=var,
                width=300,
                takefocus=True
            )


        widget.grid(row=i, column=1, padx=(10,0), pady=(10,0))
        if i == 0:
            widget.focus()

    # Checkboxes de roles
    ctk.CTkLabel(frm, text="Roles:").grid(row=len(labels), column=0, sticky="nw", pady=(10,0))
    rol_vars = {}
    chk_frame = ctk.CTkFrame(frm)
    chk_frame.grid(row=len(labels), column=1, sticky="w", pady=(10,0))
    for j, (rid, rname) in enumerate(roles):
        var_chk = tk.BooleanVar()
        rol_vars[rid] = var_chk
        ctk.CTkCheckBox(chk_frame, text=rname, variable=var_chk).grid(row=j, column=0, sticky="w", pady=2)

    # Función para guardar usuario
    def guardar_usuario(event=None):
        if not all([fn_var.get(), ln_var.get(), doc_var.get(), pwd_var.get()]):
            messagebox.showwarning("Faltan datos", "Completa todos los campos.")
            return
        try:
            first_name = fn_var.get().strip()
            last_name  = ln_var.get().strip()
            num_doc    = int(doc_var.get().strip())
            password   = pwd_var.get().strip()
            type_id    = tipo_map[tipo_var.get()]
            status_id  = status_map[stat_var.get()]
            selected   = [rid for rid, v in rol_vars.items() if v.get()]

            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO USERS 
                  (FIRST_NAME, LAST_NAME, TYPE_DOC_ID, NUM_DOC, PASSWORD, STATUS_ID)
                OUTPUT INSERTED.ID
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                first_name, last_name, type_id, num_doc, password, status_id
            )
            new_id = cur.fetchone()[0]

            for rid in selected:
                cur.execute(
                    "INSERT INTO USER_ROLES (USER_ID, ROL_ID) VALUES (?, ?)",
                    new_id, rid
                )

            conn.commit()
            cur.close()
            messagebox.showinfo("Éxito", f"Usuario creado con ID {new_id}")
            top.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # Botón Guardar
    btn = ctk.CTkButton(frm, text="Guardar Usuario", command=guardar_usuario, width=200, takefocus = True)
    btn.grid(row=len(labels)+1, column=0, columnspan=2, pady=20)
    top.bind("<Return>", guardar_usuario)


class AutocompleteEntry(ctk.CTkEntry):
    def __init__(self, parent, values, textvariable=None, **kwargs):
        # Preparar StringVar (propio o el que pase el usuario)
        if textvariable is None:
            self.var = tk.StringVar()
        else:
            self.var = textvariable

        # Evitar duplicar textvariable
        kwargs.pop('textvariable', None)
        super().__init__(parent, **kwargs)
        self.configure(textvariable=self.var)

        self._values = values
        self._listbox_window = None
        self._listbox = None

        # Bindings
        self.var.trace_add('write', lambda *args: self._show_matches())
        self.bind('<Down>', self._on_down)
        self.bind('<Escape>', lambda e: self._hide_listbox())
        # Evitar cerrar desplegable al interactuar
        self.bind('<FocusOut>', lambda e: None)

    def _show_matches(self):
        txt = self.var.get().strip().lower()
        if not txt:
            return self._hide_listbox()

        matches = [v for v in self._values if v.lower().startswith(txt)]
        if not matches:
            return self._hide_listbox()

        if not self._listbox_window:
            self._listbox_window = tk.Toplevel(self)
            self._listbox_window.overrideredirect(True)
            lb = tk.Listbox(self._listbox_window)
            lb.pack(expand=True, fill='both')
            lb.bind('<<ListboxSelect>>', self._on_listbox_select)
            lb.bind('<Return>',          self._on_listbox_select)
            lb.bind('<Up>',              self._on_listbox_nav)
            lb.bind('<Down>',            self._on_listbox_nav)
            self._listbox = lb
        else:
            self._listbox.delete(0, tk.END)

        for m in matches:
            self._listbox.insert(tk.END, m)

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = self.winfo_width()
        h = min(100, len(matches) * 20)
        self._listbox_window.geometry(f"{w}x{h}+{x}+{y}")

    def _on_listbox_select(self, event):
        if not self._listbox:
            return
        sel = self._listbox.get(self._listbox.curselection())
        self.var.set(sel)
        self.icursor(tk.END)
        self._hide_listbox()

    def _on_listbox_nav(self, event):
        if not self._listbox:
            return "break"
        idx = self._listbox.curselection()
        if not idx:
            self._listbox.selection_set(0)
            idx = (0,)
        i = idx[0]
        if event.keysym == 'Up' and i > 0:
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(i - 1)
        elif event.keysym == 'Down' and i < self._listbox.size() - 1:
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(i + 1)
        return "break"

    def _on_down(self, event):
        self._show_matches()
        if self._listbox:
            self._listbox.focus_set()
            self._listbox.selection_set(0)
            self._listbox.activate(0)
        return "break"

    def _hide_listbox(self):
        if self._listbox_window:
            self._listbox_window.destroy()
            self._listbox_window = None
            self._listbox = None


# -----------------------------
# Función iniciar_tipificacion
# -----------------------------
def iniciar_tipificacion(parent_root, conn, current_user_id):
    cur = conn.cursor()
    cur.execute("SELECT MAX(NUM_PAQUETE) FROM PAQUETE_CAMPOS")
    pkg = cur.fetchone()[0] or 0

    # Obtenemos los campos permitidos para este paquete
    cur.execute("SELECT campo FROM PAQUETE_CAMPOS WHERE NUM_PAQUETE = ?", pkg)
    campos_paquete = {r[0] for r in cur.fetchall()}
    cur.close()

    # Seleccionamos una asignación aleatoria pendiente en este paquete
    cur = conn.cursor()
    cur.execute(
        """
        SELECT TOP 1 RADICADO, NIT, FACTURA
          FROM ASIGNACION_TIPIFICACION
         WHERE STATUS_ID = 1 AND NUM_PAQUETE = ?
         ORDER BY NEWID()
        """, pkg)
    row = cur.fetchone()
    if not row:
        messagebox.showinfo("Sin asignaciones", "No hay asignaciones pendientes.")
        cur.close()
        return
    radicado, nit, factura = row
    cur.execute(
        "UPDATE ASIGNACION_TIPIFICACION SET STATUS_ID = 2 WHERE RADICADO = ?", radicado)
    conn.commit()
    cur.close()

    # Ventana principal
    win = ctk.CTkToplevel(parent_root)
    win.title(f"Tipificación · Paquete {pkg}")
    win.geometry("850x1000")
    win.grab_set()

    container = ctk.CTkFrame(win, fg_color="#1e1e1e")
    container.pack(fill='both', expand=True)
    card = ctk.CTkFrame(container, fg_color="#2b2b2b", width=820, height=880)
    card.place(relx=0.5, rely=0.5, anchor='center')

    # Avatar y título
    avatar = load_icon_from_url(
        "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/user-circle.svg",
        size=(80, 80)
    )
    ctk.CTkLabel(card, image=avatar, text="").pack(pady=(20, 5))
    ctk.CTkLabel(
        card,
        text=f"📦 Paquete #{pkg}",
        font=ctk.CTkFont(size=26, weight='bold'),
        text_color='white'
    ).pack(pady=(0, 15))

    # -----------------------------
    # Campos de solo lectura: Radicado, NIT, Factura
    # -----------------------------
    read_frame = ctk.CTkFrame(card, fg_color='transparent')
    read_frame.pack(fill='x', padx=30)
    read_frame.grid_columnconfigure(1, weight=1)
    for i, (lbl, val) in enumerate([
        ('Radicado', radicado),
        ('NIT', nit),
        ('Factura', factura)
    ]):
        ctk.CTkLabel(read_frame, text=f"{lbl}:", anchor='w').grid(
            row=i, column=0, sticky='w', pady=5)
        ctk.CTkEntry(
            read_frame,
            textvariable=tk.StringVar(value=str(val)),
            state='readonly',
            width=300
        ).grid(row=i, column=1, sticky='ew', pady=5, padx=(10, 0))

    # Scrollable para campos editables
    scroll = ctk.CTkScrollableFrame(card, fg_color='#2b2b2b', width=800, height=600)
    scroll.pack(padx=20, pady=(10, 0))

    field_vars = {}
    widgets = {}
    detail_vars = []

    def mark_required(w, var):
        def chk(e=None):
            if not var.get().strip():
                w.configure(border_color='red', border_width=2)
            else:
                w.configure(border_color='#2b2b2b', border_width=1)
        w.bind('<FocusOut>', chk)

    def make_field(label_text, icon_url=None):
        frame = ctk.CTkFrame(scroll, fg_color='transparent')
        frame.pack(fill='x', pady=8)
        if icon_url:
            ico = load_icon_from_url(icon_url, size=(20, 20))
            ctk.CTkLabel(frame, image=ico, text='').pack(side='left', padx=(0, 5))
        ctk.CTkLabel(frame, text=label_text, anchor='w').pack(fill='x')
        return frame

    # -----------------------------
    # Campos fijos (solo si están en PAQUETE_CAMPOS)
    # -----------------------------
    if 'FECHA_SERVICIO' in campos_paquete:
        frm = make_field('Fecha Servicio:',
                         'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/calendar.svg')
        var_fecha = tk.StringVar()
        entry_fecha = ctk.CTkEntry(
            frm,
            textvariable=var_fecha,
            placeholder_text='DD/MM/AAAA',
            width=300,
            validate='key',
            validatecommand=(win.register(lambda s: bool(re.match(r"^[0-9/]$", s))), '%S')
        )
        entry_fecha.pack(fill='x', pady=(5, 0))
        lbl_err_fecha = ctk.CTkLabel(frm, text='', text_color='red')
        lbl_err_fecha.pack(fill='x')
        field_vars['FECHA_SERVICIO'] = var_fecha
        widgets['FECHA_SERVICIO'] = entry_fecha

        def val_fecha(e=None):
            txt = var_fecha.get().strip()
            try:
                d = datetime.datetime.strptime(txt, '%d/%m/%Y').date()
                if d > datetime.date.today():
                    raise ValueError
                entry_fecha.configure(border_color='#2b2b2b', border_width=1)
                lbl_err_fecha.configure(text='')
                return True
            except:
                entry_fecha.configure(border_color='red', border_width=2)
                lbl_err_fecha.configure(text='Fecha inválida')
                return False
        entry_fecha.bind('<FocusOut>', val_fecha)

    if 'TIPO_DOC_ID' in campos_paquete:
        frm = make_field('Tipo Doc:',
                         'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/id-card.svg')
        cur_td = conn.cursor()
        cur_td.execute("SELECT NAME FROM TIPO_DOC")
        opts_td = [r[0] for r in cur_td.fetchall()]
        cur_td.close()
        # Tipo Doc ID: sólo letras, forzar mayúsculas
        var_tipo = tk.StringVar()

        def on_tipo_change(var, *args):
            txt = var.get().upper()
            txt = ''.join(ch for ch in txt if 'A' <= ch <= 'Z')
            var.set(txt)

        # Nota: pasamos la referencia a on_tipo_change y Tkinter le añade
        # los 3 args (name, index, mode) que nosotros ignoramos con *args
        var_tipo.trace_add('write', lambda name, index, mode: on_tipo_change(var_tipo))

        entry_tipo = AutocompleteEntry(frm, opts_td, width=300, textvariable=var_tipo)
        entry_tipo.pack(fill='x', pady=(5, 0))

        field_vars['TIPO_DOC_ID'] = var_tipo
        widgets['TIPO_DOC_ID'] = entry_tipo
        mark_required(entry_tipo, var_tipo)



    if 'NUM_DOC' in campos_paquete:
        frm = make_field('Num Doc:',
                         'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/hashtag.svg')
        var_num = tk.StringVar()
        entry_num = ctk.CTkEntry(
            frm,
            textvariable=var_num,
            placeholder_text='Solo dígitos',
            width=300,
            validate='key',
            validatecommand=(win.register(lambda s: s.isdigit()), '%S')
        )
        entry_num.pack(fill='x', pady=(5, 0))
        field_vars['NUM_DOC'] = var_num
        widgets['NUM_DOC'] = entry_num
        mark_required(entry_num, var_num)

    if 'DIAGNOSTICO' in campos_paquete:
        frm = make_field(
        'Diagnóstico:',
        'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/stethoscope.svg'
        )

        # 1) Preparamos la lista de opciones
        cur_dx = conn.cursor()
        cur_dx.execute("SELECT CODIGO FROM TBL_CIE10")
        opts_dx = [r[0] for r in cur_dx.fetchall()]
        cur_dx.close()

        # 2) Creamos el StringVar
        var_diag = tk.StringVar()

        # 3) Callback que fuerza mayúsculas y deja solo A–Z y dígitos
        def on_diag_change(var, *args):
            txt = var.get().upper()
            txt = ''.join(ch for ch in txt if ('A' <= ch <= 'Z') or ch.isdigit())
            var.set(txt)

        # 4) Asociamos el trace_add
        var_diag.trace_add('write', lambda name, index, mode: on_diag_change(var_diag))

        # 5) Creamos el AutocompleteEntry con nuestro StringVar
        entry_diag = AutocompleteEntry(frm, opts_dx, width=300, textvariable=var_diag)
        entry_diag.pack(fill='x', pady=(5, 0))

        # 6) Como antes, registramos en los diccionarios de validación
        field_vars['DIAGNOSTICO'] = var_diag
        widgets['DIAGNOSTICO'] = entry_diag
        mark_required(entry_diag, var_diag)


    # -----------------------------
    # Campos dinámicos (detalles)
    # -----------------------------
    DETAIL_ICONS = {
        'AUTORIZACION':    'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/file-invoice.svg',
        'CODIGO_SERVICIO': 'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/tools.svg',
        'CANTIDAD':        'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/list-ol.svg',
        'VLR_UNITARIO':    'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/dollar-sign.svg',
        'COPAGO':          'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/coins.svg',
        'OBSERVACION':     'https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/align-left.svg',
    }

    def add_service_block():
        dv = {}
        for campo, icon_url in DETAIL_ICONS.items():
            if campo not in campos_paquete:
                continue

            frm = make_field(campo.replace('_', ' ') + ':', icon_url)
            default = '0' if campo == 'COPAGO' else ''
            var = tk.StringVar(master=frm, value=default)

            if campo == 'AUTORIZACION':
                # Validar hasta 9 dígitos
                def only_digits_len(P):
                    return P == "" or (P.isdigit() and len(P) <= 9)
                vcmd_auth = (win.register(only_digits_len), '%P')

                # Entry y packing
                w = ctk.CTkEntry(
                    frm,
                    textvariable=var,
                    width=300,
                    placeholder_text='Solo 9 dígitos',
                    validate='key',
                    validatecommand=vcmd_auth
                )
                w.pack(fill='x', pady=(5, 0))

                # Label de error debajo del entry
                lbl_err = ctk.CTkLabel(frm, text='', text_color='red')
                lbl_err.pack(fill='x', pady=(2, 8))

                # Validación al perder foco
                def val_autorizacion(e=None, var=var, w=w, lbl=lbl_err):
                    txt = var.get().strip()
                    if not txt:
                        w.configure(border_color='red', border_width=2)
                        lbl.configure(text='Autorización obligatoria')
                        return False
                    if len(txt) != 9:
                        w.configure(border_color='red', border_width=2)
                        lbl.configure(text='Debe tener 9 dígitos')
                        return False
                    w.configure(border_color='#2b2b2b', border_width=1)
                    lbl.configure(text='')
                    return True

                w.bind('<FocusOut>', val_autorizacion)
                dv['VALIDAR_AUTORIZACION'] = val_autorizacion

            elif campo == 'CODIGO_SERVICIO':
                cur_cs = conn.cursor()
                cur_cs.execute("SELECT PRO_MAP_MAPIISS FROM TBL_HOMOLOGACION_MAPIS")
                opts_cs = [r[0] for r in cur_cs.fetchall()]
                cur_cs.close()

                w = AutocompleteEntry(frm, opts_cs, width=300, textvariable=var)
                w.pack(fill='x', pady=(5, 0))

            elif campo in ('CANTIDAD', 'VLR_UNITARIO', 'COPAGO'):
                # Solo dígitos permitidos
                def only_digits(P):
                    return P == "" or P.isdigit()
                vcmd_num = (win.register(only_digits), '%P')

                w = ctk.CTkEntry(
                    frm,
                    textvariable=var,
                    width=300,
                    placeholder_text=default,
                    validate='key',
                    validatecommand=vcmd_num
                )
                w.pack(fill='x', pady=(5, 0))

            else:
                # Otros campos sin validación adicional
                w = ctk.CTkEntry(
                    frm,
                    textvariable=var,
                    width=300,
                    placeholder_text=default
                )
                w.pack(fill='x', pady=(5, 0))

            # Guardar referencia
            dv[campo] = {'var': var, 'widget': w}

        # Fuera del for, añadimos el diccionario de este bloque
        detail_vars.append(dv)


    if any(c in campos_paquete for c in DETAIL_ICONS):
        add_service_block()

    # -----------------------------
    # Validar y guardar en BD
    # -----------------------------
    def validate_and_save(final):
        # ¿Alguna observación completada?
        any_obs = any(
            dv.get('OBSERVACION', {}).get('var').get().strip()
            for dv in detail_vars
        )
        ok = True

        if not any_obs:
            # Chequeo obligatorio de fecha si existe
            if 'FECHA_SERVICIO' in field_vars:
                ok &= val_fecha()

            # Campos fijos obligatorios
            for k, v in field_vars.items():
                w = widgets[k]
                if not v.get().strip():
                    w.configure(border_color='red', border_width=2)
                    ok = False
                else:
                    w.configure(border_color='#2b2b2b', border_width=1)

            # Detalle: si no hay observación en ese bloque, validar sus campos
            for dv in detail_vars:
                obs = dv.get('OBSERVACION', {}).get('var').get().strip()
                if obs:
                    # Si éste bloque tiene observación, salta validación de sus campos
                    continue

                # Autorización
                if 'VALIDAR_AUTORIZACION' in dv and not dv['VALIDAR_AUTORIZACION']():
                    ok = False

                # Resto de campos del detalle
                for campo, info in dv.items():
                    if campo in ('OBSERVACION', 'VALIDAR_AUTORIZACION'):
                        continue
                    w = info['widget']
                    if not info['var'].get().strip():
                        w.configure(border_color='red', border_width=2)
                        ok = False
                    else:
                        w.configure(border_color='#2b2b2b', border_width=1)

        return ok

    def do_save(final=False):
        if not validate_and_save(final):
            return

        cur2 = conn.cursor()
        asig_id = int(radicado)

        # --- 1) Preparar datos tipificación ---
        num_doc_i = int(var_num.get().strip()) if 'NUM_DOC' in field_vars and var_num.get().strip() else None
        fecha_obj = (datetime.datetime.strptime(var_fecha.get().strip(), "%d/%m/%Y").date()
                    if 'FECHA_SERVICIO' in field_vars and var_fecha.get().strip() else None)
        # TipoDoc
        if 'TIPO_DOC_ID' in field_vars and var_tipo.get().strip():
            cur2.execute("SELECT ID FROM TIPO_DOC WHERE UPPER(NAME)=?", var_tipo.get().strip().upper())
            row = cur2.fetchone()
            tipo_doc_id = row[0] if row else None
        else:
            tipo_doc_id = None
        # Diagnóstico: si está vacío, usamos None para que SQL reciba NULL
        raw = var_diag.get().strip().upper()
        diag_code = raw if raw else None

        # --- 2) Insertar cabecera TIPIFICACION con USER_ID ---
        cur2.execute("""
            INSERT INTO TIPIFICACION
            (ASIGNACION_ID, FECHA_SERVICIO, TIPO_DOC_ID, NUM_DOC, DIAGNOSTICO, USER_ID)
            OUTPUT INSERTED.ID
            VALUES (?, ?, ?, ?, ?, ?)
        """, asig_id, fecha_obj, tipo_doc_id, num_doc_i, diag_code, current_user_id)
        tip_id = cur2.fetchone()[0]

        # --- 3) Insertar detalles y detectar si hay observaciones ---
        tiene_obs = False
        for dv in detail_vars:
            # Leer cada campo
            auth   = dv.get('AUTORIZACION', {}).get('var').get().strip() or None
            auth   = int(auth) if auth else None

            cs     = dv.get('CODIGO_SERVICIO', {}).get('var').get().strip().upper() or None
            qty    = dv.get('CANTIDAD', {}).get('var').get().strip() or None
            qty    = int(qty) if qty else None

            valor  = dv.get('VLR_UNITARIO', {}).get('var').get().strip() or None
            valor  = float(valor) if valor else None

            copago = dv.get('COPAGO', {}).get('var').get().strip() or None
            copago = float(copago) if copago else None

            obs    = dv.get('OBSERVACION', {}).get('var').get().strip() or None
            if obs:
                tiene_obs = True

            # Si todo es None, saltamos
            if all(v is None for v in (auth, cs, qty, valor, copago, obs)):
                continue

            # (Opcional) validaciones de cs...
            cur2.execute("""
                INSERT INTO TIPIFICACION_DETALLES
                (TIPIFICACION_ID, AUTORIZACION, CODIGO_SERVICIO, CANTIDAD, VLR_UNITARIO, COPAGO, OBSERVACION)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, tip_id, auth, cs, qty, valor, copago, obs)

        conn.commit()

        # --- 4) Actualizar estado ASIGNACION_TIPIFICACION ---
        nuevo_status = 4 if tiene_obs else 3
        cur2.execute(
            "UPDATE ASIGNACION_TIPIFICACION SET STATUS_ID = ? WHERE RADICADO = ?",
            (nuevo_status, asig_id)
        )
        conn.commit()
        cur2.close()

        # --- 5) Cerrar ventana y continuar/volver ---
        win.destroy()
        if not final:
            iniciar_tipificacion(parent_root, conn, current_user_id)
        else:
            if parent_root:
                parent_root.deiconify()

    # -----------------------------
    # Botonera
    # -----------------------------
    footer = ctk.CTkFrame(card, fg_color='transparent')
    footer.pack(fill='x', pady=10, padx=30)

    save_img = load_icon_from_url(
        "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/save.svg", size=(18,18)
    )
    btn_save = ctk.CTkButton(
        footer, text="Guardar y siguiente", image=save_img, compound="left",
        fg_color="#28a745", hover_color="#218838",
        command=lambda: do_save(final=False)
    )
    btn_save.pack(side='left', expand=True, fill='x', padx=5)

    add_img = load_icon_from_url(
        "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/plus-circle.svg", size=(18,18)
    )
    btn_add = ctk.CTkButton(
        footer, text="Agregar servicio", image=add_img, compound="left",
        fg_color="#17a2b8", hover_color="#138496",
        command=add_service_block
    )
    btn_add.pack(side='left', expand=True, fill='x', padx=5)

    exit_img = load_icon_from_url(
        "https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/solid/sign-out-alt.svg", size=(18,18)
    )
    btn_exit = ctk.CTkButton(
        footer, text="Salir y Guardar", image=exit_img, compound="left",
        fg_color="#dc3545", hover_color="#c82333",
        command=lambda: do_save(final=True)
    )
    btn_exit.pack(side='left', expand=True, fill='x', padx=5)

    for b in (btn_save, btn_add, btn_exit):
        b.bind("<Return>", lambda e, btn=b: btn.invoke())

def ver_progreso(root, conn):
    # 1) Crear ventana principal
    win = ctk.CTkToplevel(root)
    win.title("Ver Progreso de Paquetes")
    win.geometry("600x400")
    win.grab_set()
    win.protocol("WM_DELETE_WINDOW", lambda w=win: safe_destroy(w))

    # 2) Marco de selección de paquete
    frm = ctk.CTkFrame(win, fg_color="transparent")
    frm.pack(fill="x", padx=20, pady=(20, 0))
    ctk.CTkLabel(frm, text="Selecciona paquete:").grid(row=0, column=0, sticky="w")
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT NUM_PAQUETE FROM ASIGNACION_TIPIFICACION ORDER BY NUM_PAQUETE")
    paquetes = [str(r[0]) for r in cur.fetchall()]
    cur.close()
    if not paquetes:
        messagebox.showinfo("Sin paquetes", "No hay paquetes para mostrar.")
        win.destroy()
        return

    pkg_var = tk.StringVar(value=paquetes[0])
    ctk.CTkOptionMenu(frm, values=paquetes, variable=pkg_var, width=120)\
        .grid(row=0, column=1, padx=(10,0))
    ctk.CTkButton(frm, text="Mostrar", width=100,
                  command=lambda: _cargar_tabs(win, conn, int(pkg_var.get())))\
        .grid(row=0, column=2, padx=(10,0))

    # 3) Tabview de CustomTkinter (fondo negro)
    tabs = ctk.CTkTabview(win, width=560, height=300)
    tabs.pack(padx=20, pady=20, fill="both", expand=True)
    tabs.add("Por Estado")
    tabs.add("Por Usuario")

    # Guardamos referencia a los frames internos
    win._tabview = tabs


def _cargar_tabs(win, conn, num_paquete):
    tabs = win._tabview

    # -- Pestaña “Por Estado” --
    frame1 = tabs.tab("Por Estado")
    for w in frame1.winfo_children(): w.destroy()

    cur = conn.cursor()
    cur.execute("""
        SELECT UPPER(s.NAME) AS ESTADO, COUNT(*) AS CNT
          FROM ASIGNACION_TIPIFICACION at
          JOIN STATUS s ON at.STATUS_ID = s.ID
         WHERE at.NUM_PAQUETE = ?
         GROUP BY s.NAME
         ORDER BY s.NAME
    """, (num_paquete,))
    datos = cur.fetchall(); cur.close()

    # Encabezados
    ctk.CTkLabel(frame1, text="ESTADO", anchor="w").grid(row=0, column=0, padx=5, pady=4)
    ctk.CTkLabel(frame1, text="CANTIDAD", anchor="e").grid(row=0, column=1, padx=5, pady=4)

    # Filas
    for i, (estado, cnt) in enumerate(datos, start=1):
        ctk.CTkLabel(frame1, text=estado, anchor="w")\
            .grid(row=i, column=0, sticky="w", padx=5, pady=2)
        ctk.CTkLabel(frame1, text=str(cnt), anchor="e")\
            .grid(row=i, column=1, sticky="e", padx=5, pady=2)


    # -- Pestaña “Por Usuario” --
    frame2 = tabs.tab("Por Usuario")
    for w in frame2.winfo_children(): w.destroy()

    cur = conn.cursor()
    cur.execute("""
        SELECT u.ID,
               u.FIRST_NAME + ' ' + u.LAST_NAME AS USUARIO,
               SUM(CASE WHEN at.STATUS_ID=2 THEN 1 ELSE 0 END) AS PENDIENTES,
               SUM(CASE WHEN at.STATUS_ID=3 THEN 1 ELSE 0 END) AS PROCESADOS,
               SUM(CASE WHEN at.STATUS_ID=4 THEN 1 ELSE 0 END) AS CON_OBS
          FROM TIPIFICACION t
          JOIN USERS u     ON t.USER_ID = u.ID
          JOIN ASIGNACION_TIPIFICACION at
            ON at.RADICADO = t.ASIGNACION_ID
         WHERE at.NUM_PAQUETE = ?
         GROUP BY u.ID, u.FIRST_NAME, u.LAST_NAME
         ORDER BY USUARIO
    """, (num_paquete,))
    usuarios = cur.fetchall(); cur.close()

    # Encabezados
    cols = ["ID", "USUARIO", "PENDIENTES", "PROCESADOS", "CON_OBS"]
    for j, h in enumerate(cols):
        ctk.CTkLabel(frame2, text=h, anchor="w")\
            .grid(row=0, column=j, padx=5, pady=4)

    # Filas
    for i, fila in enumerate(usuarios, start=1):
        for j, val in enumerate(fila):
            ctk.CTkLabel(frame2, text=str(val), anchor="w")\
                .grid(row=i, column=j, padx=5, pady=2)

# Subclase de AutocompleteEntry que fuerza mayúsculas y mantiene el desplegable
class UppercaseAutocompleteEntry(AutocompleteEntry):
    def __init__(self, parent, values, textvariable=None, **kwargs):
        super().__init__(parent, values, textvariable=textvariable, **kwargs)
        # quita cualquier traza previa
        for trace in self.var.trace_info():
            if trace[0] == 'write':
                self.var.trace_remove('write', trace[1])
        # añade nueva traza
        self.var.trace_add('write', self._on_var_write)

    def _on_var_write(self, *args):
        txt = self.var.get()
        up = txt.upper()
        if up != txt:
            pos = self.index(tk.INSERT)
            self.var.set(up)
            self.icursor(pos)
        # luego lanza el autocomplete normal
        self._show_matches()


def modificar_estado_usuario(root, conn):
    # 1) Crear ventana
    win = ctk.CTkToplevel(root)
    win.title("Modificar Estado de Usuario")
    win.geometry("500x350")
    win.grab_set()
    win.protocol("WM_DELETE_WINDOW", lambda w=win: safe_destroy(w))

    frm = ctk.CTkFrame(win, fg_color="transparent")
    frm.pack(padx=20, pady=20, fill="x")

    # 2) Cargo tipo_doc ID y NAME
    cur = conn.cursor()
    cur.execute("SELECT ID, NAME FROM TIPO_DOC")
    tipo_rows = cur.fetchall()  # [(1,'CC'),(2,'TI'),...]
    cur.close()
    tipo_map   = {name.upper(): tid for tid, name in tipo_rows}
    tipo_names = [name for _, name in tipo_rows]

    # Campo Autocomplete de TipoDoc (uppercase inside class)
    ctk.CTkLabel(frm, text="Tipo Doc:").grid(row=0, column=0, sticky="w", pady=5)
    entry_tipo = UppercaseAutocompleteEntry(
        frm,
        tipo_names,
        width=250
    )
    entry_tipo.grid(row=0, column=1, pady=5)

    # Num Doc
    ctk.CTkLabel(frm, text="Num Doc:").grid(row=1, column=0, sticky="w", pady=5)
    num_var = tk.StringVar()
    entry_num = ctk.CTkEntry(frm, textvariable=num_var, width=250)
    entry_num.grid(row=1, column=1, pady=5)

    # Botón Buscar
    ctk.CTkButton(frm, text="Buscar", width=100,
                  command=lambda: buscar_usuario()).grid(
        row=2, column=0, columnspan=2, pady=(10,20))

    # Área de resultados
    result_frame = ctk.CTkFrame(win)
    result_frame.pack(padx=20, pady=(0,20), fill="both", expand=True)

    def buscar_usuario():
        # limpio previos
        for w in result_frame.winfo_children():
            w.destroy()

        # obtengo tipo_id
        nombre = entry_tipo.get().strip().upper()
        tipo_id = tipo_map.get(nombre)
        if tipo_id is None:
            messagebox.showwarning("Error", "Tipo Doc no válido.")
            return

        # num doc
        try:
            nd = int(num_var.get().strip())
        except ValueError:
            messagebox.showwarning("Error", "Num Doc debe ser número.")
            return

        # consulta usuario
        cur2 = conn.cursor()
        cur2.execute("""
            SELECT u.ID, u.FIRST_NAME, u.LAST_NAME, u.STATUS_ID, s.NAME
              FROM USERS u
              JOIN STATUS s ON u.STATUS_ID = s.ID
             WHERE u.TYPE_DOC_ID=? AND u.NUM_DOC=? AND u.STATUS_ID IN (5,6)
        """, (tipo_id, nd))
        row = cur2.fetchone()
        cur2.close()

        if not row:
            messagebox.showinfo("No encontrado",
                                "No hay usuario en estado 5 o 6 con esos datos.")
            return

        user_id, fn, ln, st_id, st_name = row
        ctk.CTkLabel(result_frame,
                     text=f"Usuario: {fn} {ln}  (ID {user_id})",
                     anchor="w").pack(fill="x", pady=(0,5))
        ctk.CTkLabel(result_frame,
                     text=f"Estado actual: {st_name.upper()}",
                     anchor="w").pack(fill="x", pady=(0,10))

        # cargo estados 5 y 6
        cur3 = conn.cursor()
        cur3.execute("SELECT ID, NAME FROM STATUS WHERE ID IN (5,6)")
        estados = cur3.fetchall()  # [(5,"PENDIENTE"),(6,"RECHAZADO")]
        cur3.close()
        est_map   = {name.upper(): id_ for (id_, name) in estados}
        est_names = [name.upper() for (_, name) in estados]

        # Selector en lugar de Autocomplete
        ctk.CTkLabel(result_frame, text="Nuevo estado:").pack(anchor="w", pady=(5,0))
        estado_var = tk.StringVar(value=st_name.upper())
        opt = ctk.CTkOptionMenu(
            result_frame,
            values=est_names,
            variable=estado_var,
            width=250
        )
        opt.pack(pady=(0,10))

        def actualizar():
            sel = estado_var.get().strip().upper()
            new_id = est_map.get(sel)
            if new_id is None:
                messagebox.showwarning("Error", "Estado no válido.")
                return
            cur4 = conn.cursor()
            cur4.execute("UPDATE USERS SET STATUS_ID=? WHERE ID=?", (new_id, user_id))
            conn.commit()
            cur4.close()
            messagebox.showinfo("Listo", f"Estado cambiado a {sel}.")
            safe_destroy(win)

        ctk.CTkButton(result_frame, text="Actualizar", command=actualizar, width=120)\
            .pack(pady=(10,0))

    entry_tipo.focus()

def exportar_paquete(root, conn):
    import csv
    from tkinter import filedialog, messagebox

    # 1) Crear ventana
    win = ctk.CTkToplevel(root)
    win.title("Exportar Paquete")
    win.geometry("400x250")
    win.grab_set()
    win.protocol("WM_DELETE_WINDOW", lambda w=win: safe_destroy(w))

    frm = ctk.CTkFrame(win, fg_color="transparent")
    frm.pack(padx=20, pady=20, fill="x")

    # 2) Obtener lista de paquetes
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT NUM_PAQUETE FROM ASIGNACION_TIPIFICACION ORDER BY NUM_PAQUETE")
    paquetes = [r[0] for r in cur.fetchall()]
    cur.close()
    if not paquetes:
        messagebox.showinfo("Exportar", "No hay paquetes para exportar.")
        win.destroy()
        return

    # 3) Selector de paquete
    ctk.CTkLabel(frm, text="Paquete:").grid(row=0, column=0, sticky="w", pady=5)
    pkg_var = tk.StringVar(value=str(paquetes[0]))
    ctk.CTkOptionMenu(frm, values=[str(p) for p in paquetes], variable=pkg_var, width=200)\
        .grid(row=0, column=1, pady=5)

    # 4) Selector de formato
    ctk.CTkLabel(frm, text="Formato:").grid(row=1, column=0, sticky="w", pady=5)
    fmt_var = tk.StringVar(value="CSV")
    ctk.CTkOptionMenu(frm, values=["CSV", "TXT"], variable=fmt_var, width=200)\
        .grid(row=1, column=1, pady=5)

    # 5) Botón Exportar
    def _export():
        pkg = int(pkg_var.get())
        fmt = fmt_var.get()
        ext = ".txt" if fmt == "TXT" else ".csv"
        sep = ";" if fmt == "TXT" else ","
        path = filedialog.asksaveasfilename(
            parent=win,
            defaultextension=ext,
            filetypes=[("CSV","*.csv"),("Texto","*.txt")])
        if not path:
            return

        # 6) Consulta: convertimos a entero y formateamos fechas sin hora
        cur2 = conn.cursor()
        cur2.execute("""
            SELECT
              a.RADICADO                                    AS RADICADO,
              CONVERT(varchar(10), t.FECHA_SERVICIO, 103)   AS [FECHAIN/FECHAPRESTACION],
              d.AUTORIZACION                                AS AUTORIZACION,
              d.CODIGO_SERVICIO                             AS [COD SERVICIO],
              CONVERT(int, d.CANTIDAD)                      AS CANTIDAD,
              CONVERT(int, d.VLR_UNITARIO)                  AS [VLR UNITARIO],
              t.DIAGNOSTICO                                 AS DIAGNOSTICO,
              NULL                                          AS AUTORIZACION1,
              NULL                                          AS [COD SERVICIO1],
              NULL                                          AS DIAGNOSTICO1,
              CONVERT(varchar(10), GETDATE(), 103)          AS CreatedOn,
              u2.NUM_DOC                                    AS Modifiedby,
              td.NAME                                       AS TipoDocumento,
              a.NUM_DOC                                     AS NumeroDocumento,
              CONVERT(int, d.COPAGO)                        AS CM_COPAGO
            FROM ASIGNACION_TIPIFICACION a
            JOIN TIPIFICACION t  ON t.ASIGNACION_ID = a.RADICADO
            JOIN TIPIFICACION_DETALLES d ON d.TIPIFICACION_ID = t.ID
            JOIN USERS u2       ON u2.ID = t.USER_ID
            JOIN TIPO_DOC td    ON td.ID = t.TIPO_DOC_ID
           WHERE a.NUM_PAQUETE = ?
           ORDER BY a.RADICADO, t.FECHA_SERVICIO
        """, (pkg,))
        rows = cur2.fetchall()
        headers = [col[0] for col in cur2.description]
        cur2.close()

        # 7) Escritura
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=sep)
            writer.writerow(headers)
            writer.writerows(rows)

        messagebox.showinfo("Exportar", f"Paquete {pkg} exportado en:\n{path}")
        win.destroy()

    ctk.CTkButton(frm, text="Exportar", command=_export, width=200)\
        .grid(row=2, column=0, columnspan=2, pady=(20,0))

    win.mainloop()


def open_dashboard(user_id, first_name, last_name, parent):
    conn = conectar_sql_server('DB_DATABASE')
    if conn is None:
        messagebox.showerror("Error", "No se pudo conectar a la base de datos.")
        return

    cursor = conn.cursor()
    cursor.execute(
        "SELECT R.ID, R.NAME FROM USER_ROLES UR "
        "JOIN ROL R ON UR.ROL_ID = R.ID WHERE UR.USER_ID = ?",
        user_id
    )
    roles = cursor.fetchall()
    cursor.close()

    role_map = {name: rid for rid, name in roles}
    role_names = list(role_map.keys())

    # Creamos un Toplevel hijo de 'parent'
    root = ctk.CTkToplevel(parent)
    # Cuando cerremos este dashboard, recuperamos el login
    def on_logout():
        # destruye el dashboard actual
        safe_destroy(root)
        # vuelve a lanzar el script de login en un proceso separado
        login_script = os.path.join(os.path.dirname(__file__), "login_app.py")
        subprocess.Popen(
            [sys.executable, login_script],
            cwd=os.path.dirname(__file__)
        )
    # Remplazamos el antiguo 'root = ctk.CTk()' por...
    root.title("Dashboard - Tipificador Médica")
    root.geometry("500x400")
    root.resizable(False, False)

    ctk.CTkLabel(
        root,
        text=f"Bienvenido, {first_name} {last_name}",
        font=ctk.CTkFont(size=20, weight="bold")
    ).pack(pady=(20, 10))

    role_var = tk.StringVar(value=role_names[0] if role_names else "")
    option = ctk.CTkOptionMenu(root, values=role_names, variable=role_var)
    option.pack(pady=(0, 10))

    btn_frame = ctk.CTkFrame(root, width=400, height=200)
    btn_frame.place(relx=0.5, rely=0.5, anchor="center")
    btn_frame.pack_propagate(False)

    def start_tipificacion_and_close():
        safe_destroy(root)
        iniciar_tipificacion(None, conn,user_id)

    buttons_by_role = {
        1: [
            ("Cargar Paquete",     lambda: cargar_paquete(root, conn)),
            ("Crear Usuario",      lambda: crear_usuario(root, conn)),
            ("Ver Progreso",       lambda: ver_progreso(root, conn)),
            ("Activar/Desactivar Usuario", lambda: modificar_estado_usuario(root, conn)),
            ("Exportar Tipificación", lambda: exportar_paquete(root, conn)),
        ],
        2: [
            ("Iniciar Tipificación", start_tipificacion_and_close),
        ]
    }

    def show_role_buttons(selected):
        for w in btn_frame.winfo_children():
            w.destroy()
        rid = role_map[selected]
        for text, cmd in buttons_by_role.get(rid, []):
            ctk.CTkButton(btn_frame, text=text, command=cmd, width=200)\
                .pack(pady=5, anchor="center")

    option.configure(command=show_role_buttons)
    if role_names:
        show_role_buttons(role_var.get())

    def on_logout():
        # destruye el dashboard actual
        safe_destroy(root)
        # vuelve a lanzar el script de login en un proceso separado
        login_script = os.path.join(os.path.dirname(__file__), "login_app.py")
        subprocess.Popen(
            [sys.executable, login_script],
            cwd=os.path.dirname(__file__)
        )


    ctk.CTkButton(
        root,
        text="Logout",
        command=on_logout,
        width=120
    ).place(relx=0.5, rely=0.9, anchor="center")

if __name__ == "__main__":
    import sys
    import customtkinter as ctk

    # Asegúrate de que lleguen 4 argumentos
    if len(sys.argv) != 4:
        print("Uso: python dashboard.py <user_id> <first_name> <last_name>")
        sys.exit(1)

    _, uid, fn, ln = sys.argv

    # Crea la ventana raíz de Tkinter
    root = ctk.CTk()

    # Lanza tu dashboard pasándole root como parent
    open_dashboard(int(uid), fn, ln, parent=root)

    # Y arranca el mainloop
    root.mainloop()

