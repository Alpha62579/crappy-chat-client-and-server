import json
import os
import socket
import sys
import threading
import time

PORT = os.getenv("PORT", 62579)
SERVER = "0.0.0.0"
ADDR = (SERVER, PORT)

HEADER = 1024
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "//disconnect"
KICK_MESSAGE = "/kick"

chatrooms = {}
stay = True

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)


def handle_client(conn, addr):
    global stay
    global chatrooms
    while stay:
        try:
            raw_message = conn.recv(HEADER).decode(FORMAT)
        except:
            for i, room in enumerate(chatrooms):
                if conn in chatrooms[room]['connections']:
                    break
            trigger_message(f"{chatrooms[room.lower()]['connections'][conn]} has disconnected.", "SERVER",
                            chatrooms[room.lower()]['connections'])
            print(f"{chatrooms[room.lower()]['connections'][conn]}:{addr} has disconnected.")
            break
        if raw_message:
            raw_json = json.loads(raw_message)
            room = raw_json['room']
            if raw_json['type'] == 'packet.message':
                msg_length = raw_json['length']
                time.sleep(0.2)
                msg = conn.recv(msg_length).decode(FORMAT)
                if msg == DISCONNECT_MESSAGE:
                    name = chatrooms[raw_json['room']]['connections'][conn]
                    chatrooms[raw_json['room']]['connections'].pop(conn)
                    try:
                        trigger_message(f"{name} has disconnected.", "SERVER", chatrooms[room.lower()]['connections'])
                    except KeyError:
                        pass
                    print(f"{name}:{addr} has disconnected.")
                    if not chatrooms[raw_json['room']]['connections'].keys():
                        chatrooms.pop(raw_json['room'])
                    break
                elif msg.split(" ")[0] == KICK_MESSAGE:
                    if chatrooms[room.lower()]['connections'][conn] in chatrooms[raw_json['room']]['ops']:
                        try:
                            byebyeguy = msg.split(" ")[1]
                        except IndexError:
                            send("Enter the name of a person in this chatroom.", conn)
                            continue
                        con = None
                        for i, con in enumerate(chatrooms[room.lower()]['connections']):
                            if chatrooms[room.lower()]['connections'][con] == byebyeguy:
                                header = json.dumps({"type": "packet.kick"}).encode(FORMAT)
                                con.send(header)
                                con.close()
                                trigger_message(f"{byebyeguy} has been kicked from this chatroom!", "SERVER",
                                                chatrooms[room.lower()]['connections'])
                        if con:
                            chatrooms[raw_json['room']]['connections'].pop(con)
                        else:
                            send(f"No one by the name of {byebyeguy} is online in the chatroom.", conn)
                            continue
                    else:
                        send("Welp, you aren't an OP in the room.", conn)
                        continue
                print(f"[{chatrooms[room.lower()]['connections'][conn]}:{addr}:{raw_json['room'].lower()}] {msg}")
                trigger_message(msg, chatrooms[room.lower()]['connections'][conn],
                                chatrooms[room.lower()]['connections'])
            elif raw_json['type'] == 'packet.identify':
                if raw_json['room'].lower() not in chatrooms:
                    chatrooms[raw_json['room'].lower()] = {"connections": {conn: raw_json['name']},
                                                           "ops": [raw_json['name']], "password": raw_json[
                            'password'] if "password" in raw_json.keys() else None}
                    trigger_message(f"{chatrooms[raw_json['room'].lower()]['connections'][conn]} has connected.",
                                    "SERVER", chatrooms[room.lower()]['connections'])
                    send(f"Chatroom "
                         f"\"{raw_json['room'].lower()}\""
                         " has been created successfully." + f" Password: {raw_json['password']}" if raw_json[
                                                                                                         'password'] != "" else "",
                         conn)
                    print(f"{chatrooms[room.lower()]['connections'][conn]}:{addr} has connected")
                    print(f"Created chatroom {raw_json['room'].lower()}")
                else:
                    send(f"Chatroom \"{raw_json['room'].lower()}\" has been found. Attempting to connect to it...",
                         conn)
                    if chatrooms[raw_json['room'].lower()]['password'] == raw_json['password'] or \
                            chatrooms[raw_json['room'].lower()]['password'] == '':
                        for connection in chatrooms[room.lower()]['connections']:
                            if chatrooms[room.lower()]['connections'][connection] == raw_json['name']:
                                send("Your name is currently being used by someone else. Please use another name.",
                                     conn)
                                header = json.dumps({"type": "packet.disconnect"}).encode(FORMAT)
                                conn.send(header)
                        chatrooms[room.lower()]['connections'][conn] = raw_json['name']
                        trigger_message(f"{chatrooms[room.lower()]['connections'][conn]} has connected.", "SERVER",
                                        chatrooms[room.lower()]['connections'])
                        print(
                            f"{chatrooms[raw_json['room']]['connections'][conn]}:{addr}:{raw_json['room'].lower()} has connected.")
                    else:
                        send("Invalid password.", conn)
                        break

    conn.close()
    sys.exit(0)


def send(msg, conn):
    message = msg.encode(FORMAT)
    msg_length = len(message)
    send_length = json.dumps({"type": "packet.message", "length": msg_length, "name": "SERVER"}).encode(FORMAT)
    send_length += b' ' * (HEADER - len(send_length))
    conn.send(send_length)
    conn.send(message)


def trigger_message(message, sender, connections):
    for connection in connections:
        if connections[connection] != sender:
            message = str(message)
            if message.startswith("b'"):
                message = message[2:-1]
            message = message.encode(FORMAT)
            msg_length = json.dumps({"type": "packet.message", "length": len(message), "name": sender})
            send_length = msg_length.encode(FORMAT)
            send_length += b' ' * (HEADER - len(send_length))
            try:
                connection.send(send_length)
                connection.send(message)
            except:
                pass


def start():
    global stay
    server.listen()
    print(f"[LISTENING] Server is listening on {SERVER}:{PORT}")
    while stay:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 2}")
    sys.exit(0)


print("[SERVER] Starting server.")
t = threading.Thread(target=start, daemon=True)
t.start()
while True:
    try:
        input()
    except KeyboardInterrupt:
        print("[SERVER] Server stopping.")
        stay = False
        sys.exit(0)
