import socket
import threading
import json
from translator import Translator

class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.clients = {}        # Dictionary to store connected clients' sockets by username
        self.active_users = {}  # Dictionary to track active usernames and their languages
        self.server_socket = None
        self.is_running = False

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server listening on {self.host}:{self.port}")
        self.is_running = True

        while self.is_running:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"Accepted connection from {client_address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()
            except Exception as e:
                print(f"Error accepting connection: {e}")

    def stop(self):
        self.is_running = False
        self.server_socket.close()
        print("Server closed")

    def handle_client(self, client_socket):
        username = None
        try:
            # Receive user info (username and language) from client
            user_info_data = client_socket.recv(1024).decode('utf-8').strip()
            user_info = json.loads(user_info_data)
            username = user_info['username']
            language = user_info['language']
            if not username or not language:
                client_socket.close()
                return

            # Check if username is unique
            if username in self.active_users:
                client_socket.send("Username already taken".encode('utf-8'))
                client_socket.close()
                return

            # Register client
            self.clients[username] = client_socket
            self.active_users[username] = language
            self.broadcast_users()

            # Handle messages from client
            while True:
                message = client_socket.recv(1024).decode('utf-8')
                if not message:
                    break
                if message.startswith("dm "):
                    parts = message.split(' ', 2)
                    if len(parts) >= 3:
                        recipient = parts[1]
                        dm_message = parts[2]
                        if recipient in self.clients:
                            self.send_message(username, recipient, dm_message)
                        else:
                            # Notify sender that recipient is not online
                            client_socket.send(f"{recipient} is not online".encode('utf-8'))
                else:
                    self.broadcast_message(username, message)

        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            if username:
                self.unregister_client(username)
            client_socket.close()

    def send_message(self, sender, recipient, message):
        if recipient in self.clients:
            # Translate message to recipient's preferred language
            sender_lang = self.active_users[sender]
            recipient_lang = self.active_users[recipient]
            translator = Translator()
            translated_message = translator.translate(message,src_lang=sender_lang,tgt_lang=recipient_lang)
            self.clients[recipient].send(f"{sender} (DM) >> {translated_message}".encode('utf-8'))

   

    def broadcast_users(self):
        user_list = ",".join(self.active_users.keys())
        for client in self.clients.values():
            client.send(f"users:{user_list}".encode('utf-8'))

    def unregister_client(self, username):
        if username in self.clients:
            del self.clients[username]
        if username in self.active_users:
            del self.active_users[username]
            self.broadcast_users()

if __name__ == "__main__":
    server = Server('localhost', 1060)
    server.start()
