import socket
import threading
import json
import os
import time
import datetime
import hashlib
from typing import Dict, List, Set

# Server configuration
HOST = '127.0.0.1'
PORT = 9999

class ChatServer:
    def __init__(self):
        self.clients: Dict[str, socket.socket] = {}  # username -> socket
        self.users_db = {}  # user database
        self.groups_db = {}  # group database
        self.offline_messages = {}  # username -> list of messages
        self.friend_requests = {}  # pending friend requests
        self.lock = threading.Lock()
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        
        # Load existing data
        self.load_users()
        self.load_groups()
        self.load_offline_messages()
        
        print("[SERVER] Chat Server initialized")

    def load_users(self):
        """Load users from JSON file"""
        try:
            if os.path.exists('data/users.json'):
                with open('data/users.json', 'r') as f:
                    self.users_db = json.load(f)
                print(f"[SERVER] Loaded {len(self.users_db)} users")
            else:
                self.users_db = {}
                print("[SERVER] No users file found, starting fresh")
        except Exception as e:
            print(f"[SERVER] Error loading users: {e}")
            self.users_db = {}

    def save_users(self):
        """Save users to JSON file"""
        try:
            with open('data/users.json', 'w') as f:
                json.dump(self.users_db, f, indent=2)
            print(f"[SERVER] Saved {len(self.users_db)} users")
        except Exception as e:
            print(f"[SERVER] Error saving users: {e}")

    def load_groups(self):
        """Load groups from JSON file"""
        try:
            if os.path.exists('data/groups.json'):
                with open('data/groups.json', 'r') as f:
                    self.groups_db = json.load(f)
                print(f"[SERVER] Loaded {len(self.groups_db)} groups")
            else:
                self.groups_db = {}
                print("[SERVER] No groups file found, starting fresh")
        except Exception as e:
            print(f"[SERVER] Error loading groups: {e}")
            self.groups_db = {}

    def save_groups(self):
        """Save groups to JSON file"""
        try:
            with open('data/groups.json', 'w') as f:
                json.dump(self.groups_db, f, indent=2)
            print(f"[SERVER] Saved {len(self.groups_db)} groups")
        except Exception as e:
            print(f"[SERVER] Error saving groups: {e}")

    def load_offline_messages(self):
        """Load offline messages from JSON file"""
        try:
            if os.path.exists('data/offline_messages.json'):
                with open('data/offline_messages.json', 'r') as f:
                    self.offline_messages = json.load(f)
                print(f"[SERVER] Loaded offline messages for {len(self.offline_messages)} users")
            else:
                self.offline_messages = {}
                print("[SERVER] No offline messages file found, starting fresh")
        except Exception as e:
            print(f"[SERVER] Error loading offline messages: {e}")
            self.offline_messages = {}

    def save_offline_messages(self):
        """Save offline messages to JSON file"""
        try:
            with open('data/offline_messages.json', 'w') as f:
                json.dump(self.offline_messages, f, indent=2)
            print(f"[SERVER] Saved offline messages for {len(self.offline_messages)} users")
        except Exception as e:
            print(f"[SERVER] Error saving offline messages: {e}")

    def get_friend_file_path(self, username):
        """Get the path to a user's friend file"""
        return f'data/friends_{username}.json'

    def load_friends(self, username):
        """Load friends list for a user"""
        try:
            friend_file = self.get_friend_file_path(username)
            if os.path.exists(friend_file):
                with open(friend_file, 'r') as f:
                    friends = json.load(f)
                return set(friends)
            else:
                return set()
        except Exception as e:
            print(f"[SERVER] Error loading friends for {username}: {e}")
            return set()

    def save_friends(self, username, friends):
        """Save friends list for a user"""
        try:
            friend_file = self.get_friend_file_path(username)
            with open(friend_file, 'w') as f:
                json.dump(list(friends), f)
            print(f"[SERVER] Saved {len(friends)} friends for {username}")
        except Exception as e:
            print(f"[SERVER] Error saving friends for {username}: {e}")

    def add_friend_relationship(self, user1, user2):
        """Add bidirectional friendship between two users"""
        print(f"[SERVER] Adding friend relationship: {user1} <-> {user2}")
        
        # Load both users' friend lists
        user1_friends = self.load_friends(user1)
        user2_friends = self.load_friends(user2)
        
        # Add each other to friend lists
        user1_friends.add(user2)
        user2_friends.add(user1)
        
        # Save both friend lists
        self.save_friends(user1, user1_friends)
        self.save_friends(user2, user2_friends)
        
        print(f"[SERVER] Friend relationship established: {user1} now has {len(user1_friends)} friends, {user2} now has {len(user2_friends)} friends")

    def remove_friend_relationship(self, user1, user2):
        """Remove bidirectional friendship between two users"""
        print(f"[SERVER] Removing friend relationship: {user1} <-> {user2}")
        
        # Load both users' friend lists
        user1_friends = self.load_friends(user1)
        user2_friends = self.load_friends(user2)
        
        # Remove each other from friend lists
        user1_friends.discard(user2)
        user2_friends.discard(user1)
        
        # Save both friend lists
        self.save_friends(user1, user1_friends)
        self.save_friends(user2, user2_friends)
        
        print(f"[SERVER] Friend relationship removed: {user1} now has {len(user1_friends)} friends, {user2} now has {len(user2_friends)} friends")

    def send_json(self, sock, obj):
        """Send JSON data to a client"""
        try:
            data = json.dumps(obj).encode('utf-8')
            length = f'{len(data):08d}'.encode('utf-8')
            sock.sendall(length + data)
        except Exception as e:
            print(f"[SERVER] Error sending data: {e}")
            raise

    def recv_json(self, sock):
        """Receive JSON data from a client"""
        try:
            # Receive length header (8 bytes)
            length_bytes = b''
            while len(length_bytes) < 8:
                chunk = sock.recv(8 - len(length_bytes))
                if not chunk:
                    raise ConnectionError("Connection closed by client")
                length_bytes += chunk
            
            # Parse length
            length = int(length_bytes.decode('utf-8'))
            
            # Receive data
            data = b''
            while len(data) < length:
                chunk = sock.recv(length - len(data))
                if not chunk:
                    raise ConnectionError("Connection closed by client")
                data += chunk
            
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            print(f"[SERVER] Error receiving data: {e}")
            raise

    def broadcast_to_group(self, group_name, message, exclude_user=None):
        """Broadcast message to all members of a group"""
        if group_name not in self.groups_db:
            return
        
        group_members = self.groups_db[group_name].get('members', [])
        for member in group_members:
            if member != exclude_user and member in self.clients:
                try:
                    self.send_json(self.clients[member], message)
                except Exception as e:
                    print(f"[SERVER] Error broadcasting to {member}: {e}")

    def store_offline_message(self, username, message):
        """Store a message for offline user"""
        if username not in self.offline_messages:
            self.offline_messages[username] = []
        
        # Add timestamp to the message
        message['timestamp'] = datetime.datetime.now().isoformat()
        self.offline_messages[username].append(message)
        self.save_offline_messages()
        print(f"[SERVER] Stored offline message for {username}")

    def send_offline_messages(self, username):
        """Send all offline messages to a user when they come online"""
        if username in self.offline_messages and self.offline_messages[username]:
            messages = self.offline_messages[username]
            try:
                self.send_json(self.clients[username], {
                    'type': 'OFFLINE_MESSAGES',
                    'messages': messages
                })
                print(f"[SERVER] Sent {len(messages)} offline messages to {username}")
                
                # Clear offline messages after sending
                self.offline_messages[username] = []
                self.save_offline_messages()
                
            except Exception as e:
                print(f"[SERVER] Error sending offline messages to {username}: {e}")

    def handle_client(self, client_socket, client_address):
        """Handle communication with a client"""
        username = None
        try:
            print(f"[SERVER] New client connected from {client_address}")
            
            while True:
                try:
                    message = self.recv_json(client_socket)
                    msg_type = message.get('type')
                    
                    if msg_type == 'REGISTER':
                        username = self.handle_register(client_socket, message)
                    elif msg_type == 'LOGIN':
                        username = self.handle_login(client_socket, message)
                    elif msg_type == 'LIST_REQUEST':
                        self.handle_list_request(client_socket)
                    elif msg_type == 'GET_ALL_USERS':
                        self.handle_get_all_users(client_socket)
                    elif msg_type == 'FRIEND_REQUEST':
                        self.handle_friend_request(client_socket, message)
                    elif msg_type == 'FRIEND_REQUEST_RESPONSE':
                        self.handle_friend_request_response(client_socket, message)
                    elif msg_type == 'PRIVATE_MESSAGE':
                        self.handle_private_message(client_socket, message)
                    elif msg_type == 'GROUP_MESSAGE':
                        self.handle_group_message(client_socket, message)
                    elif msg_type == 'MEDIA':
                        self.handle_media_message(client_socket, message)
                    elif msg_type == 'GROUP_MEDIA':
                        self.handle_group_media(client_socket, message)
                    elif msg_type == 'CREATE_GROUP':
                        self.handle_create_group(client_socket, message)
                    elif msg_type == 'GROUP_INVITE':
                        self.handle_group_invite(client_socket, message)
                    elif msg_type == 'GROUP_INVITE_RESPONSE':
                        self.handle_group_invite_response(client_socket, message)
                    elif msg_type == 'JOIN_GROUP':
                        self.handle_join_group(client_socket, message)
                    elif msg_type == 'LEAVE_GROUP':
                        self.handle_leave_group(client_socket, message)
                    elif msg_type == 'UNFRIEND':
                        self.handle_unfriend(client_socket, message)
                    elif msg_type == 'GET_FRIEND_LIST':
                        self.handle_get_friend_list(client_socket, message)
                    elif msg_type == 'EDIT_PROFILE':
                        self.handle_edit_profile(client_socket, message)
                    elif msg_type == 'PING':
                        self.send_json(client_socket, {'type': 'PONG'})
                    elif msg_type == 'LOGOUT':
                        print(f"[SERVER] {username} logged out")
                        break
                    else:
                        print(f"[SERVER] Unknown message type: {msg_type}")
                        
                except ConnectionError:
                    print(f"[SERVER] Connection lost with {username or client_address}")
                    break
                except Exception as e:
                    print(f"[SERVER] Error handling message from {username or client_address}: {e}")
                    continue
                    
        except Exception as e:
            print(f"[SERVER] Error in client handler for {username or client_address}: {e}")
        finally:
            # Clean up client connection
            if username and username in self.clients:
                with self.lock:
                    del self.clients[username]
                print(f"[SERVER] {username} disconnected")
            
            try:
                client_socket.close()
            except:
                pass

    def handle_register(self, client_socket, message):
        """Handle user registration"""
        try:
            user_data = message['data']
            username = user_data['name']
            
            with self.lock:
                if username in self.users_db:
                    self.send_json(client_socket, {
                        'type': 'REGISTER_ERROR',
                        'message': 'Username already exists'
                    })
                    return None
                
                # Store user data
                self.users_db[username] = user_data
                self.save_users()
                
                # Add client to active clients
                self.clients[username] = client_socket
                
                # Get user's groups
                user_groups = []
                for group_name, group_data in self.groups_db.items():
                    if username in group_data.get('members', []):
                        user_groups.append(group_name)
                
                self.send_json(client_socket, {
                    'type': 'REGISTER_SUCCESS',
                    'groups': user_groups
                })
                
                # Send offline messages
                self.send_offline_messages(username)
                
                print(f"[SERVER] User {username} registered successfully")
                return username
                
        except Exception as e:
            print(f"[SERVER] Error in registration: {e}")
            self.send_json(client_socket, {
                'type': 'REGISTER_ERROR',
                'message': 'Registration failed'
            })
            return None

    def handle_login(self, client_socket, message):
        """Handle user login"""
        try:
            username = message['name']
            password = message['password']
            
            with self.lock:
                if username not in self.users_db:
                    self.send_json(client_socket, {
                        'type': 'LOGIN_ERROR',
                        'message': 'User not found'
                    })
                    return None
                
                if self.users_db[username]['password'] != password:
                    self.send_json(client_socket, {
                        'type': 'LOGIN_ERROR',
                        'message': 'Invalid password'
                    })
                    return None
                
                # Add client to active clients
                self.clients[username] = client_socket
                
                # Get user's groups
                user_groups = []
                for group_name, group_data in self.groups_db.items():
                    if username in group_data.get('members', []):
                        user_groups.append(group_name)
                
                self.send_json(client_socket, {
                    'type': 'LOGIN_SUCCESS',
                    'user_info': self.users_db[username],
                    'groups': user_groups
                })
                
                # Send offline messages
                self.send_offline_messages(username)
                
                print(f"[SERVER] User {username} logged in successfully")
                return username
                
        except Exception as e:
            print(f"[SERVER] Error in login: {e}")
            self.send_json(client_socket, {
                'type': 'LOGIN_ERROR',
                'message': 'Login failed'
            })
            return None

    def handle_list_request(self, client_socket):
        """Handle request for online users list"""
        try:
            with self.lock:
                online_users = list(self.clients.keys())
                self.send_json(client_socket, {
                    'type': 'LIST_RESPONSE',
                    'users': online_users
                })
        except Exception as e:
            print(f"[SERVER] Error handling list request: {e}")

    def handle_get_all_users(self, client_socket):
        """Handle request for all registered users"""
        try:
            with self.lock:
                self.send_json(client_socket, {
                    'type': 'ALL_USERS_RESPONSE',
                    'users': self.users_db
                })
        except Exception as e:
            print(f"[SERVER] Error handling get all users request: {e}")

    def handle_friend_request(self, client_socket, message):
        """Handle friend request"""
        try:
            from_user = message['from']
            to_user = message['to']
            
            print(f"[SERVER] Friend request: {from_user} -> {to_user}")
            
            # Check if target user exists
            if to_user not in self.users_db:
                self.send_json(client_socket, {
                    'type': 'FRIEND_REQUEST_ERROR',
                    'message': 'User not found'
                })
                return
            
            # Get sender info for the request
            sender_info = self.users_db.get(from_user, {})
            
            # If target user is online, send request immediately
            if to_user in self.clients:
                try:
                    self.send_json(self.clients[to_user], {
                        'type': 'FRIEND_REQUEST',
                        'from': from_user,
                        'sender_info': sender_info
                    })
                    print(f"[SERVER] Friend request delivered to {to_user}")
                except Exception as e:
                    print(f"[SERVER] Error sending friend request to {to_user}: {e}")
                    # Store as offline message if sending fails
                    self.store_offline_message(to_user, {
                        'type': 'FRIEND_REQUEST',
                        'from': from_user,
                        'sender_info': sender_info,
                        'is_friend_request': True
                    })
            else:
                # Store as offline message
                self.store_offline_message(to_user, {
                    'type': 'FRIEND_REQUEST',
                    'from': from_user,
                    'sender_info': sender_info,
                    'is_friend_request': True
                })
                print(f"[SERVER] Friend request stored as offline message for {to_user}")
            
        except Exception as e:
            print(f"[SERVER] Error handling friend request: {e}")

    def handle_friend_request_response(self, client_socket, message):
        """Handle friend request response (accept/decline)"""
        try:
            from_user = message['from']  # User responding to request
            to_user = message['to']      # User who sent the request
            accepted = message['accepted']
            
            print(f"[SERVER] Friend request response: {from_user} {'accepted' if accepted else 'declined'} {to_user}")
            
            if accepted:
                # Add bidirectional friendship
                self.add_friend_relationship(from_user, to_user)
                
                # Notify the original requester
                if to_user in self.clients:
                    try:
                        self.send_json(self.clients[to_user], {
                            'type': 'FRIEND_REQUEST_ACCEPTED',
                            'from': from_user
                        })
                        print(f"[SERVER] Acceptance notification sent to {to_user}")
                    except Exception as e:
                        print(f"[SERVER] Error notifying {to_user} of acceptance: {e}")
                        # Store as offline message
                        self.store_offline_message(to_user, {
                            'type': 'FRIEND_REQUEST_ACCEPTED',
                            'from': from_user
                        })
                else:
                    # Store as offline message
                    self.store_offline_message(to_user, {
                        'type': 'FRIEND_REQUEST_ACCEPTED',
                        'from': from_user
                    })
                
                # Also notify the accepter that the friend was added
                try:
                    self.send_json(client_socket, {
                        'type': 'FRIEND_ADDED',
                        'friend': to_user
                    })
                    print(f"[SERVER] Friend added notification sent to {from_user}")
                except Exception as e:
                    print(f"[SERVER] Error sending friend added notification: {e}")
                    
            else:
                # Notify the original requester of decline
                if to_user in self.clients:
                    try:
                        self.send_json(self.clients[to_user], {
                            'type': 'FRIEND_REQUEST_DECLINED',
                            'from': from_user
                        })
                    except Exception as e:
                        print(f"[SERVER] Error notifying {to_user} of decline: {e}")
                        # Store as offline message
                        self.store_offline_message(to_user, {
                            'type': 'FRIEND_REQUEST_DECLINED',
                            'from': from_user
                        })
                else:
                    # Store as offline message
                    self.store_offline_message(to_user, {
                        'type': 'FRIEND_REQUEST_DECLINED',
                        'from': from_user
                    })
            
        except Exception as e:
            print(f"[SERVER] Error handling friend request response: {e}")

    def handle_private_message(self, client_socket, message):
        """Handle private message"""
        try:
            from_user = message['from']
            to_user = message['to']
            msg_text = message['msg']
            timestamp = message.get('timestamp', datetime.datetime.now().isoformat())
            
            print(f"[SERVER] Private message: {from_user} -> {to_user}: {msg_text[:50]}...")
            
            # Check if users are friends
            from_friends = self.load_friends(from_user)
            if to_user not in from_friends:
                self.send_json(client_socket, {
                    'type': 'MESSAGE_ERROR',
                    'reason': f'You are not friends with {to_user}'
                })
                return
            
            # If target user is online, send message immediately
            if to_user in self.clients:
                try:
                    self.send_json(self.clients[to_user], {
                        'type': 'PRIVATE_MESSAGE',
                        'from': from_user,
                        'msg': msg_text,
                        'timestamp': timestamp
                    })
                    print(f"[SERVER] Private message delivered to {to_user}")
                except Exception as e:
                    print(f"[SERVER] Error sending message to {to_user}: {e}")
                    # Store as offline message if sending fails
                    self.store_offline_message(to_user, {
                        'type': 'PRIVATE_MESSAGE',
                        'from': from_user,
                        'msg': msg_text,
                        'timestamp': timestamp,
                        'sender_info': self.users_db.get(from_user, {})
                    })
            else:
                # Store as offline message
                self.store_offline_message(to_user, {
                    'type': 'PRIVATE_MESSAGE',
                    'from': from_user,
                    'msg': msg_text,
                    'timestamp': timestamp,
                    'sender_info': self.users_db.get(from_user, {})
                })
                print(f"[SERVER] Private message stored as offline message for {to_user}")
            
        except Exception as e:
            print(f"[SERVER] Error handling private message: {e}")

    def handle_group_message(self, client_socket, message):
        """Handle group message"""
        try:
            from_user = message['from']
            group_name = message['group_name']
            msg_text = message['msg']
            timestamp = message.get('timestamp', datetime.datetime.now().isoformat())
            
            print(f"[SERVER] Group message: {from_user} -> {group_name}: {msg_text[:50]}...")
            
            # Check if group exists and user is a member
            if group_name not in self.groups_db:
                self.send_json(client_socket, {
                    'type': 'MESSAGE_ERROR',
                    'reason': f'Group {group_name} does not exist'
                })
                return
            
            if from_user not in self.groups_db[group_name]['members']:
                self.send_json(client_socket, {
                    'type': 'MESSAGE_ERROR',
                    'reason': f'You are not a member of {group_name}'
                })
                return
            
            # Broadcast to all group members
            group_message = {
                'type': 'GROUP_MESSAGE',
                'from': from_user,
                'group_name': group_name,
                'msg': msg_text,
                'timestamp': timestamp
            }
            
            self.broadcast_to_group(group_name, group_message, exclude_user=from_user)
            print(f"[SERVER] Group message broadcasted to {group_name}")
            
        except Exception as e:
            print(f"[SERVER] Error handling group message: {e}")

    def handle_media_message(self, client_socket, message):
        """Handle media (file) message"""
        try:
            from_user = message['from']
            to_user = message['to']
            filename = message['filename']
            filedata = message['data']
            timestamp = message.get('timestamp', datetime.datetime.now().isoformat())
            
            print(f"[SERVER] Media message: {from_user} -> {to_user}: {filename}")
            
            # Check if users are friends
            from_friends = self.load_friends(from_user)
            if to_user not in from_friends:
                self.send_json(client_socket, {
                    'type': 'MESSAGE_ERROR',
                    'reason': f'You are not friends with {to_user}'
                })
                return
            
            # If target user is online, send media immediately
            if to_user in self.clients:
                try:
                    self.send_json(self.clients[to_user], {
                        'type': 'MEDIA',
                        'from': from_user,
                        'filename': filename,
                        'data': filedata,
                        'timestamp': timestamp
                    })
                    print(f"[SERVER] Media message delivered to {to_user}")
                except Exception as e:
                    print(f"[SERVER] Error sending media to {to_user}: {e}")
                    # Store as offline message if sending fails
                    self.store_offline_message(to_user, {
                        'type': 'MEDIA',
                        'from': from_user,
                        'filename': filename,
                        'data': filedata,
                        'timestamp': timestamp,
                        'is_file': True,
                        'sender_info': self.users_db.get(from_user, {})
                    })
            else:
                # Store as offline message
                self.store_offline_message(to_user, {
                    'type': 'MEDIA',
                    'from': from_user,
                    'filename': filename,
                    'data': filedata,
                    'timestamp': timestamp,
                    'is_file': True,
                    'sender_info': self.users_db.get(from_user, {})
                })
                print(f"[SERVER] Media message stored as offline message for {to_user}")
            
        except Exception as e:
            print(f"[SERVER] Error handling media message: {e}")

    def handle_group_media(self, client_socket, message):
        """Handle group media (file) message"""
        try:
            from_user = message['from']
            group_name = message['group_name']
            filename = message['filename']
            filedata = message['data']
            timestamp = message.get('timestamp', datetime.datetime.now().isoformat())
            
            print(f"[SERVER] Group media: {from_user} -> {group_name}: {filename}")
            
            # Check if group exists and user is a member
            if group_name not in self.groups_db:
                self.send_json(client_socket, {
                    'type': 'MESSAGE_ERROR',
                    'reason': f'Group {group_name} does not exist'
                })
                return
            
            if from_user not in self.groups_db[group_name]['members']:
                self.send_json(client_socket, {
                    'type': 'MESSAGE_ERROR',
                    'reason': f'You are not a member of {group_name}'
                })
                return
            
            # Broadcast to all group members
            group_media = {
                'type': 'GROUP_MEDIA',
                'from': from_user,
                'group_name': group_name,
                'filename': filename,
                'data': filedata,
                'timestamp': timestamp
            }
            
            self.broadcast_to_group(group_name, group_media, exclude_user=from_user)
            print(f"[SERVER] Group media broadcasted to {group_name}")
            
        except Exception as e:
            print(f"[SERVER] Error handling group media: {e}")

    def handle_create_group(self, client_socket, message):
        """Handle group creation"""
        try:
            group_name = message['group_name']
            creator = message['creator']
            description = message.get('description', '')
            
            print(f"[SERVER] Creating group: {group_name} by {creator}")
            
            with self.lock:
                if group_name in self.groups_db:
                    self.send_json(client_socket, {
                        'type': 'CREATE_GROUP_ERROR',
                        'message': 'Group already exists'
                    })
                    return
                
                # Create group
                self.groups_db[group_name] = {
                    'admin': creator,
                    'members': [creator],
                    'description': description,
                    'created_at': datetime.datetime.now().isoformat()
                }
                
                self.save_groups()
                
                self.send_json(client_socket, {
                    'type': 'CREATE_GROUP_SUCCESS',
                    'group_name': group_name
                })
                
                print(f"[SERVER] Group {group_name} created successfully")
                
        except Exception as e:
            print(f"[SERVER] Error creating group: {e}")
            self.send_json(client_socket, {
                'type': 'CREATE_GROUP_ERROR',
                'message': 'Failed to create group'
            })

    def handle_group_invite(self, client_socket, message):
        """Handle group invitation"""
        try:
            from_user = message['from']
            to_user = message['to']
            group_name = message['group_name']
            sender_info = message.get('inviter_info', self.users_db.get(from_user, {}))
            
            print(f"[SERVER] Group invite: {from_user} inviting {to_user} to {group_name}")
            
            # Check if group exists and sender is a member
            if group_name not in self.groups_db:
                self.send_json(client_socket, {
                    'type': 'GROUP_INVITE_ERROR',
                    'message': 'Group does not exist'
                })
                return
            
            if from_user not in self.groups_db[group_name]['members']:
                self.send_json(client_socket, {
                    'type': 'GROUP_INVITE_ERROR',
                    'message': 'You are not a member of this group'
                })
                return
            
            # Check if target user exists
            if to_user not in self.users_db:
                self.send_json(client_socket, {
                    'type': 'GROUP_INVITE_ERROR',
                    'message': 'User not found'
                })
                return
            
            # Check if user is already in the group
            if to_user in self.groups_db[group_name]['members']:
                self.send_json(client_socket, {
                    'type': 'GROUP_INVITE_ERROR',
                    'message': 'User is already a member of this group'
                })
                return
            
            # Send invitation
            invite_message = {
                'type': 'GROUP_INVITE',
                'from': from_user,
                'group_name': group_name,
                'sender_info': sender_info
            }
            
            if to_user in self.clients:
                try:
                    self.send_json(self.clients[to_user], invite_message)
                    print(f"[SERVER] Group invitation sent to {to_user}")
                except Exception as e:
                    print(f"[SERVER] Error sending group invite to {to_user}: {e}")
                    # Store as offline message
                    self.store_offline_message(to_user, {
                        **invite_message,
                        'is_group_invite': True
                    })
            else:
                # Store as offline message
                self.store_offline_message(to_user, {
                    **invite_message,
                    'is_group_invite': True
                })
                print(f"[SERVER] Group invitation stored as offline message for {to_user}")
            
        except Exception as e:
            print(f"[SERVER] Error handling group invite: {e}")

    def handle_group_invite_response(self, client_socket, message):
        """Handle group invitation response"""
        try:
            from_user = message['from']
            group_name = message['group_name']
            accepted = message['accepted']
            inviter = message.get('inviter')
            
            print(f"[SERVER] Group invite response: {from_user} {'accepted' if accepted else 'declined'} invite to {group_name}")
            
            if accepted:
                # Add user to group
                with self.lock:
                    if group_name in self.groups_db:
                        if from_user not in self.groups_db[group_name]['members']:
                            self.groups_db[group_name]['members'].append(from_user)
                            self.save_groups()
                            
                            # Notify user of successful join
                            self.send_json(client_socket, {
                                'type': 'GROUP_JOIN_SUCCESS',
                                'group_name': group_name
                            })
                            
                            # Notify inviter if they're online
                            if inviter and inviter in self.clients:
                                try:
                                    self.send_json(self.clients[inviter], {
                                        'type': 'GROUP_INVITE_ACCEPTED',
                                        'from': from_user,
                                        'group_name': group_name
                                    })
                                except Exception as e:
                                    print(f"[SERVER] Error notifying inviter: {e}")
                            
                            print(f"[SERVER] {from_user} joined group {group_name}")
                        else:
                            self.send_json(client_socket, {
                                'type': 'GROUP_INVITE_ERROR',
                                'message': 'You are already a member of this group'
                            })
                    else:
                        self.send_json(client_socket, {
                            'type': 'GROUP_INVITE_ERROR',
                            'message': 'Group no longer exists'
                        })
            else:
                # Notify inviter of decline if they're online
                if inviter and inviter in self.clients:
                    try:
                        self.send_json(self.clients[inviter], {
                            'type': 'GROUP_INVITE_DECLINED',
                            'from': from_user,
                            'group_name': group_name
                        })
                    except Exception as e:
                        print(f"[SERVER] Error notifying inviter of decline: {e}")
            
        except Exception as e:
            print(f"[SERVER] Error handling group invite response: {e}")

    def handle_join_group(self, client_socket, message):
        """Handle direct group join request"""
        try:
            group_name = message['group_name']
            username = message['user']
            
            print(f"[SERVER] Join group request: {username} -> {group_name}")
            
            with self.lock:
                if group_name not in self.groups_db:
                    self.send_json(client_socket, {
                        'type': 'JOIN_GROUP_ERROR',
                        'message': 'Group does not exist'
                    })
                    return
                
                if username in self.groups_db[group_name]['members']:
                    self.send_json(client_socket, {
                        'type': 'JOIN_GROUP_ERROR',
                        'message': 'You are already a member of this group'
                    })
                    return
                
                # Add user to group
                self.groups_db[group_name]['members'].append(username)
                self.save_groups()
                
                self.send_json(client_socket, {
                    'type': 'GROUP_JOIN_SUCCESS',
                    'group_name': group_name
                })
                
                print(f"[SERVER] {username} joined group {group_name}")
                
        except Exception as e:
            print(f"[SERVER] Error handling join group: {e}")

    def handle_leave_group(self, client_socket, message):
        """Handle group leave request"""
        try:
            group_name = message['group_name']
            username = message['user']
            
            print(f"[SERVER] Leave group request: {username} leaving {group_name}")
            
            with self.lock:
                if group_name not in self.groups_db:
                    self.send_json(client_socket, {
                        'type': 'LEAVE_GROUP_ERROR',
                        'message': 'Group does not exist'
                    })
                    return
                
                if username not in self.groups_db[group_name]['members']:
                    self.send_json(client_socket, {
                        'type': 'LEAVE_GROUP_ERROR',
                        'message': 'You are not a member of this group'
                    })
                    return
                
                # Remove user from group
                self.groups_db[group_name]['members'].remove(username)
                
                # If group is empty and user was admin, delete the group
                if not self.groups_db[group_name]['members']:
                    del self.groups_db[group_name]
                    print(f"[SERVER] Group {group_name} deleted (no members left)")
                elif self.groups_db[group_name]['admin'] == username:
                    # Transfer admin to first remaining member
                    self.groups_db[group_name]['admin'] = self.groups_db[group_name]['members'][0]
                    print(f"[SERVER] Admin of {group_name} transferred to {self.groups_db[group_name]['admin']}")
                
                self.save_groups()
                
                self.send_json(client_socket, {
                    'type': 'LEAVE_GROUP_SUCCESS',
                    'group_name': group_name
                })
                
                print(f"[SERVER] {username} left group {group_name}")
                
        except Exception as e:
            print(f"[SERVER] Error handling leave group: {e}")

    def handle_unfriend(self, client_socket, message):
        """Handle unfriend request"""
        try:
            from_user = message['from']
            target_user = message['target']
            
            print(f"[SERVER] Unfriend request: {from_user} unfriending {target_user}")
            
            # Remove bidirectional friendship
            self.remove_friend_relationship(from_user, target_user)
            
            # Notify the requesting user of success
            self.send_json(client_socket, {
                'type': 'UNFRIEND_SUCCESS',
                'unfriended_user': target_user
            })
            
            # Notify the target user if they're online
            if target_user in self.clients:
                try:
                    self.send_json(self.clients[target_user], {
                        'type': 'UNFRIENDED_BY',
                        'unfriended_by': from_user
                    })
                    print(f"[SERVER] Notified {target_user} of being unfriended by {from_user}")
                except Exception as e:
                    print(f"[SERVER] Error notifying {target_user} of unfriend: {e}")
            
            print(f"[SERVER] Unfriend completed: {from_user} <-> {target_user}")
            
        except Exception as e:
            print(f"[SERVER] Error handling unfriend: {e}")
            self.send_json(client_socket, {
                'type': 'UNFRIEND_ERROR',
                'message': 'Failed to unfriend user'
            })

    def handle_get_friend_list(self, client_socket, message):
        """Handle request for friend list"""
        try:
            username = message['username']
            friends = self.load_friends(username)
            
            self.send_json(client_socket, {
                'type': 'FRIEND_LIST_RESPONSE',
                'friends': list(friends)
            })
            
            print(f"[SERVER] Sent friend list to {username}: {len(friends)} friends")
            
        except Exception as e:
            print(f"[SERVER] Error handling get friend list: {e}")

    def handle_edit_profile(self, client_socket, message):
        """Handle profile edit request"""
        try:
            username = message['name']
            new_info = message['new_info']
            
            with self.lock:
                if username in self.users_db:
                    self.users_db[username].update(new_info)
                    self.save_users()
                    
                    self.send_json(client_socket, {
                        'type': 'EDIT_PROFILE_SUCCESS'
                    })
                    
                    print(f"[SERVER] Profile updated for {username}")
                else:
                    self.send_json(client_socket, {
                        'type': 'EDIT_PROFILE_ERROR',
                        'message': 'User not found'
                    })
            
        except Exception as e:
            print(f"[SERVER] Error handling profile edit: {e}")

    def start_server(self):
        """Start the chat server"""
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((HOST, PORT))
            server_socket.listen(5)
            
            print(f"[SERVER] Chat server started on {HOST}:{PORT}")
            print("[SERVER] Waiting for connections...")
            
            while True:
                try:
                    client_socket, client_address = server_socket.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                except Exception as e:
                    print(f"[SERVER] Error accepting connection: {e}")
                    
        except Exception as e:
            print(f"[SERVER] Error starting server: {e}")
        finally:
            try:
                server_socket.close()
            except:
                pass

if __name__ == "__main__":
    print("=== Python Chat Server ===")
    print("Features:")
    print("- User registration and login")
    print("- Friend management with bidirectional sync")
    print("- Private messaging between friends")
    print("- Group chat functionality")
    print("- File sharing (private and group)")
    print("- Offline message storage")
    print("- Profile management")
    print("- Real-time notifications")
    print("=" * 30)
    
    server = ChatServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\n[SERVER] Server shutting down...")
    except Exception as e:
        print(f"[SERVER] Server error: {e}")
