import socket, threading, json, os, base64

data_folder = "data"
os.makedirs(f"{data_folder}/chat_logs", exist_ok=True)
os.makedirs(f"{data_folder}/media", exist_ok=True)

users = {}  # socket -> user_info
usernames = {}  # name -> socket
groups = {}
friendships = {}  # username -> set of friends

# Load friendships from individual friend files
def load_friendships():
    global friendships
    friendships = {}
    # Scan for friend files
    for filename in os.listdir('.'):
        if filename.startswith('friends_') and filename.endswith('.json'):
            username = filename[8:-5]  # Remove 'friends_' prefix and '.json' suffix
            try:
                with open(filename, 'r') as f:
                    friend_list = json.load(f)
                    friendships[username] = set(friend_list)
            except Exception:
                friendships[username] = set()

def are_friends(user1, user2):
    """Check if two users are friends"""
    return (user1 in friendships and user2 in friendships[user1]) and \
           (user2 in friendships and user1 in friendships[user2])

# Load friendships at startup
load_friendships()

# Load or initialize groups
if os.path.exists(f"{data_folder}/groups.json"):
    with open(f"{data_folder}/groups.json") as f:
        groups = json.load(f)

user_db_file = f"{data_folder}/users.json"
if os.path.exists(user_db_file):
    with open(user_db_file) as f:
        user_db = json.load(f)
else:
    user_db = {}

offline_msg_file = f"{data_folder}/offline_messages.json"
if os.path.exists(offline_msg_file):
    with open(offline_msg_file) as f:
        offline_messages = json.load(f)
else:
    offline_messages = {}

server = socket.socket()
server.bind(("0.0.0.0", 9999))
server.listen()
print("[SERVER STARTED]")

def broadcast_to_group(group, sender, message):
    for member in groups[group]['members']:
        if member != sender and member in usernames:
            usernames[member].send(json.dumps(message).encode())

def recv_full(conn, length):
    data = b''
    while len(data) < length:
        more = conn.recv(length - len(data))
        if not more:
            raise ConnectionError('Socket closed')
        data += more
    return data

def recv_json(conn):
    # First, read 8 bytes for length
    length_bytes = b''
    while len(length_bytes) < 8:
        more = conn.recv(8 - len(length_bytes))
        if not more:
            raise ConnectionError('Socket closed')
        length_bytes += more
    length = int(length_bytes.decode())
    data = recv_full(conn, length)
    return json.loads(data.decode())

def send_json(conn, obj):
    data = json.dumps(obj).encode()
    length = f'{len(data):08d}'.encode()
    conn.sendall(length + data)

def handle_client(conn):
    while True:
        try:
            message = recv_json(conn)
            msg_type = message.get("type")

            # Handle group invitation: deliver to online or store for offline
            if msg_type == "GROUP_INVITE":
                to_user = message.get("to")
                group_name = message.get("group_name")
                from_user = message.get("from")
                # Prepare invitation message
                invite_msg = {
                    "type": "GROUP_INVITE",
                    "group_name": group_name,
                    "from": from_user
                }
                if to_user in usernames:
                    send_json(usernames[to_user], invite_msg)
                else:
                    # Store as offline message (as a special invite)
                    offline_msg = {
                        "from": from_user,
                        "msg": f"invited you to join group {group_name}",
                        "is_file": False,
                        "group_invite": True,
                        "group_name": group_name
                    }
                    if to_user not in offline_messages:
                        offline_messages[to_user] = []
                    offline_messages[to_user].append(offline_msg)
                    with open(offline_msg_file, "w") as f:
                        json.dump(offline_messages, f)

            if msg_type == "REGISTER":
                info = message["data"]
                name = info['name']
                password = info['password']
                # Only allow new users
                if name in user_db:
                    send_json(conn, {"type": "REGISTER_FAIL", "reason": "User already exists"})
                    continue
                user_db[name] = info
                with open(user_db_file, "w") as f:
                    json.dump(user_db, f)
                users[conn] = info
                usernames[name] = conn
                send_json(conn, {"type": "REGISTER_SUCCESS"})

            elif msg_type == "LOGIN":
                name = message["name"]
                password = message["password"]
                if name not in user_db:
                    send_json(conn, {"type": "LOGIN_FAIL", "reason": "User does not exist"})
                    continue
                if user_db[name]['password'] != password:
                    send_json(conn, {"type": "LOGIN_FAIL", "reason": "Wrong password"})
                    continue
                users[conn] = user_db[name]
                usernames[name] = conn
                send_json(conn, {"type": "LOGIN_SUCCESS"})
                # Deliver offline messages in a single batch, but do NOT send any as direct chat messages
                if name in offline_messages and offline_messages[name]:
                    # Only send as OFFLINE_MESSAGES, never as PRIVATE_MESSAGE or MEDIA
                    offline_batch = []
                    for msg in offline_messages[name]:
                        # If old format, convert to new format
                        if 'is_file' not in msg:
                            # Guess type by keys
                            if 'filename' in msg and 'data' in msg:
                                msg = {
                                    'from': msg.get('from'),
                                    'is_file': True,
                                    'filename': msg.get('filename'),
                                    'data': msg.get('data')
                                }
                            else:
                                msg = {
                                    'from': msg.get('from'),
                                    'msg': msg.get('msg'),
                                    'is_file': False
                                }
                        offline_batch.append(msg)
                    if offline_batch:  # Only send if there are messages
                        send_json(conn, {
                            "type": "OFFLINE_MESSAGES",
                            "messages": offline_batch
                        })
                        offline_messages[name] = []
                        with open(offline_msg_file, "w") as f:
                            json.dump(offline_messages, f)


            elif msg_type == "LIST":
                user_list = [info["name"] for c, info in users.items() if c != conn]
                send_json(conn, {"type": "LIST_RESPONSE", "users": user_list})

            elif msg_type == "STATUS":
                # STATUS request: expects {type: 'STATUS', 'friends': [list of friends]}
                friends = message.get('friends', [])
                # For robustness, allow both 'friends' and 'data' keys
                if not friends and 'data' in message:
                    friends = message['data']
                # Build status dict: {friend: True/False}
                status = {friend: (friend in usernames) for friend in friends}
                send_json(conn, {'type': 'STATUS_RESPONSE', 'status': status})

            elif msg_type == "REQUEST_CHAT":
                to_user = message["to"]
                if to_user in usernames:
                    send_json(usernames[to_user], {"type": "INCOMING_REQUEST", "from": users[conn]})

            elif msg_type == "FRIEND_REQUEST":
                from_user = message.get("from")
                to_user = message.get("to")
                
                # Get sender's details from user database
                sender_info = user_db.get(from_user, {})
                
                if to_user in usernames:
                    # Send friend request to the target user with sender details
                    send_json(usernames[to_user], {
                        "type": "FRIEND_REQUEST", 
                        "from": from_user,
                        "sender_info": {
                            "name": sender_info.get("name", from_user),
                            "dept": sender_info.get("dept", "Unknown"),
                            "session": sender_info.get("session", "Unknown")
                        }
                    })
                    print(f"[FRIEND REQUEST] {from_user} -> {to_user}")
                else:
                    # Store as offline message if user is not online
                    if to_user not in offline_messages:
                        offline_messages[to_user] = []
                    offline_messages[to_user].append({
                        "type": "FRIEND_REQUEST",
                        "from": from_user,
                        "msg": "sent you a friend request",
                        "is_friend_request": True,
                        "sender_info": {
                            "name": sender_info.get("name", from_user),
                            "dept": sender_info.get("dept", "Unknown"),
                            "session": sender_info.get("session", "Unknown")
                        }
                    })
                    with open(offline_msg_file, "w") as f:
                        json.dump(offline_messages, f)
                    print(f"[FRIEND REQUEST OFFLINE] {from_user} -> {to_user}")

            elif msg_type == "FRIEND_REQUEST_RESPONSE":
                from_user = message.get("from")
                to_user = message.get("to")
                accepted = message.get("accepted", False)
                if to_user in usernames:
                    if accepted:
                        send_json(usernames[to_user], {
                            "type": "FRIEND_REQUEST_ACCEPTED",
                            "from": from_user
                        })
                        # Reload friendships to update server's friendship tracking
                        load_friendships()
                        print(f"[FRIEND REQUEST ACCEPTED] {from_user} accepted by {to_user}")
                    else:
                        send_json(usernames[to_user], {
                            "type": "FRIEND_REQUEST_DECLINED", 
                            "from": from_user
                        })
                        print(f"[FRIEND REQUEST DECLINED] {from_user} declined by {to_user}")


            elif msg_type == "PRIVATE_MESSAGE":
                to = message["to"]
                from_user = message.get("from")
                
                # Check if users are friends before allowing message
                if not are_friends(from_user, to):
                    # Send error message back to sender
                    send_json(conn, {
                        "type": "MESSAGE_ERROR",
                        "reason": f"You need to be friends with {to} to send messages."
                    })
                    print(f"[MESSAGE BLOCKED] {from_user} -> {to} (not friends)")
                    continue
                    
                if to in usernames:
                    send_json(usernames[to], message)
                    print(f"[PRIVATE MESSAGE] {from_user} -> {to}")
                else:
                    # Store offline in unified format
                    offline_msg = {
                        "from": message.get("from"),
                        "msg": message.get("msg"),
                        "is_file": False
                    }
                    if to not in offline_messages:
                        offline_messages[to] = []
                    offline_messages[to].append(offline_msg)
                    with open(offline_msg_file, "w") as f:
                        json.dump(offline_messages, f)
                    print(f"[PRIVATE MESSAGE OFFLINE] {from_user} -> {to}")


            elif msg_type == "MEDIA":
                to = message["to"]
                from_user = message.get("from")
                
                # Check if users are friends before allowing file transfer
                if not are_friends(from_user, to):
                    # Send error message back to sender
                    send_json(conn, {
                        "type": "MESSAGE_ERROR",
                        "reason": f"You need to be friends with {to} to send files."
                    })
                    print(f"[FILE BLOCKED] {from_user} -> {to} (not friends)")
                    continue
                    
                if to in usernames:
                    send_json(usernames[to], message)
                    print(f"[FILE TRANSFER] {from_user} -> {to}: {message.get('filename')}")
                else:
                    # Store offline in unified format for files
                    offline_msg = {
                        "from": message.get("from"),
                        "is_file": True,
                        "filename": message.get("filename"),
                        "data": message.get("data")
                    }
                    if to not in offline_messages:
                        offline_messages[to] = []
                    offline_messages[to].append(offline_msg)
                    with open(offline_msg_file, "w") as f:
                        json.dump(offline_messages, f)
                    print(f"[FILE TRANSFER OFFLINE] {from_user} -> {to}: {message.get('filename')}")

            elif msg_type == "CREATE_GROUP":
                gname = message["group_name"]
                creator = message["creator"]
                groups[gname] = {"admin": creator, "members": [creator]}
                with open(f"{data_folder}/groups.json", "w") as f:
                    json.dump(groups, f)

            elif msg_type == "JOIN_GROUP":
                gname = message["group_name"]
                user = message["user"]
                if gname in groups and user not in groups[gname]['members']:
                    groups[gname]['members'].append(user)
                    with open(f"{data_folder}/groups.json", "w") as f:
                        json.dump(groups, f)

            elif msg_type == "GROUP_MESSAGE":
                gname = message["group_name"]
                sender = message["from"]
                broadcast_to_group(gname, sender, message)

            elif msg_type == "GROUP_MEDIA":
                gname = message["group_name"]
                sender = message["from"]
                if gname in groups:
                    for member in groups[gname]['members']:
                        if member != sender and member in usernames:
                            send_json(usernames[member], message)
        except Exception as e:
            print("[ERROR]", e)
            break

    if conn in users:
        name = users[conn]["name"]
        usernames.pop(name, None)
        users.pop(conn)
    conn.close()

while True:
    conn, addr = server.accept()
    threading.Thread(target=handle_client, args=(conn,), daemon=True).start()
