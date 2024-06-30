import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QTextEdit, QLineEdit, QPushButton, QLabel, QInputDialog, 
    QMessageBox, QComboBox, QDialog
)
from PyQt5.QtCore import pyqtSignal, QThread
import socket
import json

class ClientThread(QThread):
    message_received = pyqtSignal(str)
    users_updated = pyqtSignal(list)
    username_taken = pyqtSignal()

    def __init__(self, host, port, username, language):
        super().__init__()
        self.host = host
        self.port = port
        self.username = username
        self.language = language
        self.running = True
        self.dm_sessions = {}  # Dictionary to store DM sessions and chat history

    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            
            # Send username and language to server
            user_info = json.dumps({'username': self.username, 'language': self.language})
            self.sock.sendall(user_info.encode('utf-8'))

            # Receive initial user list from server
            user_list_data = self.sock.recv(1024).decode('utf-8')
            if user_list_data.startswith("users:"):
                users = user_list_data.split(':')[1].split(',')
                self.users_updated.emit(users)
            else:
                print("Error receiving user list from server")

            while self.running:
                message = self.sock.recv(1024).decode('utf-8')
                if message:
                    if message.startswith("users:"):
                        users = message.split(':')[1].split(',')
                        self.users_updated.emit(users)
                    elif message.startswith("dm"):
                        parts = message.split(' ', 3)
                        if len(parts) >= 4:
                            sender = parts[1]
                            recipient = parts[2]
                            message_text = parts[3]
                            
                            if recipient == self.username:
                                if sender in self.dm_sessions:
                                    self.dm_sessions[sender].append(f"{sender} >> {message_text}")
                                else:
                                    self.dm_sessions[sender] = [f"{sender} >> {message_text}"]
                            elif sender == self.username:
                                if recipient in self.dm_sessions:
                                    self.dm_sessions[recipient].append(f"You >> {message_text}")
                                else:
                                    self.dm_sessions[recipient] = [f"You >> {message_text}"]

                            self.message_received.emit(message)
                    else:
                        self.message_received.emit(message)

        except Exception as e:
            print(f"Error in client thread: {e}")
            self.running = False
            if "Username already taken" in str(e):
                self.username_taken.emit()

    def send_message(self, recipient, message):
        try:
            self.sock.sendall(f"dm {recipient} {message}".encode('utf-8'))
            if recipient in self.dm_sessions:
                self.dm_sessions[recipient].append(f"You >> {message}")
            else:
                self.dm_sessions[recipient] = [f"You >> {message}"]
        except Exception as e:
            print(f"Error sending message: {e}")

    def stop(self):
        self.running = False
        if hasattr(self, 'sock'):
            self.sock.close()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat Client")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QHBoxLayout(self.central_widget)

        self.user_list = QListWidget()
        self.user_list.itemClicked.connect(self.select_recipient)
        self.layout.addWidget(self.user_list)

        self.chat_box = QTextEdit()
        self.chat_box.setReadOnly(True)
        self.layout.addWidget(self.chat_box)

        self.input_layout = QVBoxLayout()
        self.layout.addLayout(self.input_layout)

        self.message_entry = QLineEdit()
        self.input_layout.addWidget(self.message_entry)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        self.input_layout.addWidget(self.send_button)

        self.status_label = QLabel("Status: Not connected")
        self.input_layout.addWidget(self.status_label)

        self.client_thread = None
        self.username = None
        self.language = None
        self.recipient = None

        self.get_user_info()

    def get_user_info(self):
        # Create a dialog for entering username and selecting language
        dialog = QDialog(self)
        dialog.setWindowTitle("User Information")

        dialog_layout = QVBoxLayout(dialog)

        # Username input
        username_input = QLineEdit(dialog)
        username_input.setPlaceholderText("Enter your unique username")
        dialog_layout.addWidget(username_input)

        # Language selection
        languages = [
            "Assamese", "Bengali", "Bodo", "Dogri", "English", "Konkani", "Gujarati", "Hindi", 
            "Kannada", "Kashmiri (Arabic)", "Kashmiri (Devanagari)", "Maithili", "Malayalam", 
            "Marathi", "Manipuri (Bengali)", "Manipuri (Meitei)", "Nepali", "Odia", "Punjabi", 
            "Sanskrit", "Santali", "Sindhi (Arabic)", "Sindhi (Devanagari)", "Tamil", "Telugu", "Urdu"
        ]
        language_codes = [
            "asm_Beng", "ben_Beng", "brx_Deva", "doi_Deva", "eng_Latn", "gom_Deva", "guj_Gujr", "hin_Deva",
            "kan_Knda", "kas_Arab", "kas_Deva", "mai_Deva", "mal_Mlym", "mar_Deva", "mni_Beng", "mni_Mtei",
            "npi_Deva", "ory_Orya", "pan_Guru", "san_Deva", "sat_Olck", "snd_Arab", "snd_Deva", "tam_Taml",
            "tel_Telu", "urd_Arab"
        ]

        language_combo = QComboBox(dialog)
        language_combo.addItems(languages)
        language_combo.setCurrentIndex(languages.index("English"))  # Set default to English
        dialog_layout.addWidget(language_combo)

        # OK and Cancel buttons
        button_layout = QHBoxLayout()

        ok_button = QPushButton("OK", dialog)
        ok_button.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_button)

        cancel_button = QPushButton("Cancel", dialog)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)

        dialog_layout.addLayout(button_layout)

        if dialog.exec() == QDialog.Accepted:
            self.username = username_input.text().strip()
            self.language = language_codes[language_combo.currentIndex()]
            if self.username:
                try:
                    self.client_thread = ClientThread('localhost', 1060, self.username, self.language)
                    self.client_thread.message_received.connect(self.display_message)
                    self.client_thread.users_updated.connect(self.update_user_list)
                    self.client_thread.username_taken.connect(self.handle_username_taken)
                    self.client_thread.start()
                    self.status_label.setText(f"Status: Connected as {self.username} with language {self.language}")
                except Exception as e:
                    print(f"Error connecting to server: {e}")
                    QMessageBox.critical(self, "Error", "Could not connect to server.")
                    self.status_label.setText("Status: Not connected")
                    self.username = None
                    self.language = None
                    self.get_user_info()
            else:
                QMessageBox.warning(self, "Warning", "Username cannot be empty.")
                self.get_user_info()
        else:
            sys.exit()

    def select_recipient(self, item):
        self.recipient = item.text()
        self.chat_box.clear()
        if self.recipient in self.client_thread.dm_sessions:
            for message in self.client_thread.dm_sessions[self.recipient]:
                self.display_message(message)

    def send_message(self):
        if self.client_thread and self.message_entry.text() and self.recipient:
            message = self.message_entry.text()
            self.client_thread.send_message(self.recipient, message)
            self.display_message(f"You >> {message}")
            self.message_entry.clear()

    def display_message(self, message):
        self.chat_box.append(message)

    def update_user_list(self, users):
        self.user_list.clear()
        for user in users:
            if user != self.username:  # Exclude self from user list
                self.user_list.addItem(user)

    def handle_username_taken(self):
        QMessageBox.warning(self, "Username taken", "Username already taken. Please choose another.")
        self.username = None
        self.get_user_info()

    def closeEvent(self, event):
        if self.client_thread:
            self.client_thread.stop()
            self.client_thread.wait()

        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
