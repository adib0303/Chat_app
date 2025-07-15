import socket, threading, json, os, base64, time

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
    print("[LOAD FRIENDSHIPS] Loading friendship data...")
    # Scan for friend files
    for filename in os.listdir('.'):
        if filename.startswith('friends_') and filename.endswith('.json'):
            username = filename[8:-5]  # Remove 'friends_' prefix and '.json' suffix
            try:
                with open(filename, 'r') as f:
                    friend_list = json.load(f)
                    friendships[username] = set(friend_list)
                    print(f"[LOAD FRIENDSHIPS] {username}: {friend_list}")
            except Exception as e:
                print(f"[LOAD FRIENDSHIPS ERROR] Failed to load {filename}: {e}")
                friendships[username] = set()
    
    print(f"[LOAD FRIENDSHIPS] Total loaded: {dict(friendships)}")

def are_friends(user1, user2):
    """Check if two users are friends"""
    user1_has_user2 = user1 in friendships and user2 in friendships[user1]
    user2_has_user1 = user2 in friendships and user1 in friendships[user2]
    
    result = user1_has_user2 and user2_has_user1
    print(f"[FRIENDSHIP CHECK] {user1} <-> {user2}: {result}")
    print(f"  {user1} has {user2}: {user1_has_user2}")
    print(f"  {user2} has {user1}: {user2_has_user1}")
    print(f"  Current friendships: {dict(friendships)}")
    
    return result

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
            try:
                send_json(usernames[member], message)
            except Exception as e:
                print(f"[ERROR] Failed to send group message to {member}: {e}")
                # Remove disconnected user
                if member in usernames:
                    del usernames[member]

def recv_full(conn, length):
    data = b''
    while len(data) < length:
        more = conn.recv(length - len(data))
        if not more:
            raise ConnectionError('Socket closed')
        data += more
    return data

def recv_json(conn):
    """
    Receive JSON data with improved error handling and protocol recovery
    """
    # First, read 8 bytes for length
    length_bytes = b''
    while len(length_bytes) < 8:
        try:
            more = conn.recv(8 - len(length_bytes))
            if not more:
                raise ConnectionError('Socket closed')
            length_bytes += more
        except socket.timeout:
            raise ConnectionError('Socket timeout while reading length')
        except socket.error as e:
            raise ConnectionError(f'Socket error while reading length: {e}')
    
    try:
        # Decode and convert to integer with error handling
        length_str = length_bytes.decode('utf-8')
        
        # Enhanced debugging - always show problematic data
        if not length_str.isdigit() or len(length_str) != 8:
            print(f"[SERVER PROTOCOL ERROR] Invalid length received:")
            print(f"  Raw bytes: {repr(length_bytes)}")
            print(f"  Decoded string: {repr(length_str)}")
            print(f"  Length: {len(length_str)}")
            print(f"  Is digit: {length_str.isdigit()}")
            raise ValueError(f"Invalid length format: {repr(length_str)} (expected 8 digits)")
        
        length = int(length_str)
        if length < 0 or length > 1000000:  # Reasonable size limit
            raise ValueError(f"Invalid message length: {length}")
            
    except (UnicodeDecodeError, ValueError) as e:
        raise ConnectionError(f'Invalid message length received: {repr(length_bytes)} - {e}')
    
    data = recv_full(conn, length)
    try:
        return json.loads(data.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"[SERVER JSON ERROR] Failed to parse JSON:")
        print(f"  Data length: {len(data)}")
        print(f"  First 100 bytes: {repr(data[:100])}")
        raise ConnectionError(f'Invalid JSON data received: {repr(data[:100])}... - {e}')

def send_json(conn, obj):
    """
    Send JSON data with better error handling
    """
    try:
        data = json.dumps(obj).encode('utf-8')
        length = f'{len(data):08d}'.encode('utf-8')
        
        # Validate that we're sending a proper length header
        if len(length) != 8:
            raise ValueError(f"Length header must be 8 bytes, got {len(length)}")
        
        # Send all data at once to avoid partial sends
        full_message = length + data
        conn.sendall(full_message)
        
    except socket.error as e:
        raise ConnectionError(f'Failed to send message: {e}')
    except Exception as e:
        raise ConnectionError(f'Error preparing message: {e}')

def handle_client(conn):
    while True:
        try:
            message = recv_json(conn)
            msg_type = message.get("type")

            # Handle PING keepalive message
            if msg_type == "PING":
                send_json(conn, {"type": "PONG"})
                continue

            # Handle group invitation: deliver to online or store for offline
            if msg_type == "GROUP_INVITE":
                to_user = message.get("to")
                group_name = message.get("group_name")
                from_user = message.get("from")
                
                # Get sender's details from user database
                sender_info = user_db.get(from_user, {})
                
                # Prepare invitation message with sender details
                invite_msg = {
                    "type": "GROUP_INVITE",
                    "group_name": group_name,
                    "from": from_user,
                    "sender_info": {
                        "name": sender_info.get("name", from_user),
                        "dept": sender_info.get("dept", "Unknown"),
                        "session": sender_info.get("session", "Unknown")
                    }
                }
                
                if to_user in usernames:
                    print(f"[GROUP INVITE DEBUG] Sending invite_msg to {to_user}: {invite_msg}")
                    send_json(usernames[to_user], invite_msg)
                    print(f"[GROUP INVITE] {from_user} invited {to_user} to {group_name}")
                else:
                    # Store as offline message with proper format
                    offline_msg = {
                        "type": "GROUP_INVITE",
                        "from": from_user,
                        "msg": f"invited you to join group '{group_name}'",
                        "is_group_invite": True,
                        "group_name": group_name,
                        "sender_info": {
                            "name": sender_info.get("name", from_user),
                            "dept": sender_info.get("dept", "Unknown"),
                            "session": sender_info.get("session", "Unknown")
                        }
                    }
                    if to_user not in offline_messages:
                        offline_messages[to_user] = []
                    offline_messages[to_user].append(offline_msg)
                    with open(offline_msg_file, "w") as f:
                        json.dump(offline_messages, f)
                    print(f"[GROUP INVITE OFFLINE] {from_user} invited {to_user} to {group_name}")

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
                
                # Find user's group memberships
                user_groups = []
                for group_name, group_data in groups.items():
                    if name in group_data.get('members', []):
                        user_groups.append(group_name)
                
                send_json(conn, {"type": "LOGIN_SUCCESS", "groups": user_groups})
                # Deliver offline messages in a single batch, but do NOT send any as direct chat messages
                if name in offline_messages and offline_messages[name]:
                    # Only send as OFFLINE_MESSAGES, never as PRIVATE_MESSAGE or MEDIA
                    offline_batch = []
                    for msg in offline_messages[name]:
                        # If old format, convert to new format while preserving timestamps
                        if 'is_file' not in msg and 'is_friend_request' not in msg and 'is_group_invite' not in msg:
                            # Guess type by keys
                            if 'filename' in msg and 'data' in msg:
                                msg = {
                                    'from': msg.get('from'),
                                    'is_file': True,
                                    'filename': msg.get('filename'),
                                    'data': msg.get('data'),
                                    'timestamp': msg.get('timestamp')  # Preserve timestamp if exists
                                }
                            else:
                                msg = {
                                    'from': msg.get('from'),
                                    'msg': msg.get('msg'),
                                    'is_file': False,
                                    'timestamp': msg.get('timestamp')  # Preserve timestamp if exists
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
                from_user = message.get("from")  # Person who accepted/declined
                to_user = message.get("to")      # Person who sent the request
                accepted = message.get("accepted", False)
                
                if accepted:
                    print(f"[FRIEND REQUEST ACCEPTED] {from_user} accepted {to_user}'s request")
                    
                    # Add each user to the other's friend list
                    # Load and update from_user's friend list
                    from_user_friends_file = f"friends_{from_user}.json"
                    try:
                        with open(from_user_friends_file, 'r') as f:
                            from_user_friends = json.load(f)
                    except:
                        from_user_friends = []
                    
                    if to_user not in from_user_friends:
                        from_user_friends.append(to_user)
                        with open(from_user_friends_file, 'w') as f:
                            json.dump(from_user_friends, f)
                        print(f"[FRIENDSHIP] Added {to_user} to {from_user}'s friend list")
                    
                    # Load and update to_user's friend list
                    to_user_friends_file = f"friends_{to_user}.json"
                    try:
                        with open(to_user_friends_file, 'r') as f:
                            to_user_friends = json.load(f)
                    except:
                        to_user_friends = []
                    
                    if from_user not in to_user_friends:
                        to_user_friends.append(from_user)
                        with open(to_user_friends_file, 'w') as f:
                            json.dump(to_user_friends, f)
                        print(f"[FRIENDSHIP] Added {from_user} to {to_user}'s friend list")
                    
                    # Reload friendships to update server's friendship tracking
                    load_friendships()
                    print(f"[FRIENDSHIP] Both users are now friends: {from_user} <-> {to_user}")
                    
                    # Notify the original requester
                    if to_user in usernames:
                        send_json(usernames[to_user], {
                            "type": "FRIEND_REQUEST_ACCEPTED",
                            "from": from_user
                        })
                else:
                    print(f"[FRIEND REQUEST DECLINED] {from_user} declined {to_user}'s request")
                    # Notify the original requester
                    if to_user in usernames:
                        send_json(usernames[to_user], {
                            "type": "FRIEND_REQUEST_DECLINED", 
                            "from": from_user
                        })

            elif msg_type == "GROUP_INVITE_RESPONSE":
                from_user = message.get("from")  # Person who accepted/declined
                group_name = message.get("group_name")
                inviter = message.get("inviter")  # Person who sent the invitation
                accepted = message.get("accepted", False)
                
                if accepted:
                    print(f"[GROUP INVITE ACCEPTED] {from_user} accepted invitation to {group_name}")
                    
                    # Add user to the group
                    if group_name in groups:
                        if from_user not in groups[group_name]['members']:
                            groups[group_name]['members'].append(from_user)
                            with open(f"{data_folder}/groups.json", "w") as f:
                                json.dump(groups, f)
                            print(f"[GROUP] Added {from_user} to group {group_name}")
                    
                    # Notify the inviter that invitation was accepted
                    if inviter in usernames:
                        send_json(usernames[inviter], {
                            "type": "GROUP_INVITE_ACCEPTED",
                            "from": from_user,
                            "group_name": group_name
                        })
                    
                    # Send confirmation to the person who accepted
                    send_json(conn, {
                        "type": "GROUP_JOIN_SUCCESS",
                        "group_name": group_name
                    })
                else:
                    print(f"[GROUP INVITE DECLINED] {from_user} declined invitation to {group_name}")
                    # Notify the inviter that invitation was declined
                    if inviter in usernames:
                        send_json(usernames[inviter], {
                            "type": "GROUP_INVITE_DECLINED",
                            "from": from_user,
                            "group_name": group_name
                        })

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
                    # Store offline in unified format with original timestamp
                    offline_msg = {
                        "from": message.get("from"),
                        "msg": message.get("msg"),
                        "is_file": False,
                        "timestamp": message.get("timestamp")  # Preserve original timestamp
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
                    # Store offline in unified format for files with original timestamp
                    offline_msg = {
                        "from": message.get("from"),
                        "is_file": True,
                        "filename": message.get("filename"),
                        "data": message.get("data"),
                        "timestamp": message.get("timestamp")  # Preserve original timestamp
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
                description = message.get("description", "")  # Optional description
                
                # Create group with description
                groups[gname] = {
                    "admin": creator, 
                    "members": [creator],
                    "description": description
                }
                
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
                broadcast_to_group(gname, sender, message)

            elif msg_type == "UNFRIEND":
                from_user = message["from"]
                target_user = message["target"]
                
                print(f"[DEBUG] UNFRIEND request from {from_user} to {target_user}")
                print(f"[DEBUG] from_user in usernames: {from_user in usernames}")
                print(f"[DEBUG] target_user exists check: checking friendship...")
                
                # Check if users are friends (don't require both to be online)
                if are_friends(from_user, target_user):
                    print(f"[DEBUG] Users are friends, proceeding with unfriend...")
                    
                    # Remove friendship from both sides
                    # Load and update from_user's friends list
                    from_user_friends_file = f"friends_{from_user}.json"
                    try:
                        if os.path.exists(from_user_friends_file):
                            with open(from_user_friends_file, 'r') as f:
                                from_user_friends = set(json.load(f))
                        else:
                            from_user_friends = set()
                        
                        print(f"[DEBUG] from_user friends before: {from_user_friends}")
                        from_user_friends.discard(target_user)
                        print(f"[DEBUG] from_user friends after: {from_user_friends}")
                        
                        with open(from_user_friends_file, 'w') as f:
                            json.dump(list(from_user_friends), f)
                    except Exception as e:
                        print(f"[DEBUG] Error updating {from_user}'s friend list: {e}")
                    
                    # Load and update target_user's friends list
                    target_user_friends_file = f"friends_{target_user}.json"
                    try:
                        if os.path.exists(target_user_friends_file):
                            with open(target_user_friends_file, 'r') as f:
                                target_user_friends = set(json.load(f))
                        else:
                            target_user_friends = set()
                            
                        print(f"[DEBUG] target_user friends before: {target_user_friends}")
                        target_user_friends.discard(from_user)
                        print(f"[DEBUG] target_user friends after: {target_user_friends}")
                        
                        with open(target_user_friends_file, 'w') as f:
                            json.dump(list(target_user_friends), f)
                    except Exception as e:
                        print(f"[DEBUG] Error updating {target_user}'s friend list: {e}")
                    
                    # Reload friendships to update server's friendship tracking
                    load_friendships()
                    print(f"[DEBUG] Friendships reloaded")
                    
                    # Send confirmation to the unfriending user (only if online)
                    if from_user in usernames:
                        send_json(usernames[from_user], {
                            "type": "UNFRIEND_SUCCESS",
                            "message": f"You have unfriended {target_user}.",
                            "unfriended_user": target_user
                        })
                        print(f"[DEBUG] Sent UNFRIEND_SUCCESS to {from_user}")
                    
                    # Notify the target user if they're online
                    if target_user in usernames:
                        send_json(usernames[target_user], {
                            "type": "UNFRIENDED_BY",
                            "message": f"{from_user} has removed you from their friends.",
                            "unfriended_by": from_user
                        })
                        print(f"[DEBUG] Sent UNFRIENDED_BY to {target_user}")
                else:
                    # Not friends - send error
                    print(f"[DEBUG] Users are not friends")
                    if from_user in usernames:
                        send_json(usernames[from_user], {
                            "type": "UNFRIEND_ERROR",
                            "message": f"You are not friends with {target_user}."
                        })

            elif msg_type == "LEAVE_GROUP":
                gname = message["group_name"]
                user = message["user"]
                
                # Only allow leaving if user is a member and not the admin
                if gname in groups and user in groups[gname]['members']:
                    if groups[gname]['admin'] != user:  # Admin cannot leave
                        groups[gname]['members'].remove(user)
                        
                        # Save updated groups to file
                        with open(f"{data_folder}/groups.json", "w") as f:
                            json.dump(groups, f)
                        
                        # Notify other group members about user leaving
                        leave_notification = {
                            "type": "GROUP_MESSAGE",
                            "group_name": gname,
                            "from": "System",
                            "msg": f"{user} has left the group.",
                            "timestamp": str(time.time())
                        }
                        
                        for member in groups[gname]['members']:
                            if member in usernames:
                                send_json(usernames[member], leave_notification)
                        
                        # Send confirmation to leaving user
                        if user in usernames:
                            send_json(usernames[user], {
                                "type": "LEAVE_GROUP_SUCCESS",
                                "group_name": gname
                            })
                    else:
                        # Admin cannot leave - send error
                        if user in usernames:
                            send_json(usernames[user], {
                                "type": "LEAVE_GROUP_ERROR",
                                "message": "Group admin cannot leave the group.",
                                "group_name": gname
                            })

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
