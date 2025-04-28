from PyQt5.QtGui import QIntValidator
from PyQt5 import QtCore, QtGui, QtWidgets
import subprocess, sys, os
from db_connection import conectar_sql_server
from auth import authenticate_user_by_doc

# Conexión a BD
conn = conectar_sql_server('DB_DATABASE')
if conn is None:
    raise RuntimeError("No se pudo conectar a la base de datos.")

def authenticate_user_by_doc(num_doc: str, password: str):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ID, FIRST_NAME, LAST_NAME, PASSWORD, STATUS_ID FROM USERS WHERE NUM_DOC = ?",
        (num_doc,),
    )
    row = cursor.fetchone()
    cursor.close()
    if not row:
        return None
    user_id, first_name, last_name, stored_password, status_id = row
    return (user_id, first_name, last_name, status_id) if stored_password == password else None

class LoginWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login - Tipificador Médica")
        self.resize(700, 800)
        self.center_on_screen()

        # Cargar imagen de fondo
        self.bg_path = os.path.join(os.path.dirname(__file__), "Fondo.png")
        self.bg_pixmap = QtGui.QPixmap(self.bg_path)

        # Layout principal
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Contenedor central
        central_layout = QtWidgets.QHBoxLayout()
        central_layout.addStretch()

        self.panel = QtWidgets.QFrame()
        self.panel.setFixedSize(400, 500)
        self.panel.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 150);
                border-radius: 20px;
            }
        """)

        vbox = QtWidgets.QVBoxLayout(self.panel)
        vbox.setContentsMargins(40, 30, 40, 30)
        vbox.setSpacing(20)
        vbox.setAlignment(QtCore.Qt.AlignCenter)

        # Título
        lbl_title = QtWidgets.QLabel("Iniciar sesión", alignment=QtCore.Qt.AlignCenter)
        lbl_title.setStyleSheet("""
            color: white;
            font-size: 24px;
            font-weight: bold;
            background: transparent;
        """)
        vbox.addWidget(lbl_title)

        # Documento
        self.edit_doc = QtWidgets.QLineEdit()
        self.edit_doc.setPlaceholderText("Documento")
        self.edit_doc.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255,255,255,40);
                color: white;
                border-radius: 15px;
                padding: 10px;
                font-size: 16px;
            }
        """)
        vbox.addWidget(self.edit_doc)

        # Contraseña
        self.edit_pwd = QtWidgets.QLineEdit()
        self.edit_pwd.setPlaceholderText("Contraseña")
        self.edit_pwd.setEchoMode(QtWidgets.QLineEdit.Password)
        self.edit_pwd.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255,255,255,40);
                color: white;
                border-radius: 15px;
                padding: 10px;
                font-size: 16px;
            }
        """)
        vbox.addWidget(self.edit_pwd)

        # Botón login
        btn = QtWidgets.QPushButton("Iniciar sesión")
        btn.setFixedHeight(45)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 20px;
                font-size: 18px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #339CFF;
            }
        """)
        btn.clicked.connect(self.on_login)
        vbox.addWidget(btn)

        central_layout.addWidget(self.panel)
        central_layout.addStretch()

        main_layout.addStretch()
        main_layout.addLayout(central_layout)
        main_layout.addStretch()

    def paintEvent(self, event):
        """ Pintar la imagen de fondo cada vez que se refresca """
        painter = QtGui.QPainter(self)
        if not self.bg_pixmap.isNull():
            scaled_pixmap = self.bg_pixmap.scaled(self.size(), QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
            painter.drawPixmap(self.rect(), scaled_pixmap)

    def center_on_screen(self):
        screen = QtWidgets.QApplication.primaryScreen().availableGeometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)

    def on_login(self):
        from dashboard import open_dashboard  # import tardío, evita el bucle
        open_dashboard(user_id, first_name, last_name, parent=self)
        num_doc = self.edit_doc.text().strip()
        pwd     = self.edit_pwd.text().strip()

        if not num_doc or not pwd:
            QtWidgets.QMessageBox.warning(self, "Datos faltantes", "Debe ingresar documento y contraseña.")
            return

        auth = authenticate_user_by_doc(num_doc, pwd)
        if auth is None:
            QtWidgets.QMessageBox.critical(self, "Error", "Documento o contraseña incorrectos.")
            return

        user_id, first_name, last_name, status_id = auth
        if status_id != 5:
            QtWidgets.QMessageBox.warning(self, "Usuario inactivo", "Tu cuenta no está activa. Contacta al administrador.")
            return

        # Ruta absoluta a dashboard.py
        script = os.path.join(os.path.dirname(__file__), "dashboard.py")

        # Lanza dashboard.py en un proceso separado
        subprocess.Popen([
            sys.executable,
            script,
            str(user_id),
            first_name,
            last_name
        ], cwd=os.path.dirname(__file__))

        # Cierra la ventana de login
        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = LoginWindow()
    w.show()
    sys.exit(app.exec_())