import json
import socket
import threading
import sys
import os
from dotenv import load_dotenv
from getpass import getpass
import time

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

load_dotenv()

stop = True
HEADER = 1024
PORT = int(os.getenv("PORT", 62579))
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "//disconnect"
SERVER = os.getenv("HOST")
ADDR = (SERVER, PORT)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDR)

name = input("Enter a name: ")
chatroom = input("Enter a chatroom name: ")
password = getpass(
    prompt="Enter a password, this will be used for authentication (Leave this blank if you don't want a password or there isn't one).")
packet_data = json.dumps({"type": "packet.identify", "name": name, "room": chatroom, "password": password})
client.send(packet_data.encode(FORMAT))


def send(msg):
    message = msg.encode(FORMAT)
    msg_length = len(message)
    send_length = json.dumps({"type": "packet.message", "length": msg_length, "room": chatroom}).encode(FORMAT)
    send_length += b' ' * (HEADER - len(send_length))
    try:
        client.send(send_length)
        client.send(message)
    except:
        print("An error occurred while sending. The server may have closed.")
        time.sleep(1)
        sys.exit(1)


def on_message(conn):
    global stop
    while stop:
        try:
            msg_length = conn.recv(HEADER).decode(FORMAT)
        except ConnectionResetError:
            print("Server closed.")
            stop = False
            sys.exit(0)
        if msg_length:
            msg_length = json.loads(msg_length)
            if msg_length['type'] == 'packet.kick':
                print("You got kicked from this chatroom.")
                stop = False
                sys.exit(0)
            elif msg_length['type'] == 'packet.disconnect':
                send(DISCONNECT_MESSAGE)
                time.sleep(1)
                sys.exit(0)
            msg = conn.recv(msg_length['length']).decode(FORMAT)
            print(f"Message received from {msg_length['name']}: {str(msg)}")


def main():
    global stop
    session = PromptSession()
    while stop:
        try:
            with patch_stdout():
                text = session.prompt("> ")
                if text != '':
                    if text == '//disconnect':
                        raise KeyboardInterrupt
                    send(text)
        except KeyboardInterrupt:
            send(DISCONNECT_MESSAGE)
            time.sleep(1)
            sys.exit(0)


if __name__ == '__main__':
    threading.Thread(target=on_message, args=(client,), daemon=True).start()
    main()

