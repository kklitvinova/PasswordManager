import sys
import os
import secrets
import string

try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QDialog, QFormLayout, QTextEdit, QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from crypto_utils import (
    derive_key, encrypt_password, decrypt_password,
    encrypt_file, decrypt_file
)
from user_manager import register_user, verify_user, get_user_file
from password_store import (
    init_file, load_entries, add_entry,
    find_entries, update_entry, delete_entry
)

STYLE = """
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: 'Segoe UI';
    font-size: 13px;
}
QLineEdit, QTextEdit {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 6px;
    padding: 8px;
    color: #e0e0e0;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #e94560;
}
QPushButton {
    background-color: #0f3460;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 7px 14px;
    font-weight: bold;
}
QPushButton:hover { background-color: #e94560; }
QPushButton:pressed { background-color: #c73652; }
QPushButton#danger { background-color: #7b2d2d; }
QPushButton#danger:hover { background-color: #e94560; }
QPushButton#success { background-color: #1a6b3c; }
QPushButton#success:hover { background-color: #28a35c; }
QPushButton#small {
    background-color: #0f3460;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: bold;
    min-width: 42px;
    max-width: 42px;
    min-height: 24px;
    max-height: 24px;
}
QPushButton#small:hover { background-color: #e94560; }
QPushButton#smalldanger {
    background-color: #7b2d2d;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: bold;
    min-width: 36px;
    max-width: 36px;
    min-height: 24px;
    max-height: 24px;
}
QPushButton#smalldanger:hover { background-color: #e94560; }
QTableWidget {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 6px;
    gridline-color: #0f3460;
}
QTableWidget::item { padding: 4px; }
QTableWidget::item:selected { background-color: #e94560; }
QHeaderView::section {
    background-color: #0f3460;
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
}
QLabel#title {
    font-size: 22px;
    font-weight: bold;
    color: #e94560;
}
QLabel#subtitle { font-size: 13px; color: #888; }
QScrollBar:vertical {
    background: #16213e;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #0f3460;
    border-radius: 4px;
}
"""


def generate_password(length=16) -> str:
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(chars) for _ in range(length))


class AuthWindow(QWidget):
    def __init__(self, on_login):
        super().__init__()
        self.on_login = on_login
        self.setWindowTitle("Password Manager — Login")
        self.setFixedSize(400, 460)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(14)

        title = QLabel("🔐 Password Manager")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("Secure your passwords")
        sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        layout.addSpacing(16)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        layout.addWidget(self.username)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Master Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password)

        layout.addSpacing(6)

        btn_login = QPushButton("Login")
        btn_login.setObjectName("success")
        btn_login.clicked.connect(self.do_login)
        layout.addWidget(btn_login)

        btn_register = QPushButton("Register")
        btn_register.clicked.connect(self.do_register)
        layout.addWidget(btn_register)

        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("color: #e94560;")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()

    def do_login(self):
        u = self.username.text().strip()
        p = self.password.text()
        if not u or not p:
            self.status.setText("Fill in all fields.")
            return
        if verify_user(u, p):
            self.on_login(u, p)
            self.close()
        else:
            self.status.setText("Invalid username or password.")

    def do_register(self):
        u = self.username.text().strip()
        p = self.password.text()
        if not u or not p:
            self.status.setText("Fill in all fields.")
            return
        if len(p) < 6:
            self.status.setText("Password must be at least 6 characters.")
            return
        if register_user(u, p):
            self.status.setStyleSheet("color: #28a35c;")
            self.status.setText("Registered successfully! You can now login.")
        else:
            self.status.setStyleSheet("color: #e94560;")
            self.status.setText("Username already exists.")


class EntryDialog(QDialog):
    def __init__(self, parent, aes_key, title="", url="",
                 notes="", edit_mode=False):
        super().__init__(parent)
        self.aes_key = aes_key
        self.edit_mode = edit_mode
        self.setWindowTitle("Edit Entry" if edit_mode else "Add New Entry")
        self.setFixedSize(420, 440)
        self.result_data = None
        self.init_ui(title, url, notes)

    def init_ui(self, title, url, notes):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(10)

        self.f_title = QLineEdit(title)
        self.f_title.setPlaceholderText("e.g. Gmail")
        if self.edit_mode:
            self.f_title.setReadOnly(True)

        self.f_password = QLineEdit()
        self.f_password.setPlaceholderText("Password")
        self.f_password.setEchoMode(QLineEdit.EchoMode.Password)

        self.f_url = QLineEdit(url)
        self.f_url.setPlaceholderText("https://...")

        self.f_notes = QTextEdit(notes)
        self.f_notes.setPlaceholderText("Optional notes...")
        self.f_notes.setMaximumHeight(70)

        form.addRow("Title:", self.f_title)
        form.addRow("Password:", self.f_password)
        form.addRow("URL:", self.f_url)
        form.addRow("Notes:", self.f_notes)
        layout.addLayout(form)

        btn_gen = QPushButton("Generate Strong Password")
        btn_gen.clicked.connect(self.generate)
        layout.addWidget(btn_gen)

        self.btn_show = QPushButton("Show Password")
        self.btn_show.clicked.connect(self.toggle_show)
        layout.addWidget(self.btn_show)

        btn_save = QPushButton("Save Entry")
        btn_save.setObjectName("success")
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)

        self.status = QLabel("")
        self.status.setStyleSheet("color: #e94560;")
        layout.addWidget(self.status)

    def generate(self):
        pwd = generate_password()
        self.f_password.setText(pwd)
        self.f_password.setEchoMode(QLineEdit.EchoMode.Normal)
        self.btn_show.setText("Hide Password")

    def toggle_show(self):
        if self.f_password.echoMode() == QLineEdit.EchoMode.Password:
            self.f_password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_show.setText("Hide Password")
        else:
            self.f_password.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_show.setText("Show Password")

    def save(self):
        t = self.f_title.text().strip()
        p = self.f_password.text()
        u = self.f_url.text().strip()
        n = self.f_notes.toPlainText().strip()
        if not t:
            self.status.setText("Title is required.")
            return
        if not p:
            self.status.setText("Password is required.")
            return
        enc = encrypt_password(p, self.aes_key)
        self.result_data = (t, enc, u, n)
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self, username: str, master_password: str):
        super().__init__()
        self.username = username
        self.master_password = master_password
        self.salt = username.encode().ljust(16, b'0')[:16]
        self.aes_key = derive_key(master_password, self.salt)
        self.csv_file = get_user_file(username)
        self._prepare_file()
        self.setWindowTitle(f"Password Manager — {username}")
        self.setMinimumSize(860, 580)
        self.setStyleSheet(STYLE)
        self.init_ui()
        self.refresh_table()

    def _prepare_file(self):
        enc_path = self.csv_file + '.enc'
        if os.path.exists(enc_path):
            decrypt_file(enc_path, self.aes_key)
        init_file(self.csv_file)

    def closeEvent(self, event):
        if os.path.exists(self.csv_file):
            encrypt_file(self.csv_file, self.aes_key)
        event.accept()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(16, 16, 16, 16)
        main.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("🔐 Password Manager")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        user_lbl = QLabel(f"👤 {self.username}")
        user_lbl.setStyleSheet("color: #888; font-size: 12px;")
        header.addWidget(user_lbl)
        btn_logout = QPushButton("Logout")
        btn_logout.setObjectName("danger")
        btn_logout.clicked.connect(self.logout)
        header.addWidget(btn_logout)
        main.addLayout(header)

        # Search + Add
        row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by title...")
        self.search_input.textChanged.connect(self.refresh_table)
        row.addWidget(self.search_input)
        btn_add = QPushButton("+ Add Entry")
        btn_add.setObjectName("success")
        btn_add.clicked.connect(self.add_entry)
        row.addWidget(btn_add)
        main.addLayout(row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Title", "URL", "Notes", "Password", "Actions"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 185)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        main.addWidget(self.table)

        # Status
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #28a35c; font-size: 12px;")
        main.addWidget(self.status_lbl)

    def refresh_table(self):
        query = self.search_input.text().strip()
        entries = find_entries(self.csv_file, query) if query \
            else load_entries(self.csv_file)

        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            self.table.setItem(row, 0, QTableWidgetItem(entry['title']))
            self.table.setItem(row, 1, QTableWidgetItem(entry['url']))
            self.table.setItem(row, 2, QTableWidgetItem(entry['notes']))
            self.table.setItem(row, 3, QTableWidgetItem("••••••••"))

            # Action buttons
            cell = QWidget()
            cell.setStyleSheet("background: transparent;")
            bl = QHBoxLayout(cell)
            bl.setContentsMargins(3, 2, 3, 2)
            bl.setSpacing(3)

            btn_show = QPushButton("Show")
            btn_show.setObjectName("small")
            btn_show.clicked.connect(
                lambda _, e=entry: self.show_password(e))

            btn_copy = QPushButton("Copy")
            btn_copy.setObjectName("small")
            btn_copy.clicked.connect(
                lambda _, e=entry: self.copy_password(e))

            btn_edit = QPushButton("Edit")
            btn_edit.setObjectName("small")
            btn_edit.clicked.connect(
                lambda _, e=entry: self.edit_entry(e))

            btn_del = QPushButton("Del")
            btn_del.setObjectName("smalldanger")
            btn_del.clicked.connect(
                lambda _, e=entry: self.delete_entry(e))

            bl.addWidget(btn_show)
            bl.addWidget(btn_copy)
            bl.addWidget(btn_edit)
            bl.addWidget(btn_del)

            self.table.setCellWidget(row, 4, cell)
            self.table.setRowHeight(row, 36)

    def show_password(self, entry):
        try:
            plain = decrypt_password(entry['encrypted_password'], self.aes_key)
        except Exception:
            plain = "[Decryption failed]"
        msg = QMessageBox(self)
        msg.setWindowTitle("Password")
        msg.setText(
            f"<b>Title:</b> {entry['title']}<br><br>"
            f"<b>Password:</b> <code style='font-size:14px'>{plain}</code><br><br>"
            f"<b>URL:</b> {entry['url']}")
        msg.exec()

    def copy_password(self, entry):
        if not HAS_CLIPBOARD:
            self.status_lbl.setText("pyperclip not installed.")
            return
        try:
            plain = decrypt_password(entry['encrypted_password'], self.aes_key)
            pyperclip.copy(plain)
            self.status_lbl.setText(
                f"✓ Password for '{entry['title']}' copied to clipboard.")
        except Exception:
            self.status_lbl.setText("Failed to copy password.")

    def add_entry(self):
        dlg = EntryDialog(self, self.aes_key)
        if dlg.exec() and dlg.result_data:
            t, enc, u, n = dlg.result_data
            add_entry(self.csv_file, t, enc, u, n)
            self.refresh_table()
            self.status_lbl.setText(f"✓ Entry '{t}' added.")

    def edit_entry(self, entry):
        dlg = EntryDialog(self, self.aes_key,
                          title=entry['title'],
                          url=entry['url'],
                          notes=entry['notes'],
                          edit_mode=True)
        if dlg.exec() and dlg.result_data:
            t, enc, u, n = dlg.result_data
            update_entry(self.csv_file, t, enc, u, n)
            self.refresh_table()
            self.status_lbl.setText(f"✓ Entry '{t}' updated.")

    def delete_entry(self, entry):
        reply = QMessageBox.question(
            self, "Delete",
            f"Delete entry '{entry['title']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_entry(self.csv_file, entry['title'])
            self.refresh_table()
            self.status_lbl.setText(f"✓ Entry '{entry['title']}' deleted.")

    def logout(self):
        if os.path.exists(self.csv_file):
            encrypt_file(self.csv_file, self.aes_key)
        self.close()
        self.auth = AuthWindow(on_login_callback)
        self.auth.show()


app_instance = None
main_win = None


def on_login_callback(username, master_password):
    global main_win
    main_win = MainWindow(username, master_password)
    main_win.show()


def main():
    global app_instance
    app_instance = QApplication(sys.argv)
    app_instance.setStyleSheet(STYLE)
    auth = AuthWindow(on_login_callback)
    auth.show()
    sys.exit(app_instance.exec())


if __name__ == '__main__':
    main()