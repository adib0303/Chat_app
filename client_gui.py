import socket
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
import json
import os
import base64
import tempfile
import time
import datetime

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_data_path(filename):
    """Get the absolute path to a file in the data directory"""
    return os.path.join(SCRIPT_DIR, 'data', filename)

def get_chat_path(filename):
    """Get the absolute path to a chat history file"""
    return os.path.join(SCRIPT_DIR, filename)

def get_user_info_from_server(sock, username):
    """Get user information from server"""
    try:
        send_json(sock, {'type': 'GET_USER_INFO', 'username': username})
        resp = recv_json(sock)
        if resp.get('type') == 'USER_INFO_RESPONSE':
            return resp.get('user_info', {'name': username, 'dept': 'Unknown', 'session': 'Unknown'})
    except Exception:
        pass
    return {'name': username, 'dept': 'Unknown', 'session': 'Unknown'}
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Import TCP Reno simulation
try:
    from tcp_reno_simulator import (initialize_reno, simulate_reno_transmission, get_reno_stats, 
                                   toggle_reno, reset_reno_stats, show_reno_graph, 
                                   start_graph_recording, stop_graph_recording, save_reno_graph)
    RDT_AVAILABLE = True
    print("[CHAT] 🚀 TCP Reno Algorithm module loaded!")
except ImportError:
    RDT_AVAILABLE = False
    print("[CHAT] ⚠️  TCP Reno Algorithm module not available")

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 9999

def send_json(sock, obj):
    """
    Send JSON data with RDT simulation and better error handling
    """
    try:
        # Check if socket is valid before sending
        if sock is None:
            raise ConnectionError('Socket is None')
        
        # Check if socket is still connected
        try:
            sock.getpeername()
        except socket.error:
            raise ConnectionError('Socket is not connected')
        
        data = json.dumps(obj).encode('utf-8')
        length = f'{len(data):08d}'.encode('utf-8')
        
        # Validate that we're sending a proper length header
        if len(length) != 8:
            raise ValueError(f"Length header must be 8 bytes, got {len(length)}")
        
        # RDT Simulation for message transmission
        if RDT_AVAILABLE:
            # Determine data type for RDT simulation
            data_type = "message"
            if obj.get('type') == 'MEDIA':
                data_type = "media_file"
            elif obj.get('type') == 'GROUP_MEDIA':
                data_type = "group_media_file"
            elif obj.get('type') == 'GROUP_MESSAGE':
                data_type = "group_message"
            elif obj.get('type') == 'PRIVATE_MESSAGE':
                data_type = "private_message"
            
            # TCP Reno simulation (no delays)
            simulate_reno_transmission(obj, data_type)
            
        # Send all data at once to avoid partial sends
        full_message = length + data
        sock.sendall(full_message)
        
        # Update last activity time for connection monitoring
        # (only if this is being called from ChatClient instance)
        try:
            import inspect
            frame = inspect.currentframe()
            if frame and frame.f_back and hasattr(frame.f_back.f_locals.get('self'), 'last_activity'):
                frame.f_back.f_locals['self'].last_activity = time.time()
        except:
            pass  # Safe to ignore if not in ChatClient context
        
        # Optional debug for problematic cases
        # print(f"[SEND] Sent {len(full_message)} bytes (header: {repr(length)}, data: {len(data)} bytes)")
        
    except socket.error as e:
        raise ConnectionError(f'Failed to send message: {e}')
    except Exception as e:
        raise ConnectionError(f'Error preparing message: {e}')

def recv_full(sock, length):
    data = b''
    while len(data) < length:
        try:
            more = sock.recv(length - len(data))
            if not more:
                raise ConnectionError('Socket closed')
            data += more
        except socket.timeout:
            raise ConnectionError('Socket timeout while reading data')
        except socket.error as e:
            raise ConnectionError(f'Socket error while reading data: {e}')
    return data

def recv_json(sock):
    """
    Receive JSON data with improved error handling and protocol recovery
    """
    length_bytes = b''
    while len(length_bytes) < 8:
        try:
            more = sock.recv(8 - len(length_bytes))
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
            print(f"[PROTOCOL ERROR] Invalid length received:")
            print(f"  Raw bytes: {repr(length_bytes)}")
            print(f"  Decoded string: {repr(length_str)}")
            print(f"  Length: {len(length_str)}")
            print(f"  Is digit: {length_str.isdigit()}")
            
            # Try to recover by looking for a valid length pattern
            if len(length_bytes) >= 8:
                # Check if we can find a valid 8-digit pattern
                for i in range(len(length_bytes) - 7):
                    test_bytes = length_bytes[i:i+8]
                    try:
                        test_str = test_bytes.decode('utf-8')
                        if test_str.isdigit() and len(test_str) == 8:
                            print(f"[RECOVERY] Found valid length pattern at offset {i}: {test_str}")
                            # Would need to adjust the stream here, but this is complex
                            break
                    except:
                        continue
            
            raise ValueError(f"Invalid length format: {repr(length_str)} (expected 8 digits)")
        
        length = int(length_str)
        if length < 0 or length > 1000000:  # Reasonable size limit
            raise ValueError(f"Invalid message length: {length}")
            
    except (UnicodeDecodeError, ValueError) as e:
        raise ConnectionError(f'Invalid message length received: {repr(length_bytes)} - {e}')
    
    data = recv_full(sock, length)
    try:
        return json.loads(data.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"[JSON ERROR] Failed to parse JSON:")
        print(f"  Data length: {len(data)}")
        print(f"  First 100 bytes: {repr(data[:100])}")
        raise ConnectionError(f'Invalid JSON data received: {repr(data[:100])}... - {e}')

class FriendManager:
    def __init__(self, username):
        self.username = username
        self.file = get_data_path(f"friends_{username}.json")
        self.friends = set()
        self.load()

    def load(self):
        """Load friends from JSON file"""
        try:
            if os.path.exists(self.file):
                with open(self.file, 'r') as f:
                    friends_list = json.load(f)
                    self.friends = set(friends_list)
                    print(f"[FRIEND_MANAGER] Loaded {len(self.friends)} friends for {self.username}: {list(self.friends)}")
            else:
                self.friends = set()
                print(f"[FRIEND_MANAGER] No friend file found for {self.username}, starting with empty list")
        except Exception as e:
            print(f"[FRIEND_MANAGER] Error loading friends for {self.username}: {e}")
            self.friends = set()

    def reload(self):
        """Force reload friends from file"""
        print(f"[FRIEND_MANAGER] Force reloading friends for {self.username}")
        self.load()

    def save(self):
        """Save friends to JSON file"""
        try:
            with open(self.file, 'w') as f:
                json.dump(list(self.friends), f)
            print(f"[FRIEND_MANAGER] Saved {len(self.friends)} friends for {self.username}: {list(self.friends)}")
        except Exception as e:
            print(f"[FRIEND_MANAGER] Error saving friends for {self.username}: {e}")

    def add(self, friend):
        """Add a friend and save to file"""
        if friend not in self.friends:
            self.friends.add(friend)
            self.save()
            print(f"[FRIEND_MANAGER] Added {friend} to {self.username}'s friend list")
        else:
            print(f"[FRIEND_MANAGER] {friend} already in {self.username}'s friend list")

    def remove(self, friend):
        if friend in self.friends:
            self.friends.remove(friend)
            self.save()
            return True
        return False

    def is_friend(self, friend):
        return friend in self.friends

    def get_all(self):
        return list(self.friends)

class ChatClient:
    def load_status_icons(self):
        if not PIL_AVAILABLE:
            self.green_dot_img = self.red_dot_img = None
            return
            
        try:
            self.green_dot_img = ImageTk.PhotoImage(Image.open("green_dot.png").resize((14, 14)))
            self.red_dot_img = ImageTk.PhotoImage(Image.open("red_dot.png").resize((14, 14)))
        except Exception:
            self.green_dot_img = self.red_dot_img = None
    def refresh_status(self):
        if self.connected and self.friend_manager:
            friends = self.friend_manager.get_all()
            send_json(self.sock, {'type': 'STATUS', 'friends': friends})
    def __init__(self, master):
        self.master = master
        self.master.title('Python Chat Client')
        self.sock = None
        self.listener_thread = None
        self.username = None
        self.info = {}
        self.connected = False
        self.active_users = []
        self.group_name = None
        self.friend_manager = None
        self.notifications = {}
        self.notifications_home = {}  # Initialize notifications_home early
        self.find_friend_window = None
        self.current_chat = None  # (type, name) where type is 'private' or 'group'
        
        # Connection monitoring
        self.last_activity = time.time()
        self.connection_check_interval = 30  # Check every 30 seconds
        
        self.build_login()

    def build_login(self):
        self.clear_window()
        self.login_mode = True  # True for login, False for register
        # Ensure previous socket is closed and listener thread is stopped
        if hasattr(self, 'listener_thread') and self.listener_thread and self.listener_thread.is_alive():
            self.connected = False  # Signal thread to exit
            try:
                if self.sock:
                    self.sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            self.listener_thread.join(timeout=1)
        try:
            if hasattr(self, 'sock') and self.sock:
                self.sock.close()
        except Exception:
            pass
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.login_frame = tk.Frame(self.master)
        self.login_frame.pack(pady=40)
        tk.Label(self.login_frame, text='Login', font=('Arial', 16, 'bold')).pack(pady=(0, 20))
        tk.Label(self.login_frame, text='Username:').pack()
        self.name_entry = tk.Entry(self.login_frame)
        self.name_entry.pack()
        tk.Label(self.login_frame, text='Password:').pack()
        self.password_entry = tk.Entry(self.login_frame, show='*')
        self.password_entry.pack()
        btn_frame = tk.Frame(self.login_frame)
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text='Login', width=10, command=self.login).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text='Register', width=10, command=self.show_register).pack(side=tk.LEFT, padx=5)
        tk.Button(self.login_frame, text='Quit', width=10, command=self.quit_app).pack(pady=5)

    def quit_app(self):
        # Close socket and terminate the app
        try:
            if hasattr(self, 'sock') and self.sock:
                self.sock.close()
        except Exception:
            pass
        self.master.destroy()

    def show_register(self):
        self.clear_window()
        self.login_mode = False
        self.register_frame = tk.Frame(self.master)
        self.register_frame.pack(pady=30)
        tk.Label(self.register_frame, text='Register', font=('Arial', 16, 'bold')).pack(pady=(0, 20))
        tk.Label(self.register_frame, text='Username:').pack()
        self.name_entry = tk.Entry(self.register_frame)
        self.name_entry.pack()
        tk.Label(self.register_frame, text='Department:').pack()
        self.dept_entry = tk.Entry(self.register_frame)
        self.dept_entry.pack()
        tk.Label(self.register_frame, text='Session:').pack()
        self.session_entry = tk.Entry(self.register_frame)
        self.session_entry.pack()
        tk.Label(self.register_frame, text='Password:').pack()
        self.password_entry = tk.Entry(self.register_frame, show='*')
        self.password_entry.pack()
        btn_frame = tk.Frame(self.register_frame)
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text='Register', width=10, command=self.register).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text='Back to Login', width=12, command=self.build_login).pack(side=tk.LEFT, padx=5)

    def clear_window(self):
        for widget in self.master.winfo_children():
            widget.destroy()

    def register(self):
        name = self.name_entry.get().strip()
        dept = self.dept_entry.get().strip()
        session = self.session_entry.get().strip()
        password = self.password_entry.get().strip()
        if not name or not dept or not session or not password:
            messagebox.showerror('Error', 'All fields required!')
            return
        self.info = {'name': name, 'dept': dept, 'session': session, 'password': password}
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Set socket options for better reliability
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Set timeout to prevent hanging
            self.sock.settimeout(30.0)
            self.sock.connect((SERVER_HOST, SERVER_PORT))
            send_json(self.sock, {'type': 'REGISTER', 'data': self.info})
            resp = recv_json(self.sock)
            if resp.get('type') == 'REGISTER_SUCCESS':
                self.connected = True
                self.username = name
                # Remove timeout for persistent connection
                self.sock.settimeout(None)
                self.friend_manager = FriendManager(name)
                
                # Initialize TCP Reno simulation
                if RDT_AVAILABLE:
                    initialize_reno(name)
                    print(f"[CHAT] 🚀 TCP Reno simulation initialized for {name}")
                
                self.build_main()
                # Force reload friend list after building main interface
                self.friend_manager.reload()
                self.refresh_friendlist()
                threading.Thread(target=self.listen_server, daemon=True).start()
                
                # Start connection monitoring
                self.start_connection_monitoring()
            else:
                messagebox.showerror('Error', 'Registration failed!')
        except Exception as e:
            messagebox.showerror('Error', f'Could not connect: {e}')

    def login(self):
        name = self.name_entry.get().strip()
        password = self.password_entry.get().strip()
        if not name or not password:
            messagebox.showerror('Error', 'Name and password required!')
            return
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Set socket options for better reliability
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Set timeout to prevent hanging
            self.sock.settimeout(30.0)
            self.sock.connect((SERVER_HOST, SERVER_PORT))
            send_json(self.sock, {'type': 'LOGIN', 'name': name, 'password': password})
            resp = recv_json(self.sock)
            if resp.get('type') == 'LOGIN_SUCCESS':
                self.connected = True
                self.username = name
                self.stored_password = password  # Store for reconnection
                # Remove timeout for persistent connection
                self.sock.settimeout(None)
                self.friend_manager = FriendManager(name)
                
                # Initialize TCP Reno simulation
                if RDT_AVAILABLE:
                    initialize_reno(name)
                    print(f"[CHAT] 🚀 TCP Reno simulation initialized for {name}")
                
                # Clear any old notifications from previous sessions
                print("DEBUG: Clearing old notifications for new login session")
                self.notifications_home.clear()
                
                # Restore joined groups from server response, or fall back to local storage
                user_groups = resp.get('groups', [])
                if user_groups:
                    self.joined_groups = set(user_groups)
                else:
                    # Fallback: Load from local storage
                    self.joined_groups = self.load_joined_groups()
                
                self.build_main()
                self.refresh_friendlist()
                # Force reload friend list to ensure fresh data
                print(f"DEBUG: Force reloading friend list after login for {name}")
                self.friend_manager.reload()
                self.refresh_friendlist()
                self.listener_thread = threading.Thread(target=self.listen_server, daemon=True)
                self.listener_thread.start()
                
                # Start connection monitoring
                self.start_connection_monitoring()
            else:
                messagebox.showerror('Error', resp.get('reason', 'Login failed!'))
        except Exception as e:
            messagebox.showerror('Error', f'Could not connect: {e}')

    def check_connection(self):
        """Check if the socket connection is still valid"""
        if not self.sock:
            return False
        try:
            self.sock.getpeername()
            return True
        except socket.error:
            return False

    def reconnect(self):
        """Attempt to reconnect to the server"""
        if not hasattr(self, 'username') or not self.username:
            messagebox.showerror('Reconnection Failed', 'No username available for reconnection.')
            return False
        
        try:
            # Close existing socket if any
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
            
            # Create new socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.settimeout(30.0)
            self.sock.connect((SERVER_HOST, SERVER_PORT))
            
            # Try to login again with stored credentials
            if hasattr(self, 'stored_password'):
                send_json(self.sock, {'type': 'LOGIN', 'name': self.username, 'password': self.stored_password})
                resp = recv_json(self.sock)
                if resp.get('type') == 'LOGIN_SUCCESS':
                    self.connected = True
                    self.sock.settimeout(None)
                    
                    # Restart listener thread
                    if hasattr(self, 'listener_thread') and self.listener_thread and self.listener_thread.is_alive():
                        self.connected = False
                        self.listener_thread.join(timeout=1)
                    
                    self.listener_thread = threading.Thread(target=self.listen_server, daemon=True)
                    self.listener_thread.start()
                    
                    messagebox.showinfo('Reconnected', 'Successfully reconnected to server!')
                    return True
                else:
                    messagebox.showerror('Reconnection Failed', 'Failed to authenticate with server.')
                    return False
            else:
                messagebox.showerror('Reconnection Failed', 'No stored credentials for automatic reconnection.')
                return False
                
        except Exception as e:
            messagebox.showerror('Reconnection Failed', f'Could not reconnect: {e}')
            return False

    def start_connection_monitoring(self):
        """Start periodic connection monitoring"""
        def monitor_connection():
            while self.connected:
                try:
                    time.sleep(self.connection_check_interval)
                    
                    # Check if connection is still alive
                    if self.connected and not self.check_connection():
                        print("[MONITOR] Connection lost, attempting to reconnect...")
                        
                        # Try to reconnect
                        if self.attempt_reconnection():
                            print("[MONITOR] Successfully reconnected")
                            # Restart listener thread if needed
                            if not (hasattr(self, 'listener_thread') and 
                                   self.listener_thread and self.listener_thread.is_alive()):
                                self.listener_thread = threading.Thread(target=self.listen_server, daemon=True)
                                self.listener_thread.start()
                        else:
                            print("[MONITOR] Failed to reconnect, showing user notification")
                            self.master.after(0, lambda: messagebox.showwarning(
                                'Connection Lost', 
                                'Connection to server was lost. Please try logging out and logging back in.'))
                            break
                            
                except Exception as e:
                    print(f"[MONITOR] Error in connection monitoring: {e}")
                    break
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_connection, daemon=True)
        monitor_thread.start()

    def send_heartbeat(self):
        """Send a heartbeat to keep connection alive"""
        try:
            if self.connected and self.sock:
                send_json(self.sock, {'type': 'PING'})
                self.last_activity = time.time()
        except Exception:
            pass  # Heartbeat failed, will be caught by connection monitoring

    def build_main(self):
        self.clear_window()
        self.main_frame = tk.Frame(self.master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Left: Friend List (now with images)
        left_frame = tk.Frame(self.main_frame, width=180)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(left_frame, text='Friend List:', font=('Arial', 11, 'bold')).pack(pady=(10,0))
        self.friendlist_frame = tk.Frame(left_frame)
        self.friendlist_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        tk.Button(left_frame, text='Refresh Status', command=self.refresh_status).pack(pady=2, fill=tk.X, padx=5)
        tk.Button(left_frame, text='Logout', command=self.logout).pack(pady=2, fill=tk.X, padx=5)

        # Center: Main content (now used for chat)
        center_frame = tk.Frame(self.main_frame)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Profile frame (top)
        profile_frame = tk.Frame(center_frame)
        profile_frame.pack(anchor='nw', padx=5, pady=5, fill=tk.X)
        self.profile_pic_path = f'profile_{self.username}.png'
        self.profile_img = None
        
        # Load profile picture if PIL is available
        if PIL_AVAILABLE:
            try:
                if os.path.exists(self.profile_pic_path):
                    pil_img = Image.open(self.profile_pic_path)
                else:
                    pil_img = Image.open('default_dp.png')
                pil_img.thumbnail((64, 64))
                self.profile_img = ImageTk.PhotoImage(pil_img)
                tk.Label(profile_frame, image=self.profile_img).pack(side=tk.LEFT, padx=(0,8))
            except Exception:
                try:
                    pil_img = Image.open('default_dp.png')
                    pil_img.thumbnail((64, 64))
                    self.profile_img = ImageTk.PhotoImage(pil_img)
                    tk.Label(profile_frame, image=self.profile_img).pack(side=tk.LEFT, padx=(0,8))
                except Exception:
                    tk.Label(profile_frame, text='[No Image]').pack(side=tk.LEFT, padx=(0,8))
        else:
            tk.Label(profile_frame, text='[Profile]').pack(side=tk.LEFT, padx=(0,8))
            
        tk.Label(profile_frame, text=self.username, font=('Arial', 16, 'bold')).pack(side=tk.LEFT)
        tk.Button(profile_frame, text='Edit Profile', command=self.edit_profile).pack(side=tk.LEFT, padx=10)
        # User/Group controls
        btns_frame = tk.Frame(center_frame)
        btns_frame.pack(anchor='nw', padx=5, pady=5, fill=tk.X)
        tk.Button(btns_frame, text='Refresh Friends', command=self.request_user_list).pack(side=tk.LEFT, padx=2)
        tk.Button(btns_frame, text='Find Friend', command=self.find_friend).pack(side=tk.LEFT, padx=2)
        tk.Button(btns_frame, text='Create Group', command=self.create_group).pack(side=tk.LEFT, padx=2)
        
        # RDT Stats button (only if RDT is available)
        if RDT_AVAILABLE:
            tk.Button(btns_frame, text='📊 Reno Stats', command=self.show_rdt_stats, bg='lightblue').pack(side=tk.LEFT, padx=2)
            tk.Button(btns_frame, text='⚡ Toggle Reno', command=self.toggle_rdt_simulation, bg='yellow').pack(side=tk.LEFT, padx=2)
            tk.Button(btns_frame, text='🔄 Reset Stats', command=self.reset_reno_stats, bg='orange').pack(side=tk.LEFT, padx=2)
            tk.Button(btns_frame, text='📈 CWND Graph', command=self.show_cwnd_graph, bg='lightgreen').pack(side=tk.LEFT, padx=2)

        # Chat area (shared for private/group) - Split into info and chat sections
        
        # Upper section: Friend/Group information
        self.info_frame = tk.Frame(center_frame, bg='#F0F8FF', relief='ridge', bd=2)
        self.info_frame.pack(fill=tk.X, padx=5, pady=(5, 2))
        
        # Info area content (initially empty, populated when chat is opened)
        self.info_content_frame = tk.Frame(self.info_frame, bg='#F0F8FF')
        self.info_content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Default info label
        self.default_info_label = tk.Label(self.info_content_frame, 
                                          text='Select a friend or group to view information',
                                          font=('Arial', 11), fg='gray', bg='#F0F8FF')
        self.default_info_label.pack()
        
        # Lower section: Chat area
        self.chat_area = scrolledtext.ScrolledText(center_frame, state='disabled', height=12)
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 5))
        self.msg_entry = tk.Entry(center_frame)
        self.msg_entry.pack(fill=tk.X, padx=5, pady=5)
        self.msg_entry.bind('<Return>', self.send_message)
        self.send_file_btn = tk.Button(center_frame, text='Send File', command=self.send_file_to_current)
        self.send_file_btn.pack(pady=5)
        self.current_chat = None  # (type, name) where type is 'private' or 'group'

        # Right: Notifications and Joined Groups (unchanged)
        notif_frame = tk.Frame(self.main_frame)
        notif_frame.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Label(
            notif_frame,
            text='Notifications:',
            fg='red',
            font=('Arial', 10, 'bold'),
            justify='center'
        ).pack(anchor='center', padx=5, pady=(5,0), fill='x')
        self.notification_listbox = tk.Listbox(notif_frame, fg='red', activestyle='dotbox', width=32, height=5)
        self.notification_listbox.pack(anchor='e', padx=5, pady=(0,5))
        self.notification_listbox.bind('<Double-Button-1>', self.handle_notification_click)
        # Clear any existing notifications when building main interface
        self.notification_listbox.delete(0, tk.END)
        # Only initialize if not already set
        if not hasattr(self, 'notifications_home'):
            self.notifications_home = {}  # sender -> message

        # Joined Groups List
        tk.Label(
            notif_frame,
            text='Joined Groups:',
            font=('Arial', 10, 'bold'),
            justify='center'
        ).pack(anchor='center', padx=5, pady=(10,0), fill='x')
        self.joined_groups_listbox = tk.Listbox(notif_frame, width=32, height=5)
        self.joined_groups_listbox.pack(anchor='e', padx=5, pady=(0,5))
        self.joined_groups_listbox.bind('<Double-Button-1>', self.open_group_chat)
        
        # Only initialize joined_groups if not already set (e.g., from login response)
        if not hasattr(self, 'joined_groups'):
            self.joined_groups = set()
        self.refresh_joined_groups()

        self.request_user_list()  # Always request latest online info from server
        # self.refresh_friendlist() will be called after LIST_RESPONSE

    def open_group_chat(self, event):
        """Open a group chat in the main chat area"""
        import json
        import os
        
        selection = self.joined_groups_listbox.curselection()
        if not selection:
            return
        
        group_name = self.joined_groups_listbox.get(selection[0])
        
        # Set up the main chat area for this group
        self.current_chat = ('group', group_name)
        
        # Clear and populate the group information section
        self.update_group_info_section(group_name)
        
        # Clear the chat area and load group history
        self.chat_area.config(state='normal')
        self.chat_area.delete(1.0, tk.END)
        
        # Load group chat history
        group_history_file = f"group_chat_{group_name}.json"
        if os.path.exists(group_history_file):
            with open(group_history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        arr = json.loads(line)
                        sender = arr[0] if len(arr) > 0 else ''
                        msg = arr[1] if len(arr) > 1 else ''
                        align = arr[2] if len(arr) > 2 else 'left'
                        is_file = arr[3] if len(arr) > 3 else False
                        filename = arr[4] if len(arr) > 4 else None
                        filedata = arr[5] if len(arr) > 5 else None
                        timestamp = arr[6] if len(arr) > 6 else None
                        
                        if is_file and filename and filedata:
                            self.display_file_in_main(sender, filename, filedata, align=align, timestamp=timestamp)
                        else:
                            # For group messages, show sender without the group name if it's our own message
                            if sender == self.username and align == 'right':
                                display_sender = f'You (Group {group_name})'
                            else:
                                display_sender = f'{sender} (Group {group_name})'
                            self.display_message_in_main(display_sender, msg, align=align, timestamp=timestamp)
                    except Exception:
                        continue
        else:
            # Add initial group join message if no history
            self.chat_area.insert(tk.END, f'--- Joined group chat: {group_name} ---\n')
        
        # Load any pending group messages if available
        if hasattr(self, '_pending_group_messages'):
            for msg in self._pending_group_messages:
                if group_name in msg:
                    self.chat_area.insert(tk.END, msg + '\n')
        
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)
        
        # Update group name for sending messages
        self.group_name = group_name
    
    def open_group_chat_in_main(self, group_name):
        """Open a specific group chat in the main area (helper function for notifications)"""
        # Set up the main chat area for this group
        self.current_chat = ('group', group_name)
        
        # Clear and populate the group information section
        self.update_group_info_section(group_name)
        
        # Clear the chat area and load group history
        self.chat_area.config(state='normal')
        self.chat_area.delete(1.0, tk.END)
        
        # Load group chat history
        group_history_file = f"group_chat_{group_name}.json"
        if os.path.exists(group_history_file):
            with open(group_history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        arr = json.loads(line)
                        sender = arr[0] if len(arr) > 0 else ''
                        msg = arr[1] if len(arr) > 1 else ''
                        align = arr[2] if len(arr) > 2 else 'left'
                        is_file = arr[3] if len(arr) > 3 else False
                        filename = arr[4] if len(arr) > 4 else None
                        filedata = arr[5] if len(arr) > 5 else None
                        timestamp = arr[6] if len(arr) > 6 else None
                        
                        if is_file and filename and filedata:
                            self.display_file_in_main(sender, filename, filedata, align=align, timestamp=timestamp)
                        else:
                            # For group messages, show sender without the group name if it's our own message
                            if sender == self.username and align == 'right':
                                display_sender = f'You (Group {group_name})'
                            else:
                                display_sender = f'{sender} (Group {group_name})'
                            self.display_message_in_main(display_sender, msg, align=align, timestamp=timestamp)
                    except Exception:
                        continue
        else:
            # Add initial group join message if no history
            self.chat_area.insert(tk.END, f'--- Joined group chat: {group_name} ---\n')
        
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)
        
        # Update group name for sending messages
        self.group_name = group_name
    
    def update_group_info_section(self, group_name):
        """Update the upper info section with group information"""
        # Clear existing content
        for widget in self.info_content_frame.winfo_children():
            widget.destroy()
        
        # Load group information from groups.json
        group_info = {'admin': 'Unknown', 'members': [], 'description': ''}
        try:
            with open(get_data_path('groups.json'), 'r') as f:
                groups_data = json.load(f)
                if group_name in groups_data:
                    group_info = groups_data[group_name]
        except Exception:
            pass
        
        # Create info layout
        info_main_frame = tk.Frame(self.info_content_frame, bg='#F0F8FF')
        info_main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side: Group icon
        left_frame = tk.Frame(info_main_frame, bg='#F0F8FF')
        left_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        # Group icon
        icon_label = tk.Label(left_frame, text='👥', font=('Arial', 40), bg='#F0F8FF')
        icon_label.pack()
        
        # Right side: Group information
        right_frame = tk.Frame(info_main_frame, bg='#F0F8FF')
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Group details
        tk.Label(right_frame, text=f"Group: {group_name}", 
                font=('Arial', 16, 'bold'), bg='#F0F8FF', fg='#2C3E50').pack(anchor='w')
        
        tk.Label(right_frame, text=f"Admin: {group_info.get('admin', 'Unknown')}", 
                font=('Arial', 12), bg='#F0F8FF', fg='#34495E').pack(anchor='w', pady=(5, 0))
        
        members_count = len(group_info.get('members', []))
        tk.Label(right_frame, text=f"Members: {members_count}", 
                font=('Arial', 12), bg='#F0F8FF', fg='#34495E').pack(anchor='w', pady=(2, 0))
        
        # Group description if available
        description = group_info.get('description', '').strip()
        if description:
            tk.Label(right_frame, text=f"Description: {description}", 
                    font=('Arial', 11), bg='#F0F8FF', fg='#7F8C8D', 
                    wraplength=300, justify='left').pack(anchor='w', pady=(5, 0))
        
        # Add Member button for group members
        if hasattr(self, 'username') and self.username in group_info.get('members', []):
            button_frame = tk.Frame(right_frame, bg='#F0F8FF')
            button_frame.pack(anchor='w', pady=(10, 0))
            
            add_member_btn = tk.Button(button_frame, text='+ Add Member', 
                                     command=lambda: self.show_add_member_dialog(group_name),
                                     bg='#17A2B8', fg='white', font=('Arial', 10, 'bold'),
                                     relief='raised', bd=2, cursor='hand2',
                                     activebackground='#138496', activeforeground='white')
            add_member_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            # Leave Group button (only if not admin)
            is_admin = group_info.get('admin') == self.username
            if not is_admin:
                leave_group_btn = tk.Button(button_frame, text='Leave Group', 
                                           command=lambda: self.show_leave_group_dialog(group_name),
                                           bg='#DC3545', fg='white', font=('Arial', 10, 'bold'),
                                           relief='raised', bd=2, cursor='hand2',
                                           activebackground='#C82333', activeforeground='white')
                leave_group_btn.pack(side=tk.LEFT)
    
    def reset_info_section(self):
        """Reset the info section to default state"""
        # Clear existing content
        for widget in self.info_content_frame.winfo_children():
            widget.destroy()
        
        # Show default message
        self.default_info_label = tk.Label(self.info_content_frame, 
                                          text='Select a friend or group to view information',
                                          font=('Arial', 11), fg='gray', bg='#F0F8FF')
        self.default_info_label.pack(expand=True)

    def refresh_joined_groups(self):
        # Update the joined groups listbox
        if not hasattr(self, 'joined_groups_listbox'):
            return
        self.joined_groups_listbox.delete(0, tk.END)
        for g in sorted(self.joined_groups):
            self.joined_groups_listbox.insert(tk.END, g)

    def save_joined_groups(self):
        """Save joined groups to local file as backup"""
        if hasattr(self, 'username') and hasattr(self, 'joined_groups'):
            try:
                import json
                groups_file = f"joined_groups_{self.username}.json"
                with open(groups_file, 'w') as f:
                    json.dump(list(self.joined_groups), f)
            except Exception:
                pass  # Fail silently

    def load_joined_groups(self):
        """Load joined groups from local file as backup"""
        if hasattr(self, 'username'):
            try:
                import json
                groups_file = f"joined_groups_{self.username}.json"
                if os.path.exists(groups_file):
                    with open(groups_file, 'r') as f:
                        groups_list = json.load(f)
                        return set(groups_list)
            except Exception:
                pass  # Fail silently
        return set()

    def add_joined_group(self, group_name):
        if not hasattr(self, 'joined_groups'):
            self.joined_groups = set()
        self.joined_groups.add(group_name)
        self.refresh_joined_groups()
        self.save_joined_groups()  # Save to local file

    def remove_joined_group(self, group_name):
        if hasattr(self, 'joined_groups') and group_name in self.joined_groups:
            self.joined_groups.remove(group_name)
            self.refresh_joined_groups()
            self.save_joined_groups()  # Save to local file

    def edit_profile(self):
        from tkinter import filedialog
        
        win = tk.Toplevel(self.master)
        win.title('Edit Profile')
        win.geometry('350x350')
        tk.Label(win, text='Edit Profile', font=('Arial', 12, 'bold')).pack(pady=10)
        tk.Label(win, text='Name:').pack()
        name_entry = tk.Entry(win)
        name_entry.insert(0, self.username)
        name_entry.pack()
        tk.Label(win, text='Department:').pack()
        dept_entry = tk.Entry(win)
        dept_entry.insert(0, self.info.get('dept', ''))
        dept_entry.pack()
        tk.Label(win, text='Session:').pack()
        session_entry = tk.Entry(win)
        session_entry.insert(0, self.info.get('session', ''))
        session_entry.pack()
        tk.Label(win, text='Password:').pack()
        password_entry = tk.Entry(win, show='*')
        password_entry.insert(0, self.info.get('password', ''))
        password_entry.pack()
        
        # Profile picture selection
        img_frame = tk.Frame(win)
        img_frame.pack(pady=10)
        img_label = tk.Label(img_frame, text='No image selected')
        img_label.pack()
        selected_img_path = [self.profile_pic_path if os.path.exists(self.profile_pic_path) else None]
        
        def select_img():
            if not PIL_AVAILABLE:
                messagebox.showwarning('Warning', 'PIL/Pillow not installed. Image selection disabled.')
                return
                
            path = filedialog.askopenfilename(filetypes=[('Image Files', '*.png;*.jpg;*.jpeg;*.gif')])
            if path:
                selected_img_path[0] = path
                img_label.config(text=os.path.basename(path))
        
        tk.Button(img_frame, text='Select Profile Picture', command=select_img).pack()
        
        def save_profile():
            new_name = name_entry.get().strip()
            new_dept = dept_entry.get().strip()
            new_session = session_entry.get().strip()
            new_password = password_entry.get().strip()
            if not new_name or not new_dept or not new_session or not new_password:
                messagebox.showerror('Error', 'All fields required!')
                return
            
            # Save profile picture
            if selected_img_path[0] and PIL_AVAILABLE:
                try:
                    img = Image.open(selected_img_path[0])
                    img.thumbnail((128, 128))
                    img.save(f'profile_{self.username}.png')
                except Exception as e:
                    messagebox.showerror('Error', f'Failed to save image: {e}')
                    return
            
            # Update info locally
            self.info = {'name': new_name, 'dept': new_dept, 'session': new_session, 'password': new_password}
            
            # Send update to server (if needed)
            try:
                send_json(self.sock, {'type': 'EDIT_PROFILE', 'name': self.username, 'new_info': self.info})
            except Exception:
                pass
                
            messagebox.showinfo('Success', 'Profile updated!')
            win.destroy()
            self.build_main()
        
        tk.Button(win, text='Save', command=save_profile).pack(pady=10)

    def show_rdt_stats(self):
        """Show TCP Reno transmission statistics"""
        if not RDT_AVAILABLE:
            messagebox.showwarning('TCP Reno Stats', 'TCP Reno simulation is not available')
            return
            
        try:
            stats = get_reno_stats()
            
            win = tk.Toplevel(self.master)
            win.title('📊 TCP Reno Algorithm Statistics')
            win.geometry('500x450')
            win.configure(bg='white')
            
            # Title
            title_label = tk.Label(win, text='🚀 TCP Reno Performance Statistics', 
                                 font=('Arial', 14, 'bold'), bg='white', fg='navy')
            title_label.pack(pady=15)
            
            # Stats frame
            stats_frame = tk.Frame(win, bg='white')
            stats_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
            
            # Create stats display
            stats_text = tk.Text(stats_frame, height=20, width=60, font=('Courier', 9))
            stats_text.pack(fill=tk.BOTH, expand=True)
            
            # Format TCP Reno statistics
            stats_display = f"""
╔══════════════════════════════════════════════════════════════╗
║                    TCP RENO ALGORITHM                        ║
╠══════════════════════════════════════════════════════════════╣
║ User: {self.username:<50} ║
║                                                              ║
║ � Congestion Control State:                                ║
║    • Current CWND: {stats.get('cwnd', 0):<35.2f} ║
║    • Slow Start Threshold: {stats.get('ssthresh', 0):<26.2f} ║
║    • Current State: {stats.get('state', 'N/A'):<33} ║
║                                                              ║
║ 📈 Transmission Statistics:                                 ║
║    • Packets Sent: {stats.get('packets_sent', 0):<35} ║
║    • Total Retransmissions: {stats.get('retransmissions', 0):<26} ║
║    • Fast Retransmits: {stats.get('fast_retransmits', 0):<30} ║
║    • Timeouts: {stats.get('timeouts', 0):<41} ║
║                                                              ║
║ � Network Conditions:                                      ║
║    • Current Loss Rate: {stats.get('loss_rate', 0)*100:<28.1f}% ║
║    • Algorithm: {stats.get('algorithm', 'Unknown'):<41} ║
║                                                              ║
║ 🎯 Performance Metrics:                                     ║
║    • Retransmission Ratio: {(stats.get('retransmissions', 0) / max(stats.get('packets_sent', 1), 1) * 100):<25.1f}% ║
║    • Fast Recovery Usage: {(stats.get('fast_retransmits', 0) / max(stats.get('retransmissions', 1), 1) * 100):<27.1f}% ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

🔍 TCP Reno Algorithm Explanation:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 SLOW START Phase:
   • CWND grows exponentially (doubles every RTT)
   • Continues until CWND ≥ SSTHRESH
   • Formula: CWND += 1 for each ACK

📍 CONGESTION AVOIDANCE Phase:
   • CWND grows linearly (+1 per RTT)
   • Formula: CWND += 1/CWND for each ACK
   • More conservative growth

� FAST RETRANSMIT:
   • Triggered by 3 duplicate ACKs
   • Immediately retransmits lost packet
   • Avoids timeout delay

📍 FAST RECOVERY:
   • Entered after Fast Retransmit
   • SSTHRESH = CWND/2, CWND = SSTHRESH + 3
   • Inflates window for each additional dup ACK
   • Exits on new ACK → Congestion Avoidance

💡 Real-time Monitoring:
   • Watch terminal during message/file sending
   • See actual congestion control decisions
   • Different data sizes trigger different behaviors
"""
            
            stats_text.insert(tk.END, stats_display)
            stats_text.config(state='disabled')
            
            # Buttons frame
            btn_frame = tk.Frame(win, bg='white')
            btn_frame.pack(pady=10)
            
            # Refresh button
            def refresh_stats():
                new_stats = get_reno_stats()
                stats_text.config(state='normal')
                stats_text.delete(1.0, tk.END)
                
                # Update display with new stats
                updated_display = stats_display.replace(
                    f"Current CWND: {stats.get('cwnd', 0):<35.2f}",
                    f"Current CWND: {new_stats.get('cwnd', 0):<35.2f}"
                ).replace(
                    f"Current State: {stats.get('state', 'N/A'):<33}",
                    f"Current State: {new_stats.get('state', 'N/A'):<33}"
                ).replace(
                    f"Packets Sent: {stats.get('packets_sent', 0):<35}",
                    f"Packets Sent: {new_stats.get('packets_sent', 0):<35}"
                ).replace(
                    f"Fast Retransmits: {stats.get('fast_retransmits', 0):<30}",
                    f"Fast Retransmits: {new_stats.get('fast_retransmits', 0):<30}"
                )
                
                stats_text.insert(tk.END, updated_display)
                stats_text.config(state='disabled')
                
            refresh_btn = tk.Button(btn_frame, text='🔄 Refresh Stats', command=refresh_stats, 
                                  bg='lightblue', font=('Arial', 10, 'bold'))
            refresh_btn.pack(side=tk.LEFT, padx=5)
            
            # Reset stats button
            def reset_stats():
                if messagebox.askyesno('Reset Statistics', 'Are you sure you want to reset all TCP Reno statistics?'):
                    reset_reno_stats()
                    refresh_stats()
                    messagebox.showinfo('Reset Complete', 'TCP Reno statistics have been reset.')
            
            reset_btn = tk.Button(btn_frame, text='🔄 Reset Stats', command=reset_stats, 
                                bg='orange', font=('Arial', 10, 'bold'))
            reset_btn.pack(side=tk.LEFT, padx=5)
            
            close_btn = tk.Button(btn_frame, text='Close', command=win.destroy, 
                                bg='lightcoral', font=('Arial', 10))
            close_btn.pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror('Error', f'Failed to get TCP Reno stats: {e}')

    def toggle_rdt_simulation(self):
        """Toggle TCP Reno simulation on/off"""
        if not RDT_AVAILABLE:
            messagebox.showwarning('TCP Reno Toggle', 'TCP Reno simulation is not available')
            return
            
        try:
            enabled = toggle_reno()
            status = "ENABLED" if enabled else "DISABLED"
            messagebox.showinfo('TCP Reno Toggle', f'TCP Reno simulation is now {status}')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to toggle TCP Reno: {e}')

    def reset_reno_stats(self):
        """Reset TCP Reno statistics"""
        if not RDT_AVAILABLE:
            messagebox.showwarning('Reset Stats', 'TCP Reno simulation is not available')
            return
            
        try:
            success = reset_reno_stats()
            if success:
                messagebox.showinfo('Reset Complete', 'TCP Reno statistics have been reset.')
            else:
                messagebox.showwarning('Reset Failed', 'TCP Reno controller not initialized.')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to reset stats: {e}')

    def show_cwnd_graph(self):
        """Show TCP Reno CWND automated graph"""
        if not RDT_AVAILABLE:
            messagebox.showwarning('CWND Graph', 'TCP Reno simulation is not available')
            return
            
        try:
            # Check if matplotlib is available
            try:
                import matplotlib.pyplot as plt
                import matplotlib.animation as animation
            except ImportError:
                messagebox.showerror('Graph Error', 
                    'Matplotlib is required for graphing.\n\n'
                    'Please install it with:\n'
                    'pip install matplotlib\n\n'
                    'Then restart the application.')
                return
            
            # Start recording if not already started
            start_graph_recording()
            
            # Show the graph window
            graph_window = show_reno_graph(self.master)
            
            if graph_window:
                # Show instructions dialog
                instructions = """
🚀 TCP Reno CWND Graph Instructions:

📊 Real-time Monitoring:
• The graph shows Congestion Window (CWND) evolution
• Blue line: Current CWND value
• Red dashed line: Slow Start Threshold (SSTHRESH)
• Different colors mark algorithm states

📈 Graph Features:
• ▶️ Start/Stop recording data points
• 🗑️ Clear all graph data
• Real-time updates during message/file transmission

🎯 How to Generate Data:
• Send messages or files to see CWND changes
• Larger files create more interesting patterns
• Different network conditions trigger different behaviors

📍 Algorithm States:
• Green triangles: Slow Start phase
• Blue squares: Congestion Avoidance phase  
• Red X marks: Fast Recovery phase
• Annotations show special events

💡 Tips:
• Send multiple files to see complete algorithm behavior
• Watch for Fast Retransmit and Timeout events
• Graph automatically saves data between sessions
                """
                
                messagebox.showinfo('CWND Graph Help', instructions)
                
                messagebox.showinfo('Graph Ready', 
                    '📈 TCP Reno CWND Graph is now active!\n\n'
                    '✅ Start sending messages or files to see the graph update\n'
                    '✅ The graph records data automatically during transmissions\n'
                    '✅ Try sending different sized files for varied patterns')
            else:
                messagebox.showwarning('Graph Error', 'Could not create graph window')
                
        except Exception as e:
            messagebox.showerror('Error', f'Failed to show CWND graph: {e}')

    # Deprecated: All private chats now use the main chat area
    def open_private_chat(self, user):
        self.open_chat_in_main(user)

    def send_group_message(self, event=None):
        msg = self.group_msg_entry.get().strip()
        if not msg or not self.group_name:
            return
        send_json(self.sock, {'type': 'GROUP_MESSAGE', 'group_name': self.group_name, 'from': self.username, 'msg': msg})
        self.display_group_message(f'You (Group {self.group_name}): {msg}')
        self.group_msg_entry.delete(0, tk.END)

    def display_group_message(self, msg):
        """Display group message in the main chat area"""
        if hasattr(self, 'chat_area'):
            self.chat_area.config(state='normal')
            self.chat_area.insert(tk.END, msg + '\n')
            self.chat_area.config(state='disabled')
            self.chat_area.see(tk.END)
        else:
            # Fallback - store message for later display
            if not hasattr(self, '_pending_group_messages'):
                self._pending_group_messages = []
            self._pending_group_messages.append(msg)

    def send_file_to_group(self):
        import os
        import json
        import base64
        from tkinter import filedialog
        
        # Check connection first
        if not self.connected or not self.sock:
            messagebox.showerror('Connection Error', 'Not connected to server. Please login again.')
            return
        
        if not hasattr(self, 'current_chat') or not self.current_chat or self.current_chat[0] != 'group':
            messagebox.showinfo('Info', 'Please select a group chat first.')
            return
            
        group_name = self.current_chat[1]
        file_path = filedialog.askopenfilename(title='Select file to send')
        if not file_path:
            return
            
        # Check file size (limit to 10MB for safety)
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            messagebox.showerror('File Too Large', 'File size must be less than 10MB.')
            return
        
        try:
            # Show progress for large files
            if file_size > 1024 * 1024:  # 1MB
                messagebox.showinfo('Sending File', f'Sending {os.path.basename(file_path)}...\nPlease wait.')
            
            with open(file_path, 'rb') as f:
                data = f.read()
            encoded = base64.b64encode(data).decode()
            filename = os.path.basename(file_path)
            current_time = datetime.datetime.now()
            timestamp = current_time.isoformat()
            
            msg = {'type': 'GROUP_MEDIA', 'group_name': group_name, 'from': self.username, 'filename': filename, 'data': encoded, 'timestamp': timestamp}
            
            # Verify connection before sending
            if not self.check_connection():
                print("[GROUP_FILE_SEND] Connection lost before sending, attempting reconnection...")
                if not self.reconnect():
                    raise ConnectionError("Failed to reconnect before sending file")
            
            # Try to send the message
            send_json(self.sock, msg)
            
            # Verify connection is still alive after sending
            if not self.check_connection():
                print("[GROUP_FILE_SEND] WARNING: Connection may have been lost during file transmission")
                # Try to reconnect silently
                if self.reconnect():
                    print("[GROUP_FILE_SEND] Successfully reconnected after file transmission")
                else:
                    print("[GROUP_FILE_SEND] Failed to reconnect after file transmission")
                    messagebox.showwarning('Connection Warning', 
                        f'File "{filename}" was sent successfully to group "{group_name}", but connection was lost.\n'
                        'You may need to reconnect manually if you experience issues.')
            
            # Display file in chat for sender
            self.display_file_in_main(self.username, filename, encoded, align='right')
            
            # Save to group chat history with timestamp
            group_history_file = f"group_chat_{group_name}.json"
            arr = [self.username, '', 'right', True, filename, encoded, timestamp]
            with open(group_history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(arr) + '\n')
            
            # Show success message for large files
            if file_size > 1024 * 1024:  # 1MB
                messagebox.showinfo('File Sent', f'{filename} sent successfully!')
                
        except ConnectionError as e:
            messagebox.showerror('Connection Error', 
                f'Failed to send file due to connection issue:\n{str(e)}\n\n'
                'Please check your connection and try again.')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to send file: {e}')
    def send_file(self, to_user):
        import os
        from tkinter import filedialog
        
        # Check connection first
        if not self.connected or not self.sock:
            messagebox.showerror('Connection Error', 'Not connected to server. Please login again.')
            return
        
        # Check if the user is a friend before sending file
        if not self.friend_manager.is_friend(to_user):
            messagebox.showwarning('Not Friends', f'You need to be friends with {to_user} to send files.\nSend a friend request first.')
            return
            
        file_path = filedialog.askopenfilename(title='Select file to send')
        if not file_path:
            return
            
        # Check file size (limit to 10MB for safety)
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            messagebox.showerror('File Too Large', 'File size must be less than 10MB.')
            return
            
        try:
            # Show progress for large files
            if file_size > 1024 * 1024:  # 1MB
                messagebox.showinfo('Sending File', f'Sending {os.path.basename(file_path)}...\nPlease wait.')
            
            with open(file_path, 'rb') as f:
                data = f.read()
            import base64
            encoded = base64.b64encode(data).decode()
            filename = os.path.basename(file_path)
            current_time = datetime.datetime.now()
            timestamp = current_time.isoformat()
            
            msg = {'type': 'MEDIA', 'to': to_user, 'from': self.username, 'filename': filename, 'data': encoded, 'timestamp': timestamp}
            
            # Verify connection before sending
            if not self.check_connection():
                print("[FILE_SEND] Connection lost before sending, attempting reconnection...")
                if not self.reconnect():
                    raise ConnectionError("Failed to reconnect before sending file")
            
            # Try to send the message
            send_json(self.sock, msg)
            
            # Verify connection is still alive after sending
            if not self.check_connection():
                print("[FILE_SEND] WARNING: Connection may have been lost during file transmission")
                # Try to reconnect silently
                if self.reconnect():
                    print("[FILE_SEND] Successfully reconnected after file transmission")
                else:
                    print("[FILE_SEND] Failed to reconnect after file transmission")
                    messagebox.showwarning('Connection Warning', 
                        f'File "{filename}" was sent successfully, but connection was lost.\n'
                        'You may need to reconnect manually if you experience issues.')
            
            # Display file in chat for sender
            self.display_file_in_main(self.username, filename, encoded, align='right', timestamp=timestamp)
            
            # Save to chat history with timestamp
            users = sorted([self.username, to_user])
            history_file = f"chat_{users[0]}_{users[1]}.json"
            arr = [self.username, '', 'right', True, filename, encoded, timestamp]
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(arr) + '\n')
            
            # Show success message for large files
            if file_size > 1024 * 1024:  # 1MB
                messagebox.showinfo('File Sent', f'{filename} sent successfully!')
                
        except ConnectionError as e:
            messagebox.showerror('Connection Error', 
                f'Failed to send file due to connection issue:\n{str(e)}\n\n'
                'Please check your connection and try again.')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to send file: {e}')

    def send_file_to_current(self):
        """Send file to current chat (private or group)"""
        if not self.current_chat:
            messagebox.showinfo('Info', 'Please select a chat first.')
            return
        
        chat_type, name = self.current_chat
        if chat_type == 'private':
            self.send_file(name)
        elif chat_type == 'group':
            self.send_file_to_group()
        else:
            messagebox.showinfo('Info', 'Unknown chat type.')

    def request_user_list(self):
        if self.connected:
            send_json(self.sock, {'type': 'LIST'})
            # Do not call refresh_friendlist here; wait for LIST_RESPONSE from server

    def find_friend(self):
        """Open a window to find and add friends from all registered users with profile pictures"""
        if not self.connected:
            messagebox.showinfo('Info', 'Please connect to the server first.')
            return
        
        # Create find friend window
        find_win = tk.Toplevel(self.master)
        find_win.title('Find Friend')
        find_win.geometry('500x600')
        find_win.resizable(False, False)
        
        tk.Label(find_win, text='Find Friends', font=('Arial', 14, 'bold')).pack(pady=10)
        tk.Label(find_win, text='All Registered Users:', font=('Arial', 10)).pack(pady=(10,5))
        
        # Search box
        search_frame = tk.Frame(find_win)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text='Search:').pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5,0))
        
        # Users frame with scrollbar (replacing listbox with custom frames)
        list_frame = tk.Frame(find_win)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create canvas and scrollbar for custom user items
        canvas = tk.Canvas(list_frame, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Request all users from server instead of reading local file
        all_users = []
        users_data = {}
        
        # First try: Get users from server
        server_success = False
        try:
            # Send request to server for user list
            send_json(self.sock, {'type': 'GET_ALL_USERS'})
            resp = recv_json(self.sock)
            
            if resp.get('type') == 'ALL_USERS_RESPONSE':
                users_data = resp.get('users', {})
                all_users = list(users_data.keys())
                server_success = True
                print(f"✅ Got {len(all_users)} users from server")
            elif resp.get('type') == 'ERROR':
                print(f"⚠️ Server error: {resp.get('message', 'Unknown error')}")
            else:
                print(f"⚠️ Unexpected server response: {resp}")
        except Exception as e:
            print(f"❌ Error getting users from server: {e}")
        
        # Second try: Fall back to local file if server failed
        if not server_success:
            try:
                with open(get_data_path('users.json'), 'r') as f:
                    users_data = json.load(f)
                    all_users = list(users_data.keys())
                    print(f"✅ Fallback: Got {len(all_users)} users from local file")
            except Exception as e2:
                # Third try: Use hardcoded default users as last resort
                print(f"⚠️ Local file also failed: {e2}")
                print("💡 Using default user list as fallback")
                users_data = {
                    "adib": {"name": "adib", "dept": "cse", "session": "2021-22"},
                    "habib": {"name": "habib", "dept": "eee", "session": "2021-22"},
                    "jim": {"name": "jim", "dept": "cse", "session": "2021-22"},
                    "sakib": {"name": "sakib", "dept": "cse", "session": "2021-22"}
                }
                all_users = list(users_data.keys())
                print(f"✅ Using default {len(all_users)} users")
                
                # Show info to user about the fallback
                tk.Label(find_win, text="Note: Using default user list (server/file unavailable)", 
                        fg='orange', font=('Arial', 9)).pack(pady=5)
        
        # Store user frames for selection
        user_frames = {}
        selected_user = [None]  # Use list to make it mutable in nested functions
        
        def create_user_item(user, user_info):
            """Create a user item with profile picture and info"""
            # Main user frame
            user_frame = tk.Frame(scrollable_frame, relief='solid', bd=1, bg='white')
            user_frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Load profile picture
            profile_img = None
            from PIL import Image, ImageTk
            img_path = f'profile_{user}.png'
            try:
                if os.path.exists(img_path):
                    pil_img = Image.open(img_path)
                else:
                    pil_img = Image.open('default_dp.png')
                pil_img.thumbnail((50, 50))
                profile_img = ImageTk.PhotoImage(pil_img)
            except Exception:
                try:
                    pil_img = Image.open('default_dp.png')
                    pil_img.thumbnail((50, 50))
                    profile_img = ImageTk.PhotoImage(pil_img)
                except Exception:
                    profile_img = None
            
            # Left side - Profile picture
            img_frame = tk.Frame(user_frame, bg='white')
            img_frame.pack(side=tk.LEFT, padx=10, pady=5)
            
            if profile_img:
                img_label = tk.Label(img_frame, image=profile_img, bg='white')
                img_label.image = profile_img  # Keep reference
                img_label.pack()
            else:
                tk.Label(img_frame, text='[No Image]', bg='white', 
                        font=('Arial', 8), fg='gray').pack()
            
            # Right side - User information
            info_frame = tk.Frame(user_frame, bg='white')
            info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=5)
            
            # Username
            dept = user_info.get('dept', 'Unknown')
            session = user_info.get('session', 'Unknown')
            status = " (Friend)" if self.friend_manager.is_friend(user) else ""
            
            tk.Label(info_frame, text=f"{user}{status}", 
                    font=('Arial', 12, 'bold'), bg='white', anchor='w').pack(anchor='w')
            tk.Label(info_frame, text=f"Department: {dept}", 
                    font=('Arial', 10), bg='white', anchor='w').pack(anchor='w')
            tk.Label(info_frame, text=f"Session: {session}", 
                    font=('Arial', 10), bg='white', anchor='w').pack(anchor='w')
            
            # Click handler for selection
            def on_click(event):
                # Clear previous selection
                for frame in user_frames.values():
                    frame.config(bg='white')
                    for child in frame.winfo_children():
                        child.config(bg='white')
                        for grandchild in child.winfo_children():
                            try:
                                grandchild.config(bg='white')
                            except:
                                pass
                
                # Highlight selected
                user_frame.config(bg='lightblue')
                img_frame.config(bg='lightblue')
                info_frame.config(bg='lightblue')
                for child in info_frame.winfo_children():
                    child.config(bg='lightblue')
                for child in img_frame.winfo_children():
                    try:
                        child.config(bg='lightblue')
                    except:
                        pass
                
                selected_user[0] = user
            
            # Bind click events
            user_frame.bind("<Button-1>", on_click)
            img_frame.bind("<Button-1>", on_click)
            info_frame.bind("<Button-1>", on_click)
            for child in info_frame.winfo_children():
                child.bind("<Button-1>", on_click)
            
            user_frames[user] = user_frame
            
            return user_frame
        
        def filter_users():
            """Filter users based on search query"""
            query = search_var.get().lower().strip()
            
            # Clear existing items
            for widget in scrollable_frame.winfo_children():
                widget.destroy()
            user_frames.clear()
            selected_user[0] = None
            
            for user in all_users:
                if user == self.username:  # Don't show current user
                    continue
                if not query or query in user.lower():
                    user_info = users_data.get(user, {})
                    create_user_item(user, user_info)
        
        # Initial population of users
        filter_users()
        
        search_var.trace('w', lambda *args: filter_users())
        
        # Buttons
        btn_frame = tk.Frame(find_win)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def send_friend_request():
            if not selected_user[0]:
                messagebox.showinfo('Info', 'Please select a user to send friend request.')
                return
            
            username = selected_user[0]
            
            if self.friend_manager.is_friend(username):
                messagebox.showinfo('Info', f'{username} is already your friend.')
                return
            
            if username == self.username:
                messagebox.showinfo('Info', 'You cannot add yourself as a friend.')
                return
            
            # Send friend request to server
            send_json(self.sock, {
                'type': 'FRIEND_REQUEST', 
                'from': self.username, 
                'to': username
            })
            messagebox.showinfo('Success', f'Friend request sent to {username}!')
        
        def refresh_users():
            """Refresh the user list from users.json"""
            try:
                with open(get_data_path('users.json'), 'r') as f:
                    new_users_data = json.load(f)
                    users_data.clear()
                    users_data.update(new_users_data)
                    all_users.clear()
                    all_users.extend(list(new_users_data.keys()))
                    filter_users()
            except Exception as e:
                messagebox.showerror('Error', f'Could not refresh users: {e}')
        
        def close_window():
            self.find_friend_window = None
            find_win.destroy()
        
        def simulate_friend_request():
            """Simulate receiving a friend request for testing"""
            if not selected_user[0]:
                messagebox.showinfo('Info', 'Please select a user to simulate a friend request from.')
                return
            
            username = selected_user[0]
            
            if username == self.username:
                messagebox.showinfo('Info', 'Cannot simulate friend request from yourself.')
                return
            
            # Simulate receiving a friend request
            self.add_home_notification(username, "sent you a friend request", is_friend_request=True)
            messagebox.showinfo('Test', f'Simulated friend request from {username}!\nCheck notifications panel.')
        
        tk.Button(btn_frame, text='Send Friend Request', command=send_friend_request).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text='Test Request (Demo)', command=simulate_friend_request).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text='Refresh', command=refresh_users).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text='Close', command=close_window).pack(side=tk.RIGHT, padx=5)
        
        # Handle window close event
        find_win.protocol("WM_DELETE_WINDOW", close_window)
        
        # Store references for updating from server response
        find_win.filter_users = filter_users
        
        # Store the window reference to update it when we get server response
        self.find_friend_window = find_win

    def create_group(self):
        """Create a new group and optionally invite friends"""
        if not self.connected:
            messagebox.showinfo('Info', 'Please connect to the server first.')
            return
        
        # Show group creation dialog
        self.show_group_creation_dialog()
    
    def show_group_creation_dialog(self):
        """Show dialog to create a new group with name and description"""
        create_win = tk.Toplevel(self.master)
        create_win.title('Create New Group')
        create_win.geometry('450x400')  # Increased height to ensure buttons are visible
        create_win.resizable(False, False)
        create_win.grab_set()
        
        # Center the window
        create_win.transient(self.master)
        
        # Main frame
        main_frame = tk.Frame(create_win)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text='Create New Group', 
                              font=('Arial', 16, 'bold'), fg='#2C3E50')
        title_label.pack(pady=(0, 15))
        
        # Group name section
        name_frame = tk.Frame(main_frame)
        name_frame.pack(fill=tk.X, pady=(0, 15))
        
        name_label = tk.Label(name_frame, text='Group Name *', 
                             font=('Arial', 12, 'bold'))
        name_label.pack(anchor='w')
        
        name_entry = tk.Entry(name_frame, font=('Arial', 11), width=35)
        name_entry.pack(fill=tk.X, pady=(5, 0))
        name_entry.focus()
        
        # Description section
        desc_frame = tk.Frame(main_frame)
        desc_frame.pack(fill=tk.X, pady=(0, 15))  # Changed from fill=tk.BOTH, expand=True
        
        desc_label = tk.Label(desc_frame, text='Short Description (Optional)', 
                             font=('Arial', 12, 'bold'))
        desc_label.pack(anchor='w')
        
        # Text area for description
        desc_text_frame = tk.Frame(desc_frame)
        desc_text_frame.pack(fill=tk.X, pady=(5, 0))  # Changed from fill=tk.BOTH, expand=True
        
        desc_text = tk.Text(desc_text_frame, height=4, width=35, font=('Arial', 10),  # Reduced height
                           wrap=tk.WORD, relief=tk.RIDGE, bd=1)
        desc_scrollbar = tk.Scrollbar(desc_text_frame, orient="vertical", command=desc_text.yview)
        desc_text.configure(yscrollcommand=desc_scrollbar.set)
        
        desc_text.pack(side="left", fill="both", expand=True)
        desc_scrollbar.pack(side="right", fill="y")
        
        # Character limit label
        char_label = tk.Label(desc_frame, text='(Max 200 characters)', 
                             font=('Arial', 9), fg='#7F8C8D')
        char_label.pack(anchor='w', pady=(2, 0))
        
        # Button frame - Make sure it's visible
        btn_frame = tk.Frame(main_frame, bg='#F8F9FA')  # Add background color to make it visible
        btn_frame.pack(fill=tk.X, pady=(20, 0))  # Increased top padding
        
        def create_group_action():
            group_name = name_entry.get().strip()
            description = desc_text.get("1.0", tk.END).strip()
            
            # Validate group name
            if not group_name:
                messagebox.showerror('Error', 'Group name is required!')
                name_entry.focus()
                return
            
            if len(group_name) < 2:
                messagebox.showerror('Error', 'Group name must be at least 2 characters long!')
                name_entry.focus()
                return
                
            if len(group_name) > 50:
                messagebox.showerror('Error', 'Group name cannot exceed 50 characters!')
                name_entry.focus()
                return
            
            # Validate description length
            if len(description) > 200:
                messagebox.showerror('Error', 'Description cannot exceed 200 characters!')
                desc_text.focus()
                return
            
            try:
                # Send create group request to server with description
                group_data = {
                    'type': 'CREATE_GROUP', 
                    'group_name': group_name, 
                    'creator': self.username
                }
                
                # Add description if provided
                if description:
                    group_data['description'] = description
                
                send_json(self.sock, group_data)
                
                # Close creation dialog
                create_win.destroy()
                
                # Show success message
                success_msg = f'Group "{group_name}" created successfully!\nYou are the admin.'
                if description:
                    success_msg += f'\n\nDescription: {description}'
                
                messagebox.showinfo('Success', success_msg)
                self.add_joined_group(group_name)
                
                # Show friend invitation dialog
                if self.friend_manager:
                    friends = self.friend_manager.get_all()
                    if friends:
                        self.show_invite_friends_dialog(group_name, friends)
                    else:
                        messagebox.showinfo('Info', 
                                          f'Group "{group_name}" created.\n\n'
                                          'You have no friends to invite yet.\n'
                                          'Add friends first through "Find Friend".')
                else:
                    messagebox.showinfo('Info', 
                                      f'Group "{group_name}" created.\n'
                                      'You can invite friends later.')
                    
            except Exception as e:
                messagebox.showerror('Error', f'Failed to create group: {e}')
        
        def cancel_action():
            create_win.destroy()
        
        # Add some spacing before buttons
        btn_spacer = tk.Frame(btn_frame, height=10)
        btn_spacer.pack(fill=tk.X)
        
        # Create button container for better control
        button_container = tk.Frame(btn_frame)
        button_container.pack(fill=tk.X, padx=10, pady=10)
        
        # Buttons with improved styling
        create_btn = tk.Button(button_container, text='Create', command=create_group_action,
                              bg='#28A745', fg='white', font=('Arial', 11, 'bold'),
                              width=12, height=2, relief=tk.RAISED, bd=2)
        create_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        cancel_btn = tk.Button(button_container, text='Cancel', command=cancel_action,
                              bg='#6C757D', fg='white', font=('Arial', 11),
                              width=12, height=2, relief=tk.RAISED, bd=2)
        cancel_btn.pack(side=tk.RIGHT)
        
        # Handle window close
        create_win.protocol("WM_DELETE_WINDOW", cancel_action)
        
        # Bind Enter key to create action
        def on_enter(event):
            if event.widget == desc_text:
                return  # Allow Enter in text area
            create_group_action()
        
        name_entry.bind('<Return>', on_enter)
        create_win.bind('<Return>', on_enter)
    
    def show_invite_friends_dialog(self, group_name, friends):
        """Show dialog to invite friends to a group"""
        invite_win = tk.Toplevel(self.master)
        invite_win.title(f'Invite Friends to {group_name}')
        invite_win.geometry('450x550')
        invite_win.resizable(False, False)
        invite_win.grab_set()
        
        # Center the window
        invite_win.transient(self.master)
        
        # Main frame
        main_frame = tk.Frame(invite_win)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Title
        title_label = tk.Label(main_frame, text=f'Invite Friends to "{group_name}"', 
                              font=('Arial', 16, 'bold'), fg='#2C3E50')
        title_label.pack(pady=(0, 10))
        
        # Subtitle
        subtitle_label = tk.Label(main_frame, text='Select friends you want to invite to this group', 
                                 font=('Arial', 11), fg='#7F8C8D')
        subtitle_label.pack(pady=(0, 20))
        
        # Friends list with checkboxes
        list_frame = tk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Create a label frame for better organization
        friends_label_frame = tk.LabelFrame(list_frame, text=f"Available Friends ({len(friends)})", 
                                           font=('Arial', 10, 'bold'), fg='#2C3E50')
        friends_label_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable frame for friends
        canvas = tk.Canvas(friends_label_frame)
        scrollbar = tk.Scrollbar(friends_label_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)
        
        # Friend selection variables
        friend_vars = {}
        
        # Create checkbox for each friend with better styling
        for i, friend in enumerate(sorted(friends)):
            var = tk.BooleanVar()
            friend_vars[friend] = var
            
            friend_frame = tk.Frame(scrollable_frame, relief=tk.FLAT)
            friend_frame.pack(fill=tk.X, pady=1, padx=5)
            
            cb = tk.Checkbutton(friend_frame, text=f"  {friend}", variable=var, 
                               font=('Arial', 11), anchor='w',
                               bg='white' if i % 2 == 0 else '#F8F9FA')
            cb.pack(fill=tk.X, padx=5, pady=2)
        
        # Selection buttons
        select_frame = tk.Frame(main_frame)
        select_frame.pack(fill=tk.X, pady=(0, 20))
        
        def select_all():
            for var in friend_vars.values():
                var.set(True)
        
        def select_none():
            for var in friend_vars.values():
                var.set(False)
        
        tk.Button(select_frame, text='Select All', command=select_all,
                 font=('Arial', 10), bg='#E3F2FD', relief=tk.FLAT).pack(side=tk.LEFT, padx=5)
        tk.Button(select_frame, text='Select None', command=select_none,
                 font=('Arial', 10), bg='#FFF3E0', relief=tk.FLAT).pack(side=tk.LEFT, padx=5)
        
        # Action buttons
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        def send_invites():
            selected_friends = [friend for friend, var in friend_vars.items() if var.get()]
            
            if not selected_friends:
                messagebox.showinfo('Info', 'Please select at least one friend to invite.')
                return
            
            try:
                # Send invitations to selected friends
                for friend in selected_friends:
                    send_json(self.sock, {
                        'type': 'GROUP_INVITE', 
                        'group_name': group_name, 
                        'from': self.username, 
                        'to': friend
                    })
                
                invite_win.destroy()
                messagebox.showinfo('Success', 
                                  f'Invitations sent to {len(selected_friends)} friend(s):\n' + 
                                  '\n'.join(f'• {friend}' for friend in selected_friends))
                
            except Exception as e:
                messagebox.showerror('Error', f'Failed to send invitations: {e}')
        
        def skip_invites():
            """Skip invitation and close dialog"""
            invite_win.destroy()
            messagebox.showinfo('Info', 
                              f'Group "{group_name}" is ready to use!\n\n'
                              'You can invite friends later from the group chat window.')
        
        def cancel_invite():
            invite_win.destroy()
        
        # Three buttons: Send Invitations, Skip, Cancel
        tk.Button(btn_frame, text='Send Invitations', command=send_invites,
                 bg='#28A745', fg='white', font=('Arial', 11, 'bold'),
                 width=15).pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Button(btn_frame, text='Skip for Now', command=skip_invites,
                 bg='#17A2B8', fg='white', font=('Arial', 11),
                 width=12).pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text='Cancel', command=cancel_invite,
                 bg='#6C757D', fg='white', font=('Arial', 11),
                 width=10).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Handle window close
        invite_win.protocol("WM_DELETE_WINDOW", cancel_invite)

    def show_add_member_dialog(self, group_name):
        """Show dialog to add friends to an existing group"""
        if not self.connected:
            messagebox.showinfo('Info', 'Please connect to the server first.')
            return
        
        # Get current group information
        try:
            with open(get_data_path('groups.json'), 'r') as f:
                groups_data = json.load(f)
                if group_name not in groups_data:
                    messagebox.showerror('Error', f'Group "{group_name}" not found.')
                    return
                group_info = groups_data[group_name]
        except Exception as e:
            messagebox.showerror('Error', f'Failed to load group information: {e}')
            return
        
        # Check if user is a member of the group
        if not hasattr(self, 'username') or self.username not in group_info.get('members', []):
            messagebox.showerror('Error', 'You are not a member of this group.')
            return
        
        # Get user's friends who are not already in the group
        if not self.friend_manager:
            messagebox.showinfo('Info', 'No friends available to invite.')
            return
        
        all_friends = self.friend_manager.get_all()
        current_members = set(group_info.get('members', []))
        available_friends = [friend for friend in all_friends if friend not in current_members]
        
        if not available_friends:
            messagebox.showinfo('Info', 'All your friends are already members of this group.')
            return
        
        # Create add member dialog window
        add_win = tk.Toplevel(self.master)
        add_win.title(f'Add Members to {group_name}')
        add_win.geometry('450x550')
        add_win.resizable(False, False)
        add_win.grab_set()
        
        # Center the window
        add_win.transient(self.master)
        
        # Main frame
        main_frame = tk.Frame(add_win)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Title
        title_label = tk.Label(main_frame, text=f'Add Members to "{group_name}"', 
                              font=('Arial', 16, 'bold'), fg='#2C3E50')
        title_label.pack(pady=(0, 10))
        
        # Subtitle
        subtitle_label = tk.Label(main_frame, text='Select friends you want to invite to this group', 
                                 font=('Arial', 11), fg='#7F8C8D')
        subtitle_label.pack(pady=(0, 20))
        
        # Friends list with checkboxes
        list_frame = tk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Create a label frame for better organization
        friends_label_frame = tk.LabelFrame(list_frame, text=f"Available Friends ({len(available_friends)})", 
                                           font=('Arial', 10, 'bold'), fg='#2C3E50')
        friends_label_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable frame for friends
        canvas = tk.Canvas(friends_label_frame)
        scrollbar = tk.Scrollbar(friends_label_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=10)
        
        # Friend selection variables
        friend_vars = {}
        
        # Create checkbox for each available friend with better styling
        for i, friend in enumerate(sorted(available_friends)):
            var = tk.BooleanVar()
            friend_vars[friend] = var
            
            friend_frame = tk.Frame(scrollable_frame, relief=tk.FLAT)
            friend_frame.pack(fill=tk.X, pady=1, padx=5)
            
            cb = tk.Checkbutton(friend_frame, text=f"  {friend}", variable=var, 
                               font=('Arial', 11), anchor='w',
                               bg='white' if i % 2 == 0 else '#F8F9FA')
            cb.pack(fill=tk.X, padx=5, pady=2)
        
        # Selection buttons
        select_frame = tk.Frame(main_frame)
        select_frame.pack(fill=tk.X, pady=(0, 20))
        
        def select_all():
            for var in friend_vars.values():
                var.set(True)
        
        def select_none():
            for var in friend_vars.values():
                var.set(False)
        
        tk.Button(select_frame, text='Select All', command=select_all,
                 font=('Arial', 10), bg='#E3F2FD', relief=tk.FLAT).pack(side=tk.LEFT, padx=5)
        tk.Button(select_frame, text='Select None', command=select_none,
                 font=('Arial', 10), bg='#FFF3E0', relief=tk.FLAT).pack(side=tk.LEFT, padx=5)
        
        # Action buttons
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)
        
        def send_invites():
            selected_friends = [friend for friend, var in friend_vars.items() if var.get()]
            
            if not selected_friends:
                messagebox.showinfo('Info', 'Please select at least one friend to invite.')
                return
            
            try:
                # Get current user's info for the invitation
                user_info = {'name': self.username, 'dept': 'Unknown', 'session': 'Unknown'}
                try:
                    with open(get_data_path('users.json'), 'r') as f:
                        users_data = json.load(f)
                        if self.username in users_data:
                            user_info = users_data[self.username]
                except Exception:
                    pass
                
                # Send invitations to selected friends
                for friend in selected_friends:
                    send_json(self.sock, {
                        'type': 'GROUP_INVITE',
                        'from': self.username,
                        'to': friend,
                        'group_name': group_name,
                        'inviter_info': {
                            'name': user_info.get('name', self.username),
                            'dept': user_info.get('dept', 'Unknown'),
                            'session': user_info.get('session', 'Unknown')
                        }
                    })
                
                add_win.destroy()
                messagebox.showinfo('Success', 
                                  f'Invitations sent to {len(selected_friends)} friend(s):\n' + 
                                  '\n'.join(f'• {friend}' for friend in selected_friends))
                
            except Exception as e:
                messagebox.showerror('Error', f'Failed to send invitations: {e}')
        
        def cancel_add():
            add_win.destroy()
        
        # Two buttons: Send Invitations, Cancel
        tk.Button(btn_frame, text='Send Invitations', command=send_invites,
                 bg='#28A745', fg='white', font=('Arial', 11, 'bold'),
                 width=15).pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Button(btn_frame, text='Cancel', command=cancel_add,
                 bg='#6C757D', fg='white', font=('Arial', 11),
                 width=10).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Handle window close
        add_win.protocol("WM_DELETE_WINDOW", cancel_add)

    def show_leave_group_dialog(self, group_name):
        """Show confirmation dialog for leaving a group"""
        if not self.connected:
            messagebox.showinfo('Info', 'Please connect to the server first.')
            return
        
        # Create leave group confirmation dialog
        leave_win = tk.Toplevel(self.master)
        leave_win.title('Leave Group')
        leave_win.geometry('400x300')
        leave_win.resizable(False, False)
        leave_win.grab_set()
        
        # Center the window
        leave_win.transient(self.master)
        
        # Main frame
        main_frame = tk.Frame(leave_win)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Warning icon and title
        title_frame = tk.Frame(main_frame)
        title_frame.pack(pady=(0, 20))
        
        title_label = tk.Label(title_frame, text='⚠️ Leave Group', 
                              font=('Arial', 16, 'bold'), fg='#DC3545')
        title_label.pack()
        
        # Confirmation message
        message_label = tk.Label(main_frame, 
                                text=f'Are you sure you want to leave the group\n"{group_name}"?',
                                font=('Arial', 12), justify='center')
        message_label.pack(pady=(0, 10))
        
        # Warning message
        warning_label = tk.Label(main_frame, 
                                text='You will no longer receive messages from this group\nand will need to be re-invited to rejoin.',
                                font=('Arial', 10), fg='#6C757D', justify='center')
        warning_label.pack(pady=(0, 30))
        
        # Button functions
        def confirm_leave():
            try:
                # Send leave group request to server
                send_json(self.sock, {
                    'type': 'LEAVE_GROUP',
                    'group_name': group_name,
                    'user': self.username
                })
                
                # Remove from local joined groups
                self.remove_joined_group(group_name)
                
                # Reset info section if currently viewing this group
                if hasattr(self, 'current_chat') and self.current_chat and self.current_chat[1] == group_name:
                    self.current_chat = None
                    self.reset_info_section()
                    # Clear chat area
                    self.chat_area.config(state='normal')
                    self.chat_area.delete(1.0, tk.END)
                    self.chat_area.config(state='disabled')
                
                # Close dialog
                leave_win.destroy()
                
                # Show confirmation message
                messagebox.showinfo('Group Left', 
                                  f'You have successfully left the group "{group_name}".')
                
            except Exception as e:
                messagebox.showerror('Error', f'Failed to leave group: {e}')
                leave_win.destroy()
        
        def cancel_leave():
            leave_win.destroy()
        
        # Action buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack()
        
        # Leave button
        leave_btn = tk.Button(button_frame, text='Leave Group', 
                             command=confirm_leave,
                             bg='#DC3545', fg='white', 
                             font=('Arial', 12, 'bold'),
                             width=12, height=2,
                             relief='raised', bd=3,
                             cursor='hand2',
                             activebackground='#C82333',
                             activeforeground='white')
        leave_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        # Cancel button
        cancel_btn = tk.Button(button_frame, text='Cancel', 
                              command=cancel_leave,
                              bg='#6C757D', fg='white', 
                              font=('Arial', 12),
                              width=12, height=2,
                              relief='raised', bd=3,
                              cursor='hand2',
                              activebackground='#5A6268',
                              activeforeground='white')
        cancel_btn.pack(side=tk.RIGHT)
        
        # Add button hover effects
        def on_leave_enter(e):
            leave_btn.config(bg='#C82333')
        def on_leave_leave(e):
            leave_btn.config(bg='#DC3545')
        def on_cancel_enter(e):
            cancel_btn.config(bg='#5A6268')
        def on_cancel_leave(e):
            cancel_btn.config(bg='#6C757D')
            
        leave_btn.bind('<Enter>', on_leave_enter)
        leave_btn.bind('<Leave>', on_leave_leave)
        cancel_btn.bind('<Enter>', on_cancel_enter)
        cancel_btn.bind('<Leave>', on_cancel_leave)
        
        # Handle window close (treat as cancel)
        leave_win.protocol("WM_DELETE_WINDOW", cancel_leave)
        
        # Focus on dialog
        leave_win.focus_set()

    def join_group(self):
        gname = simpledialog.askstring('Join Group', 'Enter group name:')
        if gname:
            send_json(self.sock, {'type': 'JOIN_GROUP', 'group_name': gname, 'user': self.username})
            messagebox.showinfo('Info', f'Requested to join group {gname}.')
            self.group_name = gname
            self.add_joined_group(gname)

    def send_message(self, event=None):
        import json
        
        # Check connection first
        if not self.connected or not self.sock:
            messagebox.showerror('Connection Error', 'Not connected to server. Please login again.')
            return
        
        msg = self.msg_entry.get().strip()
        if not msg:
            return
        if self.current_chat:
            chat_type, name = self.current_chat
            current_time = datetime.datetime.now()
            timestamp = current_time.isoformat()
            
            try:
                if chat_type == 'private':
                    # Check if the user is a friend before sending message
                    is_friend = self.friend_manager.is_friend(name)
                    print(f"DEBUG: Checking if {self.username} is friends with {name}: {is_friend}")
                    print(f"DEBUG: Current friends list: {self.friend_manager.get_all()}")
                    
                    if not is_friend:
                        messagebox.showwarning('Not Friends', f'You need to be friends with {name} to send messages.\nSend a friend request first.')
                        return
                        
                    send_json(self.sock, {'type': 'PRIVATE_MESSAGE', 'to': name, 'from': self.username, 'msg': msg, 'timestamp': timestamp})
                    self.display_message_in_main(self.username, msg, align='right', timestamp=timestamp)
                    # Save to chat history with timestamp
                    users = sorted([self.username, name])
                    history_file = f"chat_{users[0]}_{users[1]}.json"
                    arr = [self.username, msg, 'right', False, None, None, timestamp]
                    with open(history_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(arr) + '\n')
                elif chat_type == 'group':
                    send_json(self.sock, {'type': 'GROUP_MESSAGE', 'group_name': name, 'from': self.username, 'msg': msg, 'timestamp': timestamp})
                    self.display_message_in_main(f'You (Group {name})', msg, align='right', timestamp=timestamp)
                    # Save to group chat history with timestamp
                    group_history_file = f"group_chat_{name}.json"
                    arr = [self.username, msg, 'right', False, None, None, timestamp]
                    with open(group_history_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(arr) + '\n')
            except ConnectionError as e:
                messagebox.showerror('Connection Error', 
                    f'Failed to send message due to connection issue:\n{str(e)}\n\n'
                    'Please check your connection and try again.')
                return
            except Exception as e:
                messagebox.showerror('Error', f'Failed to send message: {e}')
                return
        else:
            messagebox.showinfo('Info', 'Select a user or join a group to chat.')
        self.msg_entry.delete(0, tk.END)

    # No longer used for private chat, handled in ChatWindow

    def check_connection_health(self):
        """
        Check if the connection is still healthy and attempt recovery if needed
        """
        try:
            # Send a simple ping to check connection
            if hasattr(self, 'sock') and self.sock and self.connected:
                # Try to send a keepalive message
                send_json(self.sock, {'type': 'PING'})
                return True
        except Exception as e:
            print(f"[CONNECTION HEALTH] Connection check failed: {e}")
            return False
        return False

    def attempt_reconnection(self):
        """
        Attempt to reconnect to the server
        """
        try:
            print("[RECONNECT] Attempting to reconnect...")
            
            # Close existing socket
            if hasattr(self, 'sock') and self.sock:
                try:
                    self.sock.close()
                except:
                    pass
            
            # Create new socket with proper configuration
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.settimeout(30.0)
            
            # Attempt connection
            self.sock.connect((SERVER_HOST, SERVER_PORT))
            
            # Re-login using stored credentials
            if hasattr(self, 'username') and hasattr(self, 'stored_password'):
                send_json(self.sock, {'type': 'LOGIN', 'name': self.username, 'password': self.stored_password})
                resp = recv_json(self.sock)
                
                if resp.get('type') == 'LOGIN_SUCCESS':
                    print("[RECONNECT] Successfully reconnected!")
                    self.connected = True
                    self.sock.settimeout(None)  # Remove timeout for listening
                    return True
                else:
                    print(f"[RECONNECT] Login failed after reconnection: {resp.get('reason', 'Unknown error')}")
                    return False
            else:
                print("[RECONNECT] No stored credentials available for re-login")
                return False
                
        except Exception as e:
            print(f"[RECONNECT] Reconnection failed: {e}")
            return False

    def listen_server(self):
        import json
        import os
        
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        try:
            while self.connected:
                try:
                    message = recv_json(self.sock)
                    consecutive_errors = 0  # Reset error counter on successful receive
                    
                    mtype = message.get('type')
                    
                    # Handle PING response
                    if mtype == 'PONG':
                        continue  # Just a keepalive, ignore
                    
                    if mtype == 'LIST_RESPONSE':
                        self.active_users = message['users']
                        self.refresh_friendlist(self.active_users)
                    elif mtype == 'FRIEND_REQUEST':
                        from_user = message.get('from')
                        sender_info = message.get('sender_info', {})
                        if from_user:
                            print(f"[FRIEND REQUEST] Received friend request from {from_user}")
                            # Add friend request to notifications with sender info
                            self.add_home_notification(from_user, f"sent you a friend request", 
                                                     is_friend_request=True, sender_info=sender_info)
                            
                            # Don't show auto dialog anymore - let user click notification
                            # response = messagebox.askyesno('Friend Request', 
                            #     f'{from_user} wants to add you as a friend.\nDo you accept?')
                            # if response:
                            #     # Accept friend request
                            #     send_json(self.sock, {
                            #         'type': 'FRIEND_REQUEST_RESPONSE',
                            #         'from': self.username,
                            #         'to': from_user,
                            #         'accepted': True
                            #     })
                            #     # Add to friend list
                            #     self.friend_manager.add(from_user)
                            #     self.refresh_friendlist()
                            #     messagebox.showinfo('Friend Added', f'{from_user} has been added to your friends!')
                            # else:
                            #     # Decline friend request
                            #     send_json(self.sock, {
                            #         'type': 'FRIEND_REQUEST_RESPONSE',
                            #         'from': self.username,
                            #         'to': from_user,
                            #         'accepted': False
                            #     })
                    elif mtype == 'FRIEND_REQUEST_ACCEPTED':
                        from_user = message.get('from')
                        print(f"[FRIEND_REQUEST_ACCEPTED] ===== RECEIVED ACCEPTANCE NOTIFICATION =====")
                        print(f"[FRIEND_REQUEST_ACCEPTED] User {self.username} received acceptance from {from_user}")
                        print(f"[FRIEND_REQUEST_ACCEPTED] Current friends before: {self.friend_manager.get_all()}")
                        if from_user:
                            # Force reload friend list from file first
                            self.friend_manager.reload()
                            # Add to friend list
                            self.friend_manager.add(from_user)
                            print(f"[FRIEND_REQUEST_ACCEPTED] Added {from_user} to friend list")
                            print(f"[FRIEND_REQUEST_ACCEPTED] Current friends after: {self.friend_manager.get_all()}")
                            self.refresh_friendlist()
                            print(f"[FRIEND_REQUEST_ACCEPTED] Refreshed friend list display")
                            messagebox.showinfo('Friend Request Accepted', f'{from_user} accepted your friend request!')
                            print(f"[FRIEND_REQUEST_ACCEPTED] ===== ACCEPTANCE PROCESSING COMPLETE =====")
                        else:
                            print(f"[FRIEND_REQUEST_ACCEPTED] ERROR: No from_user in message: {message}")
                    elif mtype == 'FRIEND_ADDED':
                        # Notification for the user who accepted the friend request
                        friend_name = message.get('friend')
                        print(f"[FRIEND_ADDED] ===== RECEIVED FRIEND ADDED NOTIFICATION =====")
                        print(f"[FRIEND_ADDED] User {self.username} notified that {friend_name} was added")
                        print(f"[FRIEND_ADDED] Current friends before: {self.friend_manager.get_all()}")
                        if friend_name:
                            # Force reload friend list from file first
                            self.friend_manager.reload()
                            # Make sure the friend is in our list and refresh
                            self.friend_manager.add(friend_name)
                            print(f"[FRIEND_ADDED] Ensured {friend_name} is in friend list")
                            print(f"[FRIEND_ADDED] Current friends after: {self.friend_manager.get_all()}")
                            self.refresh_friendlist()
                            print(f"[FRIEND_ADDED] Refreshed friend list display")
                            print(f"[FRIEND_ADDED] ===== FRIEND ADDED PROCESSING COMPLETE =====")
                        else:
                            print(f"[FRIEND_ADDED] ERROR: No friend_name in message: {message}")
                    elif mtype == 'FRIEND_REQUEST_DECLINED':
                        from_user = message.get('from')
                        if from_user:
                            messagebox.showinfo('Friend Request Declined', f'{from_user} declined your friend request.')
                    elif mtype == 'STATUS_RESPONSE':
                        status_dict = message.get('status', {})
                        self.refresh_friendlist([f for f, online in status_dict.items() if online])
                    elif mtype == 'INCOMING_REQUEST':
                        from_user = message['from']
                        info = f"Name: {from_user['name']}, Dept: {from_user['dept']}, Session: {from_user['session']}"
                        if messagebox.askyesno('Chat Request', f"{info}\nAccept chat?"):
                            self.open_private_chat(from_user['name'])
                        else:
                            messagebox.showinfo('Info', f'Ignored chat request from {from_user["name"]}')
                    elif mtype == 'PRIVATE_MESSAGE':
                        sender = message['from']
                        msg = message['msg']
                        timestamp = message.get('timestamp', datetime.datetime.now().isoformat())
                        if self.current_chat and self.current_chat[0] == 'private' and self.current_chat[1] == sender:
                            self.display_message_in_main(sender, msg, align='left', timestamp=timestamp)
                            users = sorted([self.username, sender])
                            history_file = f"chat_{users[0]}_{users[1]}.json"
                            arr = [sender, msg, 'left', False, None, None, timestamp]
                            with open(history_file, 'a', encoding='utf-8') as f:
                                f.write(json.dumps(arr) + '\n')
                        else:
                            self.add_home_notification(sender, msg)
                    elif mtype == 'MEDIA':
                        sender = message['from']
                        filename = message['filename']
                        filedata = message['data']
                        timestamp = message.get('timestamp', datetime.datetime.now().isoformat())
                        if self.current_chat and self.current_chat[0] == 'private' and self.current_chat[1] == sender:
                            self.display_file_in_main(sender, filename, filedata, align='left', timestamp=timestamp)
                            users = sorted([self.username, sender])
                            history_file = f"chat_{users[0]}_{users[1]}.json"
                            arr = [sender, '', 'left', True, filename, filedata, timestamp]
                            with open(history_file, 'a', encoding='utf-8') as f:
                                f.write(json.dumps(arr) + '\n')
                        else:
                            self.add_home_notification(sender, f'Sent a file: {filename}', is_file=True, filedata=filedata, filename=filename)
                    elif mtype == 'GROUP_MESSAGE':
                        sender = message['from']
                        msg = message['msg']
                        gname = message['group_name']
                        timestamp = message.get('timestamp', datetime.datetime.now().isoformat())
                        self.group_name = gname
                        
                        # Display in main chat if currently viewing this group
                        if (self.current_chat and self.current_chat[0] == 'group' and 
                            self.current_chat[1] == gname):
                            print(f"DEBUG: Displaying group message in main chat for group {gname}")
                            self.display_message_in_main(f'{sender} (Group {gname})', msg, align='left', timestamp=timestamp)
                        else:
                            # Add as notification if not viewing this group
                            print(f"DEBUG: Current chat: {self.current_chat}")
                            print(f"DEBUG: Adding group message notification from {sender} for group {gname}")
                            # Format message to trigger group message detection
                            group_msg_text = f'(Group {gname}) {msg}'
                            self.add_home_notification(sender, group_msg_text, timestamp=timestamp)
                        
                        # Save to group chat history with timestamp (only once)
                        group_history_file = f"group_chat_{gname}.json"
                        arr = [sender, msg, 'left', False, None, None, timestamp]
                        with open(group_history_file, 'a', encoding='utf-8') as f:
                            f.write(json.dumps(arr) + '\n')
                        
                        self.add_joined_group(gname)
                    elif mtype == 'GROUP_INVITE':
                        print(f"DEBUG: Received GROUP_INVITE message: {message}")
                        group_name = message.get('group_name')
                        from_user = message.get('from')
                        sender_info = message.get('sender_info', {})
                        print(f"DEBUG: group_name={group_name}, from_user={from_user}, sender_info={sender_info}")
                        
                        if group_name and from_user:
                            # Add group invitation to notifications instead of showing dialog directly
                            print(f"DEBUG: Adding group invitation notification for {group_name} from {from_user}")
                            self.add_home_notification(from_user, f"invited you to join group '{group_name}'", 
                                                     is_group_invite=True, group_name=group_name, sender_info=sender_info)
                        else:
                            print(f"DEBUG: Missing group_name or from_user in GROUP_INVITE message")
                    elif mtype == 'GROUP_MEDIA':
                        sender = message['from']
                        filename = message['filename']
                        filedata = message['data']
                        gname = message['group_name']
                        timestamp = message.get('timestamp', datetime.datetime.now().isoformat())
                        
                        # Display in main chat if currently viewing this group
                        if (self.current_chat and self.current_chat[0] == 'group' and 
                            self.current_chat[1] == gname):
                            self.display_file_in_main(sender, filename, filedata, align='left', timestamp=timestamp)
                        else:
                            # Add as notification if not viewing this group
                            self.add_home_notification(sender, f'(Group {gname}) Sent a file: {filename}', 
                                                      is_file=True, filedata=filedata, filename=filename, timestamp=timestamp)
                        
                        # Save to group chat history with timestamp (only once)
                        group_history_file = f"group_chat_{gname}.json"
                        arr = [sender, '', 'left', True, filename, filedata, timestamp]
                        with open(group_history_file, 'a', encoding='utf-8') as f:
                            f.write(json.dumps(arr) + '\n')
                        
                        self.add_joined_group(gname)
                    elif mtype == 'OFFLINE_MESSAGES':
                        for msg in message.get('messages', []):
                            sender = msg.get('from')
                            sender_info = msg.get('sender_info')
                            timestamp = msg.get('timestamp')  # Get original timestamp
                            if msg.get('is_friend_request'):
                                self.add_home_notification(sender, msg.get('msg', 'sent you a friend request'), 
                                                         is_friend_request=True, sender_info=sender_info, timestamp=timestamp, is_offline_message=True)
                            elif msg.get('is_group_invite'):
                                # Handle group invitations from offline messages - add to notifications
                                group_name = msg.get('group_name')
                                if group_name:
                                    self.add_home_notification(sender, f"invited you to join group '{group_name}'", 
                                                             is_group_invite=True, group_name=group_name, sender_info=sender_info, timestamp=timestamp, is_offline_message=True)
                            elif msg.get('is_file'):
                                self.add_home_notification(sender, f"Sent a file: {msg.get('filename')}", is_file=True, filedata=msg.get('data'), filename=msg.get('filename'), timestamp=timestamp, is_offline_message=True)
                            else:
                                self.add_home_notification(sender, msg.get('msg', ''), timestamp=timestamp, is_offline_message=True)
                    elif mtype == 'MESSAGE_ERROR':
                        reason = message.get('reason', 'Message sending failed')
                        messagebox.showerror('Message Error', reason)
                    elif mtype == 'GROUP_INVITE_ACCEPTED':
                        from_user = message.get('from')
                        group_name = message.get('group_name')
                        if from_user and group_name:
                            messagebox.showinfo('Group Invitation Accepted', 
                                              f'{from_user} accepted your invitation to join "{group_name}"!')
                    elif mtype == 'GROUP_INVITE_DECLINED':
                        from_user = message.get('from')
                        group_name = message.get('group_name')
                        if from_user and group_name:
                            messagebox.showinfo('Group Invitation Declined', 
                                              f'{from_user} declined your invitation to join "{group_name}".')
                    elif mtype == 'GROUP_JOIN_SUCCESS':
                        group_name = message.get('group_name')
                        if group_name:
                            self.add_joined_group(group_name)
                            messagebox.showinfo('Joined Group', f'You have successfully joined "{group_name}"!')
                    elif mtype == 'LEAVE_GROUP_SUCCESS':
                        group_name = message.get('group_name')
                        if group_name:
                            # Group removal is handled in the dialog, just show confirmation
                            pass  # Dialog already shows confirmation
                    elif mtype == 'LEAVE_GROUP_ERROR':
                        error_msg = message.get('message', 'Failed to leave group')
                        messagebox.showerror('Leave Group Error', error_msg)
                    elif mtype == 'UNFRIEND_SUCCESS':
                        unfriended_user = message.get('unfriended_user')
                        print(f"[DEBUG] Received UNFRIEND_SUCCESS for {unfriended_user}")
                        if unfriended_user:
                            # Refresh friend list to update UI (friendship already removed locally)
                            self.refresh_friendlist()
                            print(f"[DEBUG] Refreshed friend list after unfriend success")
                            # The success message is already shown in unfriend_user method
                    elif mtype == 'UNFRIEND_ERROR':
                        error_msg = message.get('message', 'Failed to unfriend user')
                        print(f"[DEBUG] Received UNFRIEND_ERROR: {error_msg}")
                        messagebox.showerror('Unfriend Error', error_msg)
                    elif mtype == 'UNFRIENDED_BY':
                        unfriended_by = message.get('unfriended_by')
                        print(f"[DEBUG] Received UNFRIENDED_BY from {unfriended_by}")
                        if unfriended_by:
                            # Remove from local friend list
                            removed = self.friend_manager.remove(unfriended_by)
                            print(f"[DEBUG] Removed {unfriended_by} from local friend list: {removed}")
                            
                            # Refresh friend list to update UI
                            self.refresh_friendlist()
                            print(f"[DEBUG] Refreshed friend list after being unfriended")
                            
                            # Show notification
                            messagebox.showinfo('Unfriended', 
                                              f'{unfriended_by} has removed you from their friends list.')
                            
                            # Close chat if currently chatting with this user
                            if (hasattr(self, 'current_chat') and self.current_chat and 
                                self.current_chat[0] == 'private' and self.current_chat[1] == unfriended_by):
                                # Reset to default state
                                self.current_chat = None
                                self.reset_info_section()
                                self.chat_area.config(state='normal')
                                self.chat_area.delete(1.0, tk.END)
                                self.chat_area.insert(tk.END, 'Select a friend or group to start chatting.\n')
                                self.chat_area.config(state='disabled')
                                print(f"[DEBUG] Closed chat with unfriended user {unfriended_by}")
                except ConnectionError as e:
                    # Connection specific errors - likely network issues
                    consecutive_errors += 1
                    print(f"[CONNECTION ERROR #{consecutive_errors}] {e}")
                    
                    if self.connected and consecutive_errors < max_consecutive_errors:
                        print(f"[RECOVERY] Attempting to recover from connection error...")
                        
                        # Try to reconnect
                        if self.attempt_reconnection():
                            print("[RECOVERY] Successfully reconnected, continuing...")
                            consecutive_errors = 0
                            continue
                        else:
                            print("[RECOVERY] Reconnection failed")
                    
                    if self.connected:
                        messagebox.showerror('Connection Error', 
                                           f'Network communication error: {e}\n\n'
                                           f'Please try reconnecting by logging out and logging back in.')
                    break
                except Exception as e:
                    # Only show error if still connected (not after logout)
                    consecutive_errors += 1
                    if self.connected:
                        print(f"[GENERAL ERROR #{consecutive_errors}] {e}")
                        
                        if consecutive_errors < max_consecutive_errors:
                            print("[RECOVERY] Attempting to continue after general error...")
                            continue
                        else:
                            messagebox.showerror('Error', f'Multiple errors encountered: {e}')
                    break
        except Exception:
            pass
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        self.connected = False
        # Only show disconnect error if not logging out
        # messagebox.showerror('Error', 'Disconnected from server.')

    def show_notification(self, sender, msg):
        # Deprecated: now using home page notification area
        pass

    def add_home_notification(self, sender, msg, is_file=False, filedata=None, filename=None, is_friend_request=False, sender_info=None, is_group_invite=False, group_name=None, timestamp=None, is_offline_message=False):
        # Only one notification per sender (but allow friend requests, group invites, group messages, and offline messages to override regular messages)
        if not hasattr(self, 'notification_listbox'):
            print(f"[ERROR] No notification_listbox found!")
            return
        
        # Check if this is a group message notification
        is_group_message = msg.startswith('(Group ')
        print(f"DEBUG: add_home_notification called - sender={sender}, msg={msg[:50]}..., is_group_message={is_group_message}, is_offline_message={is_offline_message}")
        
        # Block duplicate notifications unless it's a friend request, group invite, group message, or offline message
        if sender in self.notifications_home and not is_friend_request and not is_group_invite and not is_group_message and not is_offline_message:
            print(f"DEBUG: Blocking duplicate notification from {sender}")
            return
        
        # Remove existing notification from same sender if this is a friend request, group invitation, or group message (but not for offline messages)
        if (is_friend_request or is_group_invite or is_group_message) and sender in self.notifications_home and not is_offline_message:
            print(f"DEBUG: Removing existing notification from {sender}")
            # Find and remove existing notification
            for i in range(self.notification_listbox.size()):
                if self.notification_listbox.get(i).startswith(f'{sender}:') or self.notification_listbox.get(i).startswith(f'[FRIEND REQUEST] {sender}:') or self.notification_listbox.get(i).startswith(f'[GROUP INVITE] {sender}:'):
                    self.notification_listbox.delete(i)
                    break
        
        # Format display text differently for friend requests and group invitations
        if is_friend_request:
            display = f'[FRIEND REQUEST] {sender}: {msg}'
            print(f"[FRIEND REQUEST] Added notification: {display}")
        elif is_group_invite:
            display = f'[GROUP INVITE] {sender}: {msg}'
            print(f"[GROUP INVITE] Added notification: {display}")
        else:
            display = f'{sender}: {msg}'
            print(f"DEBUG: Adding regular notification to listbox: {display}")
            
        self.notification_listbox.insert(tk.END, display)
        print(f"DEBUG: Notification added to listbox. New size: {self.notification_listbox.size()}")
        
        # For offline messages, allow multiple notifications from the same sender
        # Create a unique key if this is an offline message to avoid overwriting
        storage_key = sender
        if is_offline_message:
            # Create unique key for offline messages using timestamp or counter
            import time
            storage_key = f"{sender}_{int(time.time() * 1000)}"  # Use milliseconds for uniqueness
        
        print(f"DEBUG: Storing notification with key: {storage_key}")
        self.notifications_home[storage_key] = {
            'sender': sender,  # Store original sender for lookup
            'msg': msg, 
            'is_file': is_file, 
            'filedata': filedata, 
            'filename': filename,
            'is_friend_request': is_friend_request,
            'is_group_invite': is_group_invite,
            'group_name': group_name,
            'sender_info': sender_info,
            'timestamp': timestamp,
            'is_offline_message': is_offline_message
        }
        
        print(f"DEBUG: Total notifications in storage: {len(self.notifications_home)}")
        print(f"DEBUG: Listbox has {self.notification_listbox.size()} items")

    def handle_notification_click(self, event):
        selection = self.notification_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        display = self.notification_listbox.get(idx)
        
        # Extract sender from display string
        if display.startswith('[FRIEND REQUEST]'):
            # Format: "[FRIEND REQUEST] sender: message"
            sender = display.split('] ')[1].split(':', 1)[0]
        elif display.startswith('[GROUP INVITE]'):
            # Format: "[GROUP INVITE] sender: message"
            sender = display.split('] ')[1].split(':', 1)[0]
        else:
            # Format: "sender: message"
            sender = display.split(':', 1)[0]
        
        # Find the notification info by searching through all stored notifications
        # This handles both regular notifications (stored by sender) and offline messages (stored by unique keys)
        info = None
        info_key = None
        
        # First try direct lookup
        if sender in self.notifications_home:
            info = self.notifications_home[sender]
            info_key = sender
        else:
            # Search for offline message with this sender
            for key, notification in self.notifications_home.items():
                if notification.get('sender') == sender:
                    info = notification
                    info_key = key
                    break
        
        if not info:
            print(f"DEBUG: No notification info found for sender {sender}")
            return
        
        # Handle friend request notification
        if info and info.get('is_friend_request'):
            print(f"[FRIEND REQUEST] Opening friend request dialog for {sender}")
            sender_info = info.get('sender_info', {})
            # Show detailed friend request dialog
            self.show_friend_request_dialog(sender, sender_info)
            # Remove notification from listbox and dict after showing dialog
            self.notification_listbox.delete(idx)
            if info_key in self.notifications_home:
                del self.notifications_home[info_key]
            return
        
        # Handle group invitation notification
        if info and info.get('is_group_invite'):
            print(f"DEBUG: Group invitation notification clicked for {sender}")
            group_name = info.get('group_name')
            sender_info = info.get('sender_info', {})
            print(f"DEBUG: Group name: {group_name}, Sender info: {sender_info}")
            # Show detailed group invitation dialog
            self.show_group_invitation_dialog(sender, group_name, sender_info)
            # Remove notification from listbox and dict after showing dialog
            self.notification_listbox.delete(idx)
            if info_key in self.notifications_home:
                del self.notifications_home[info_key]
            return
        
        # Check if this is a group message notification
        is_group_notification = info and info.get('msg', '').startswith('(Group ')
        if is_group_notification:
            # Extract group name from message like "(Group groupname) message"
            msg = info.get('msg', '')
            try:
                group_name = msg.split('(Group ')[1].split(')')[0]
                # Open group chat instead of private chat
                self.current_chat = ('group', group_name)
                self.open_group_chat_in_main(group_name)
                
                # Remove notification from listbox and dict
                self.notification_listbox.delete(idx)
                if info_key in self.notifications_home:
                    del self.notifications_home[info_key]
                return
            except Exception:
                print(f"DEBUG: Failed to parse group name from message: {msg}")
        
        # Open private chat in main area for regular messages
        self.open_chat_in_main(sender)
        # If info is a file, display file; else display message
        already_in_history = False
        users = sorted([self.username, sender])
        history_file = f"chat_{users[0]}_{users[1]}.json"
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    last = json.loads(lines[-1])
                    if info and info.get('is_file') and info.get('filedata') and info.get('filename'):
                        if len(last) > 4 and last[0] == sender and last[4] == info['filename']:
                            already_in_history = True
                    elif info and len(last) > 1 and last[0] == sender and last[1] == info['msg']:
                        already_in_history = True
        except Exception:
            pass
        if info and not already_in_history:
            if info.get('is_file') and info.get('filedata') and info.get('filename'):
                if sender != self.username:
                    # Use original timestamp if available
                    timestamp = info.get('timestamp')
                    self.display_file_in_main(sender, info['filename'], info['filedata'], align='left', timestamp=timestamp)
                # Save to chat history with original timestamp
                arr = [sender, '', 'left', True, info['filename'], info['filedata'], info.get('timestamp')]
                with open(history_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(arr) + '\n')
            else:
                if sender != self.username:
                    # Use original timestamp if available
                    timestamp = info.get('timestamp')
                    self.display_message_in_main(sender, info["msg"], align='left', timestamp=timestamp)
                arr = [sender, info["msg"], 'left', False, None, None, info.get('timestamp')]
                with open(history_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(arr) + '\n')
        # Remove notification from listbox and dict
        self.notification_listbox.delete(idx)
        if info_key in self.notifications_home:
            del self.notifications_home[info_key]

    def refresh_friendlist(self, online_users=None):
        if self.friend_manager:
            # Clear previous friend widgets
            for widget in getattr(self, 'friendlist_frame', []).winfo_children():
                widget.destroy()
            if not hasattr(self, 'green_dot_img'):
                self.load_status_icons()
            if online_users is not None:
                online_set = set(online_users)
            elif hasattr(self, 'active_users'):
                online_set = set(self.active_users)
            else:
                online_set = set()
            self._friend_labels = []
            for friend in sorted(self.friend_manager.get_all()):
                if friend == self.username:
                    continue
                is_online = friend in online_set
                img = self.green_dot_img if is_online else self.red_dot_img
                status_text = 'Online' if is_online else 'Offline'
                friend_row = tk.Frame(self.friendlist_frame)
                friend_row.pack(fill=tk.X, pady=1)
                if img:
                    icon_label = tk.Label(friend_row, image=img)
                    icon_label.image = img  # keep reference
                else:
                    icon_label = tk.Label(friend_row, text=status_text)
                icon_label.pack(side=tk.LEFT, padx=(0,4))
                name_label = tk.Label(friend_row, text=friend, anchor='w')
                name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
                # Make the whole row clickable (double-click for chat)
                def make_callback(f=friend):
                    return lambda e: self.open_chat_in_main(f)
                friend_row.bind('<Double-Button-1>', make_callback())
                icon_label.bind('<Double-Button-1>', make_callback())
                name_label.bind('<Double-Button-1>', make_callback())
                self._friend_labels.append((friend_row, icon_label, name_label))

    def open_chat_in_main(self, friend):
        # Check if the user is a friend before opening chat
        if not self.friend_manager.is_friend(friend):
            messagebox.showwarning('Not Friends', f'You need to be friends with {friend} to chat.\nSend a friend request first through "Find Friend".')
            return
            
        # Set up the main chat area for this friend
        self.current_chat = ('private', friend)
        
        # Clear and populate the friend information section
        self.update_friend_info_section(friend)
        
        # Clear the chat area and load chat history
        self.chat_area.config(state='normal')
        self.chat_area.delete(1.0, tk.END)
        
        # Load chat history
        users = sorted([self.username, friend])
        history_file = f"chat_{users[0]}_{users[1]}.json"
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        arr = json.loads(line)
                        sender = arr[0] if len(arr) > 0 else ''
                        msg = arr[1] if len(arr) > 1 else ''
                        align = arr[2] if len(arr) > 2 else 'left'
                        is_file = arr[3] if len(arr) > 3 else False
                        filename = arr[4] if len(arr) > 4 else None
                        filedata = arr[5] if len(arr) > 5 else None
                        timestamp = arr[6] if len(arr) > 6 else None
                        if is_file and filename and filedata:
                            self.display_file_in_main(sender, filename, filedata, align=align, timestamp=timestamp)
                        else:
                            self.display_message_in_main(sender, msg, align=align, timestamp=timestamp)
                    except Exception:
                        continue
        self.chat_area.config(state='disabled')
    
    def update_friend_info_section(self, friend):
        """Update the upper info section with friend information"""
        # Clear existing content
        for widget in self.info_content_frame.winfo_children():
            widget.destroy()
        
        # Load friend information from users.json
        friend_info = {'name': friend, 'dept': 'Unknown', 'session': 'Unknown'}
        try:
            with open(get_data_path('users.json'), 'r') as f:
                users_data = json.load(f)
                if friend in users_data:
                    friend_info = users_data[friend]
        except Exception:
            pass
        
        # Create info layout
        info_main_frame = tk.Frame(self.info_content_frame, bg='#F0F8FF')
        info_main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side: Profile picture
        left_frame = tk.Frame(info_main_frame, bg='#F0F8FF')
        left_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        # Load and display profile picture
        profile_img = None
        from PIL import Image, ImageTk
        img_path = f'profile_{friend}.png'
        try:
            if os.path.exists(img_path):
                pil_img = Image.open(img_path)
            else:
                pil_img = Image.open('default_dp.png')
            pil_img.thumbnail((60, 60))
            profile_img = ImageTk.PhotoImage(pil_img)
        except Exception:
            try:
                pil_img = Image.open('default_dp.png')
                pil_img.thumbnail((60, 60))
                profile_img = ImageTk.PhotoImage(pil_img)
            except Exception:
                profile_img = None
        
        if profile_img is not None:
            img_label = tk.Label(left_frame, image=profile_img, bg='#F0F8FF')
            img_label.image = profile_img  # Keep reference
            img_label.pack()
        else:
            tk.Label(left_frame, text='[No Image]', bg='#F0F8FF', 
                    font=('Arial', 10), fg='gray').pack()
        
        # Right side: Friend information
        right_frame = tk.Frame(info_main_frame, bg='#F0F8FF')
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Friend details
        tk.Label(right_frame, text=friend_info.get('name', friend), 
                font=('Arial', 16, 'bold'), bg='#F0F8FF', fg='#2C3E50').pack(anchor='w')
        
        tk.Label(right_frame, text=f"Department: {friend_info.get('dept', 'Unknown')}", 
                font=('Arial', 12), bg='#F0F8FF', fg='#34495E').pack(anchor='w', pady=(5, 0))
        
        tk.Label(right_frame, text=f"Session: {friend_info.get('session', 'Unknown')}", 
                font=('Arial', 12), bg='#F0F8FF', fg='#34495E').pack(anchor='w', pady=(2, 0))
        
        # Status indicator - Check actual online status
        status_frame = tk.Frame(right_frame, bg='#F0F8FF')
        status_frame.pack(anchor='w', pady=(5, 0))
        
        # Check if friend is online by looking at active_users list
        is_online = hasattr(self, 'active_users') and friend in self.active_users
        
        # Set status color and text based on actual online status
        if is_online:
            status_color = '#28A745'  # Green for online
            status_text = 'Online'
        else:
            status_color = '#DC3545'  # Red for offline
            status_text = 'Offline'
        
        status_label = tk.Label(status_frame, text='●', fg=status_color, bg='#F0F8FF', font=('Arial', 12))
        status_label.pack(side=tk.LEFT)
        tk.Label(status_frame, text=status_text, font=('Arial', 10), bg='#F0F8FF', 
                fg=status_color).pack(side=tk.LEFT, padx=(2, 0))
        
        # Action buttons frame
        button_frame = tk.Frame(right_frame, bg='#F0F8FF')
        button_frame.pack(anchor='w', pady=(15, 0))
        
        # Unfriend button
        unfriend_btn = tk.Button(button_frame, text='Unfriend', 
                               command=lambda: self.unfriend_user(friend),
                               bg='#DC3545', fg='white', font=('Arial', 10, 'bold'),
                               relief='raised', bd=2, cursor='hand2',
                               activebackground='#C82333', activeforeground='white')
        unfriend_btn.pack(side=tk.LEFT, padx=(0, 10))

    def unfriend_user(self, friend):
        """Remove a friend from the friend list after confirmation"""
        # Show confirmation dialog
        result = messagebox.askyesno(
            'Confirm Unfriend', 
            f'Are you sure you want to remove {friend} from your friends?\n\n'
            'This action cannot be undone and you will need to send another '
            'friend request to add them back.',
            icon='warning'
        )
        
        if result:
            try:
                # Send unfriend request to server
                if self.connected and self.sock:
                    print(f"[DEBUG] Sending UNFRIEND request for {friend}")
                    send_json(self.sock, {
                        'type': 'UNFRIEND',
                        'from': self.username,
                        'target': friend
                    })
                    print(f"[DEBUG] UNFRIEND request sent")
                
                # Remove friend locally immediately (don't wait for server response)
                if self.friend_manager.remove(friend):
                    print(f"[DEBUG] Removed {friend} from local friend list")
                    messagebox.showinfo('Success', f'{friend} has been removed from your friends.')
                    
                    # Refresh the friend list to update the UI
                    self.refresh_friendlist()
                    
                    # Close the current chat if it's with the unfriended user
                    if (hasattr(self, 'current_chat') and self.current_chat and 
                        self.current_chat[0] == 'private' and self.current_chat[1] == friend):
                        # Reset to default state
                        self.current_chat = None
                        self.reset_info_section()
                        self.chat_area.config(state='normal')
                        self.chat_area.delete(1.0, tk.END)
                        self.chat_area.insert(tk.END, 'Select a friend or group to start chatting.\n')
                        self.chat_area.config(state='disabled')
                else:
                    print(f"[DEBUG] {friend} was not in local friend list")
                    messagebox.showwarning('Warning', f'{friend} was not in your friends list.')
                    
            except Exception as e:
                print(f"[DEBUG] Error in unfriend_user: {e}")
                messagebox.showerror('Error', f'Failed to unfriend {friend}: {str(e)}')

    def display_message_in_main(self, sender, msg, align=None, timestamp=None):
        """
        Enhanced message display with profile pictures, names, and timestamps for groups
        For private messages, only show timestamps
        """
        from PIL import Image, ImageTk
        import os
        
        self.chat_area.config(state='normal')
        
        # Check if this is a group message
        is_group_message = '(Group' in sender
        
        # Determine profile image path and alignment
        if sender == self.username or (hasattr(self, 'username') and sender.startswith('You')):
            img_path = f'profile_{self.username}.png'
            align = 'right'
            display_name = 'You'
            actual_sender = self.username
        else:
            # Extract sender name from group messages like "sender (Group groupname)"
            if is_group_message:
                actual_sender = sender.split(' (Group')[0]
                group_name = sender.split('(Group ')[1].rstrip(')')
                display_name = actual_sender
            else:
                actual_sender = sender
                display_name = sender
            img_path = f'profile_{actual_sender}.png'
            align = 'left'
        
        # Handle timestamp - use provided timestamp or show placeholder for old messages
        if timestamp:
            try:
                # Parse ISO format timestamp and format for display
                dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%H:%M")
            except:
                # Fallback if timestamp parsing fails - show placeholder for unknown time
                time_str = "--:--"
        else:
            # For old messages without timestamps, show placeholder instead of current time
            time_str = "--:--"
        
        # For private messages, display layout with profile picture and timestamp (no name)
        if not is_group_message:
            # Load profile image for private messages
            profile_img = None
            try:
                if os.path.exists(img_path):
                    pil_img = Image.open(img_path)
                else:
                    pil_img = Image.open('default_dp.png')
                pil_img.thumbnail((40, 40))
                profile_img = ImageTk.PhotoImage(pil_img)
            except Exception:
                try:
                    pil_img = Image.open('default_dp.png')
                    pil_img.thumbnail((40, 40))
                    profile_img = ImageTk.PhotoImage(pil_img)
                except Exception:
                    profile_img = None
            
            # Create main container frame for the entire message
            container_frame = tk.Frame(self.chat_area, bg='white')
            
            # Create the message layout based on alignment
            if align == 'right':
                # Own messages: profile on right, message on left
                message_frame = tk.Frame(container_frame, bg='white')
                message_frame.pack(side=tk.RIGHT, padx=(400, 10), pady=5, anchor='e')
                
                # Create horizontal layout for own messages
                content_frame = tk.Frame(message_frame, bg='white')
                content_frame.pack(anchor='e')
                
                # Profile section (on the right side)
                profile_frame = tk.Frame(content_frame, bg='white')
                profile_frame.pack(side=tk.RIGHT)
                
                # Profile picture
                if profile_img is not None:
                    img_label = tk.Label(profile_frame, image=profile_img, bg='white')
                    img_label.image = profile_img  # Keep reference
                    img_label.pack()
                else:
                    img_label = tk.Label(profile_frame, text='👤', font=('Arial', 24), bg='white', fg='gray')
                    img_label.pack()
                
                # Only timestamp below profile picture (no name for private messages)
                time_label = tk.Label(profile_frame, text=time_str, 
                                     bg='white', fg='#666666', font=('Arial', 8),
                                     justify='center')
                time_label.pack(pady=(2, 0))
                
                # Message bubble (on the left side of profile)
                bubble_frame = tk.Frame(content_frame, bg='white')
                bubble_frame.pack(side=tk.RIGHT, padx=(0, 10))
                
                bubble_bg = '#DCF8C6'  # WhatsApp-like green for own messages
                text_color = '#000000'
                
                bubble = tk.Label(bubble_frame, text=msg, bg=bubble_bg, fg=text_color,
                                  font=('Arial', 11), wraplength=250, justify='left', 
                                  bd=1, relief='solid', padx=12, pady=8,
                                  anchor='w')
                bubble.pack()
                
            else:
                # Others' messages: profile on left, message on right
                message_frame = tk.Frame(container_frame, bg='white')
                message_frame.pack(side=tk.LEFT, padx=(10, 100), pady=5, anchor='w')
                
                # Create horizontal layout for other's messages
                content_frame = tk.Frame(message_frame, bg='white')
                content_frame.pack(anchor='w')
                
                # Profile section (on the left)
                profile_frame = tk.Frame(content_frame, bg='white')
                profile_frame.pack(side=tk.LEFT)
                
                # Profile picture
                if profile_img is not None:
                    img_label = tk.Label(profile_frame, image=profile_img, bg='white')
                    img_label.image = profile_img  # Keep reference
                    img_label.pack()
                else:
                    img_label = tk.Label(profile_frame, text='👤', font=('Arial', 24), bg='white', fg='gray')
                    img_label.pack()
                
                # Only timestamp below profile picture (no name for private messages)
                time_label = tk.Label(profile_frame, text=time_str, 
                                     bg='white', fg='#666666', font=('Arial', 8),
                                     justify='center')
                time_label.pack(pady=(2, 0))
                
                # Message bubble (on the right of profile)
                bubble_frame = tk.Frame(content_frame, bg='white')
                bubble_frame.pack(side=tk.LEFT, padx=(10, 0))
                
                bubble_bg = '#F0F0F0'  # Light gray for other's messages
                text_color = '#000000'
                
                bubble = tk.Label(bubble_frame, text=msg, bg=bubble_bg, fg=text_color,
                                  font=('Arial', 11), wraplength=250, justify='left', 
                                  bd=1, relief='solid', padx=12, pady=8,
                                  anchor='w')
                bubble.pack()
            
            # Add container to chat area
            self.chat_area.window_create(tk.END, window=container_frame)
            self.chat_area.insert(tk.END, '\n')
            self.chat_area.config(state='disabled')
            self.chat_area.see(tk.END)
            return
        
        # For group messages, load profile image and show full layout
        profile_img = None
        try:
            if os.path.exists(img_path):
                pil_img = Image.open(img_path)
            else:
                pil_img = Image.open('default_dp.png')
            pil_img.thumbnail((40, 40))  # Slightly larger profile picture
            profile_img = ImageTk.PhotoImage(pil_img)
        except Exception:
            try:
                pil_img = Image.open('default_dp.png')
                pil_img.thumbnail((40, 40))
                profile_img = ImageTk.PhotoImage(pil_img)
            except Exception:
                profile_img = None
        
        # Create main container frame for the entire message
        container_frame = tk.Frame(self.chat_area, bg='white')
        
        # Create the message layout for group messages
        if align == 'right':
            # Own messages: aligned to the right
            message_frame = tk.Frame(container_frame, bg='white')
            message_frame.pack(side=tk.RIGHT, padx=(400, 10), pady=5, anchor='e')
            
            # Create horizontal layout for own messages
            content_frame = tk.Frame(message_frame, bg='white')
            content_frame.pack(anchor='e')
            
            # Profile section (on the right side)
            profile_frame = tk.Frame(content_frame, bg='white')
            profile_frame.pack(side=tk.RIGHT)
            
            # Profile picture
            if profile_img is not None:
                img_label = tk.Label(profile_frame, image=profile_img, bg='white')
                img_label.image = profile_img  # Keep reference
                img_label.pack()
            else:
                img_label = tk.Label(profile_frame, text='👤', font=('Arial', 24), bg='white', fg='gray')
                img_label.pack()
            
            # Name and time below profile picture (small text, center aligned)
            name_time_label = tk.Label(profile_frame, text=f"{display_name}\n{time_str}", 
                                       bg='white', fg='#666666', font=('Arial', 8),
                                       justify='center')
            name_time_label.pack(pady=(2, 0))
            
            # Message bubble (on the left side of profile)
            bubble_frame = tk.Frame(content_frame, bg='white')
            bubble_frame.pack(side=tk.RIGHT, padx=(0, 10))
            
            bubble_bg = '#DCF8C6'  # WhatsApp-like green for own messages
            text_color = '#000000'
            
            bubble = tk.Label(bubble_frame, text=msg, bg=bubble_bg, fg=text_color,
                              font=('Arial', 11), wraplength=250, justify='left', 
                              bd=1, relief='solid', padx=12, pady=8,
                              anchor='w')
            bubble.pack()
            
        else:
            # Other's messages: aligned to the left
            message_frame = tk.Frame(container_frame, bg='white')
            message_frame.pack(side=tk.LEFT, padx=(10, 100), pady=5, anchor='w')
            
            # Create horizontal layout for other's messages
            content_frame = tk.Frame(message_frame, bg='white')
            content_frame.pack(anchor='w')
            
            # Profile section (on the left)
            profile_frame = tk.Frame(content_frame, bg='white')
            profile_frame.pack(side=tk.LEFT)
            
            # Profile picture
            if profile_img is not None:
                img_label = tk.Label(profile_frame, image=profile_img, bg='white')
                img_label.image = profile_img  # Keep reference
                img_label.pack()
            else:
                img_label = tk.Label(profile_frame, text='👤', font=('Arial', 24), bg='white', fg='gray')
                img_label.pack()
            
            # Name and time below profile picture (small text, center aligned)
            name_time_label = tk.Label(profile_frame, text=f"{display_name}\n{time_str}", 
                                       bg='white', fg='#666666', font=('Arial', 8),
                                       justify='center')
            name_time_label.pack(pady=(2, 0))
            
            # Message bubble (on the right of profile)
            bubble_frame = tk.Frame(content_frame, bg='white')
            bubble_frame.pack(side=tk.LEFT, padx=(10, 0))
            
            bubble_bg = '#F0F0F0'  # Light gray for other's messages
            text_color = '#000000'
            
            bubble = tk.Label(bubble_frame, text=msg, bg=bubble_bg, fg=text_color,
                              font=('Arial', 11), wraplength=250, justify='left', 
                              bd=1, relief='solid', padx=12, pady=8,
                              anchor='w')
            bubble.pack()
        
        # Insert the container into chat area
        self.chat_area.window_create(tk.END, window=container_frame)
        self.chat_area.insert(tk.END, '\n')
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)

    def display_file_in_main(self, sender, filename, filedata, align='left', timestamp=None):
        """
        Enhanced file display with profile pictures, names, and timestamps for groups
        For private messages, only show timestamps
        """
        import base64
        import tempfile
        from tkinter import Button, filedialog
        from PIL import Image, ImageTk
        
        # Check if this is a group message
        is_group_message = '(Group' in sender
        
        # Determine alignment and sender info
        if sender == self.username or (hasattr(self, 'username') and sender.startswith('You')):
            align = 'right'
            display_name = 'You'
            actual_sender = self.username
        else:
            if is_group_message:
                actual_sender = sender.split(' (Group')[0]
                display_name = actual_sender
            else:
                actual_sender = sender
                display_name = sender
            align = 'left'
        
        # Get timestamp - use provided timestamp or show placeholder for old messages
        if timestamp:
            try:
                # Parse ISO format timestamp and format for display
                dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%H:%M")
            except:
                # Fallback if timestamp parsing fails - show placeholder for unknown time
                time_str = "--:--"
        else:
            # For old messages without timestamps, show placeholder instead of current time
            time_str = "--:--"
        
        # For private messages, display layout with profile picture and timestamp (no name)
        if not is_group_message:
            self.chat_area.config(state='normal')
            
            # Create main container frame
            container_frame = tk.Frame(self.chat_area, bg='white')
            
            # Create the message layout based on alignment
            if align == 'right':
                # Own files: profile on right, file on left
                message_frame = tk.Frame(container_frame, bg='white')
                message_frame.pack(side=tk.RIGHT, padx=(400, 10), pady=5, anchor='e')
                
                # Create horizontal layout
                content_frame = tk.Frame(message_frame, bg='white')
                content_frame.pack(anchor='e')
                
                # Profile section (on the right side)
                profile_frame = tk.Frame(content_frame, bg='white')
                profile_frame.pack(side=tk.RIGHT)
                
                # Load and display profile image
                img_path = f'profile_{actual_sender}.png'
                profile_img = None
                try:
                    if os.path.exists(img_path):
                        pil_img = Image.open(img_path)
                    else:
                        pil_img = Image.open('default_dp.png')
                    pil_img.thumbnail((40, 40))
                    profile_img = ImageTk.PhotoImage(pil_img)
                except Exception:
                    try:
                        pil_img = Image.open('default_dp.png')
                        pil_img.thumbnail((40, 40))
                        profile_img = ImageTk.PhotoImage(pil_img)
                    except Exception:
                        profile_img = None
                
                # Profile picture
                if profile_img is not None:
                    img_label = tk.Label(profile_frame, image=profile_img, bg='white')
                    img_label.image = profile_img  # Keep reference
                    img_label.pack()
                else:
                    img_label = tk.Label(profile_frame, text='👤', font=('Arial', 24), bg='white', fg='gray')
                    img_label.pack()
                
                # Only timestamp below profile picture (no name for private messages)
                time_label = tk.Label(profile_frame, text=time_str, 
                                     bg='white', fg='#666666', font=('Arial', 8),
                                     justify='center')
                time_label.pack(pady=(2, 0))
                
                # File bubble (on the left side of profile)
                bubble_frame = tk.Frame(content_frame, bg='white')
                bubble_frame.pack(side=tk.RIGHT, padx=(0, 10))
                
                file_bubble = tk.Frame(bubble_frame, bg='#DCF8C6', relief='solid', bd=1)
                file_bubble.pack(padx=5, pady=5)
                
            else:
                # Others' files: profile on left, file on right
                message_frame = tk.Frame(container_frame, bg='white')
                message_frame.pack(side=tk.LEFT, padx=(10, 100), pady=5, anchor='w')
                
                # Create horizontal layout
                content_frame = tk.Frame(message_frame, bg='white')
                content_frame.pack(anchor='w')
                
                # Profile section (on the left)
                profile_frame = tk.Frame(content_frame, bg='white')
                profile_frame.pack(side=tk.LEFT)
                
                # Load and display profile image
                img_path = f'profile_{actual_sender}.png'
                profile_img = None
                try:
                    if os.path.exists(img_path):
                        pil_img = Image.open(img_path)
                    else:
                        pil_img = Image.open('default_dp.png')
                    pil_img.thumbnail((40, 40))
                    profile_img = ImageTk.PhotoImage(pil_img)
                except Exception:
                    try:
                        pil_img = Image.open('default_dp.png')
                        pil_img.thumbnail((40, 40))
                        profile_img = ImageTk.PhotoImage(pil_img)
                    except Exception:
                        profile_img = None
                
                # Profile picture
                if profile_img is not None:
                    img_label = tk.Label(profile_frame, image=profile_img, bg='white')
                    img_label.image = profile_img  # Keep reference
                    img_label.pack()
                else:
                    img_label = tk.Label(profile_frame, text='👤', font=('Arial', 24), bg='white', fg='gray')
                    img_label.pack()
                
                # Only timestamp below profile picture (no name for private messages)
                time_label = tk.Label(profile_frame, text=time_str, 
                                     bg='white', fg='#666666', font=('Arial', 8),
                                     justify='center')
                time_label.pack(pady=(2, 0))
                
                # File bubble (on the right of profile)
                bubble_frame = tk.Frame(content_frame, bg='white')
                bubble_frame.pack(side=tk.LEFT, padx=(10, 0))
                
                file_bubble = tk.Frame(bubble_frame, bg='#F0F0F0', relief='solid', bd=1)
                file_bubble.pack(padx=5, pady=5)
            
            # Display file content in bubble
            self._current_file_sender = sender  # Set for download button logic
            self._display_file_content_in_bubble(file_bubble, filename, filedata, 
                                                file_bubble.cget('bg'))
            
            # Add container to chat area
            self.chat_area.window_create(tk.END, window=container_frame)
            self.chat_area.insert(tk.END, '\n')
            self.chat_area.config(state='disabled')
            self.chat_area.see(tk.END)
            return
        
        # For group messages, load profile image and show full layout
        img_path = f'profile_{actual_sender}.png'
        profile_img = None
        try:
            if os.path.exists(img_path):
                pil_img = Image.open(img_path)
            else:
                pil_img = Image.open('default_dp.png')
            pil_img.thumbnail((40, 40))
            profile_img = ImageTk.PhotoImage(pil_img)
        except Exception:
            try:
                pil_img = Image.open('default_dp.png')
                pil_img.thumbnail((40, 40))
                profile_img = ImageTk.PhotoImage(pil_img)
            except Exception:
                profile_img = None
        
        # For group messages, display with profile pictures and names
        self.chat_area.config(state='normal')
        
        # Create main container frame for the file message
        container_frame = tk.Frame(self.chat_area, bg='white')
        
        # Create the message layout similar to text messages
        if align == 'right':
            # Own file messages: aligned to the right
            message_frame = tk.Frame(container_frame, bg='white')
            message_frame.pack(side=tk.RIGHT, padx=(400, 10), pady=5, anchor='e')
            
            content_frame = tk.Frame(message_frame, bg='white')
            content_frame.pack(anchor='e')
            
            # Profile section (on the right side)
            profile_frame = tk.Frame(content_frame, bg='white')
            profile_frame.pack(side=tk.RIGHT)
            
            # Add profile picture and name/time to profile section
            if profile_img is not None:
                img_label = tk.Label(profile_frame, image=profile_img, bg='white')
                img_label.image = profile_img  # Keep reference
                img_label.pack()
            else:
                img_label = tk.Label(profile_frame, text='👤', font=('Arial', 24), bg='white', fg='gray')
                img_label.pack()
            
            # Name and time below profile picture
            name_time_label = tk.Label(profile_frame, text=f"{display_name}\n{time_str}", 
                                       bg='white', fg='#666666', font=('Arial', 8),
                                       justify='center')
            name_time_label.pack(pady=(2, 0))
            
            # File bubble (on the left side of profile)
            bubble_frame = tk.Frame(content_frame, bg='white')
            bubble_frame.pack(side=tk.RIGHT, padx=(0, 10))
            
            bubble_bg = '#DCF8C6'  # WhatsApp-like green for own messages
            
            file_bubble = tk.Frame(bubble_frame, bg=bubble_bg, relief='solid', bd=1)
            file_bubble.pack(padx=5, pady=5)
            
        else:
            # Other's file messages: aligned to the left
            message_frame = tk.Frame(container_frame, bg='white')
            message_frame.pack(side=tk.LEFT, padx=(10, 100), pady=5, anchor='w')
            
            content_frame = tk.Frame(message_frame, bg='white')
            content_frame.pack(anchor='w')
            
            # Profile section (on the left)
            profile_frame = tk.Frame(content_frame, bg='white')
            profile_frame.pack(side=tk.LEFT)
            
            # Add profile picture and name/time to profile section
            if profile_img is not None:
                img_label = tk.Label(profile_frame, image=profile_img, bg='white')
                img_label.image = profile_img  # Keep reference
                img_label.pack()
            else:
                img_label = tk.Label(profile_frame, text='👤', font=('Arial', 24), bg='white', fg='gray')
                img_label.pack()
            
            # Name and time below profile picture
            name_time_label = tk.Label(profile_frame, text=f"{display_name}\n{time_str}", 
                                       bg='white', fg='#666666', font=('Arial', 8),
                                       justify='center')
            name_time_label.pack(pady=(2, 0))
            
            # File bubble (on the right of profile)
            bubble_frame = tk.Frame(content_frame, bg='white')
            bubble_frame.pack(side=tk.LEFT, padx=(10, 0))
            
            bubble_bg = '#F0F0F0'  # Light gray for other's messages
            
            file_bubble = tk.Frame(bubble_frame, bg=bubble_bg, relief='solid', bd=1)
            file_bubble.pack(padx=5, pady=5)
        
        # Display file content in bubble
        self._current_file_sender = sender  # Set for download button logic
        self._display_file_content_in_bubble(file_bubble, filename, filedata, bubble_bg)
        
        # Insert the container into chat area
        self.chat_area.window_create(tk.END, window=container_frame)
        self.chat_area.insert(tk.END, '\n')
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)

    def _display_file_content_in_bubble(self, bubble_frame, filename, filedata, bubble_bg):
        """Helper function to display file content in a bubble"""
        import base64
        import tempfile
        import os
        from PIL import Image, ImageTk
        from tkinter import Button, filedialog, messagebox
        
        ext = os.path.splitext(filename)[1].lower()
        is_image = ext in ['.png', '.jpg', '.jpeg', '.gif']
        temp_path = os.path.join(tempfile.gettempdir(), f'temp_{filename}')
        
        try:
            with open(temp_path, 'wb') as f:
                f.write(base64.b64decode(filedata))
        except Exception:
            tk.Label(bubble_frame, text=f"❌ Failed to load: {filename}", 
                    bg=bubble_bg, fg='#000000', font=('Arial', 10)).pack(padx=8, pady=8)
            return
        
        # File content display
        if is_image:
            try:
                # Display image thumbnail
                pil_img = Image.open(temp_path)
                pil_img.thumbnail((150, 150))
                img = ImageTk.PhotoImage(pil_img)
                
                if not hasattr(self, '_img_refs_main'):
                    self._img_refs_main = []
                self._img_refs_main.append(img)
                
                # Image in the bubble
                img_display = tk.Label(bubble_frame, image=img, bg=bubble_bg)
                img_display.pack(padx=8, pady=8)
                
                # File name label
                name_label = tk.Label(bubble_frame, text=f"📷 {filename}", 
                                     bg=bubble_bg, fg='#000000', font=('Arial', 10, 'bold'))
                name_label.pack(padx=8, pady=(0, 5))
                
            except Exception:
                # Fallback if image can't be displayed
                tk.Label(bubble_frame, text=f"📷 Image: {filename}", 
                        bg=bubble_bg, fg='#000000', font=('Arial', 10, 'bold')).pack(padx=8, pady=8)
        else:
            # Non-image file
            file_icon = "📄"
            if ext in ['.pdf']: file_icon = "📋"
            elif ext in ['.doc', '.docx']: file_icon = "📝"
            elif ext in ['.xls', '.xlsx']: file_icon = "📊"
            elif ext in ['.zip', '.rar']: file_icon = "📦"
            elif ext in ['.mp3', '.wav']: file_icon = "🎵"
            elif ext in ['.mp4', '.avi']: file_icon = "🎬"
            
            tk.Label(bubble_frame, text=f"{file_icon} {filename}", 
                    bg=bubble_bg, fg='#000000', font=('Arial', 10, 'bold')).pack(padx=8, pady=8)
        
        # Add download button for received files (not for own files)
        sender = getattr(self, '_current_file_sender', '')
        if sender != self.username and not sender.startswith('You'):
            def download():
                save_path = filedialog.asksaveasfilename(initialfile=filename)
                if save_path:
                    try:
                        with open(temp_path, 'rb') as src, open(save_path, 'wb') as dst:
                            dst.write(src.read())
                        messagebox.showinfo('Success', f'File saved to {save_path}')
                    except Exception as e:
                        messagebox.showerror('Error', f'Failed to save file: {e}')
            
            download_btn = tk.Button(bubble_frame, text='💾 Download', command=download,
                                   bg='#4CAF50', fg='white', font=('Arial', 9, 'bold'),
                                   relief='flat', cursor='hand2')
            download_btn.pack(padx=8, pady=(0, 8))

    def logout(self):
        # Save joined groups before logout
        self.save_joined_groups()
        
        # Mark as disconnected and reset UI, but do NOT close the socket
        self.connected = False
        # Reset info section
        if hasattr(self, 'info_content_frame'):
            self.reset_info_section()
        # Optionally, notify server of logout (if protocol supports it)
        try:
            send_json(self.sock, {'type': 'LOGOUT', 'name': self.username})
        except Exception:
            pass
        # Wait for listener thread to exit
        if hasattr(self, 'listener_thread') and self.listener_thread and self.listener_thread.is_alive():
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            self.listener_thread.join(timeout=1)
        # Close all notification windows
        for notif in list(self.notifications.values()):
            try:
                notif.destroy()
            except Exception:
                pass
        self.notifications.clear()
        self.group_name = None
        self.build_login()

    def show_friend_request_dialog(self, sender, sender_info):
        """Show detailed friend request dialog with user information"""
        print(f"[FRIEND REQUEST DIALOG] ===== OPENING DIALOG =====")
        print(f"[FRIEND REQUEST DIALOG] Sender: {sender}")
        print(f"[FRIEND REQUEST DIALOG] Sender info: {sender_info}")
        
        # Validate inputs
        if not sender:
            print(f"[FRIEND REQUEST DIALOG] ERROR: No sender provided!")
            messagebox.showerror('Error', 'Invalid friend request data.')
            return
            
        if not sender_info:
            print(f"[FRIEND REQUEST DIALOG] WARNING: No sender_info, using defaults")
            sender_info = {'name': sender, 'dept': 'Unknown', 'session': 'Unknown'}
        
        # Create friend request dialog window
        dialog = tk.Toplevel(self.master)
        dialog.title('Friend Request')
        dialog.geometry('450x400')
        dialog.resizable(False, False)
        dialog.grab_set()  # Make dialog modal
        
        # Center the dialog
        dialog.transient(self.master)
        
        # Main frame
        main_frame = tk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text='Friend Request', 
                              font=('Arial', 16, 'bold'), fg='blue')
        title_label.pack(pady=(0, 15))
        
        # Request message
        request_msg = tk.Label(main_frame, 
                              text=f'{sender} wants to add you as a friend',
                              font=('Arial', 12, 'bold'))
        request_msg.pack(pady=(0, 10))
        
        # User details in a simple box
        info_box = tk.Frame(main_frame, bg='lightgray', relief='solid', bd=2)
        info_box.pack(fill=tk.X, pady=10)
        
        tk.Label(info_box, text='User Information:', 
                font=('Arial', 11, 'bold'), bg='lightgray').pack(pady=5)
        
        # User details
        tk.Label(info_box, text=f"Username: {sender_info.get('name', sender)}", 
                bg='lightgray', font=('Arial', 10)).pack(pady=2)
        tk.Label(info_box, text=f"Department: {sender_info.get('dept', 'Unknown')}", 
                bg='lightgray', font=('Arial', 10)).pack(pady=2)
        tk.Label(info_box, text=f"Session: {sender_info.get('session', 'Unknown')}", 
                bg='lightgray', font=('Arial', 10)).pack(pady=2)
        
        # Add some padding
        tk.Label(info_box, text='', bg='lightgray').pack(pady=3)
        
        # Button functions
        def accept_request():
            print(f"[FRIEND_REQUEST_ACCEPT] ===== ACCEPTING FRIEND REQUEST =====")
            print(f"[FRIEND_REQUEST_ACCEPT] User {self.username} accepting request from {sender}")
            try:
                # Force reload friend list from file first
                self.friend_manager.reload()
                # Add to friend list locally FIRST
                self.friend_manager.add(sender)
                print(f"[FRIEND_REQUEST_ACCEPT] Added {sender} to local friend list")
                print(f"[FRIEND_REQUEST_ACCEPT] Current friends: {self.friend_manager.get_all()}")
                
                # Send acceptance to server
                response_data = {
                    'type': 'FRIEND_REQUEST_RESPONSE',
                    'from': self.username,
                    'to': sender,
                    'accepted': True
                }
                print(f"[FRIEND_REQUEST_ACCEPT] Sending to server: {response_data}")
                send_json(self.sock, response_data)
                print(f"[FRIEND_REQUEST_ACCEPT] Sent acceptance to server successfully")
                
                # Refresh friend list display
                self.refresh_friendlist()
                print(f"[FRIEND_REQUEST_ACCEPT] Refreshed friend list display")
                
                # Close dialog
                dialog.destroy()
                
                # Show success message
                messagebox.showinfo('Friend Added', 
                                  f'{sender} has been added to your friends!')
                print(f"[FRIEND_REQUEST_ACCEPT] ===== ACCEPTANCE COMPLETE =====")
                
                # Remove notification from home
                self.remove_notification(sender)
                
            except Exception as e:
                print(f"DEBUG: Error in accept_request: {e}")
                messagebox.showerror('Error', f'Failed to accept friend request: {e}')
                dialog.destroy()
        
        def ignore_request():
            print(f"DEBUG: Ignore button clicked for {sender}")
            try:
                # Send decline to server
                send_json(self.sock, {
                    'type': 'FRIEND_REQUEST_RESPONSE',
                    'from': self.username,
                    'to': sender,
                    'accepted': False
                })
                print(f"DEBUG: Sent decline to server")
                
                # Close dialog
                dialog.destroy()
                
                # Show info message
                messagebox.showinfo('Friend Request', 
                                  f'You declined the friend request from {sender}.')
                
                # Remove notification from home
                self.remove_notification(sender)
                
            except Exception as e:
                print(f"DEBUG: Error in ignore_request: {e}")
                messagebox.showerror('Error', f'Failed to decline friend request: {e}')
                dialog.destroy()
        
        # Action buttons frame
        action_frame = tk.Frame(main_frame)
        action_frame.pack(pady=30)
        
        # Accept button
        accept_btn = tk.Button(action_frame, text='✓ Accept', 
                              command=accept_request,
                              bg='#28A745', fg='white', 
                              font=('Arial', 14, 'bold'),
                              width=12, height=2,
                              relief='raised', bd=3,
                              cursor='hand2',
                              activebackground='#218838',
                              activeforeground='white')
        accept_btn.pack(side=tk.LEFT, padx=30)
        
        # Ignore button  
        ignore_btn = tk.Button(action_frame, text='✗ Ignore', 
                              command=ignore_request,
                              bg='#DC3545', fg='white', 
                              font=('Arial', 14, 'bold'),
                              width=12, height=2,
                              relief='raised', bd=3,
                              cursor='hand2',
                              activebackground='#C82333',
                              activeforeground='white')
        ignore_btn.pack(side=tk.RIGHT, padx=30)
        
        # Add button hover effects
        def on_accept_enter(e):
            accept_btn.config(bg='#218838')
        def on_accept_leave(e):
            accept_btn.config(bg='#28A745')
        def on_ignore_enter(e):
            ignore_btn.config(bg='#C82333')
        def on_ignore_leave(e):
            ignore_btn.config(bg='#DC3545')
            
        accept_btn.bind('<Enter>', on_accept_enter)
        accept_btn.bind('<Leave>', on_accept_leave)
        ignore_btn.bind('<Enter>', on_ignore_enter)
        ignore_btn.bind('<Leave>', on_ignore_leave)
        
        # Handle window close (treat as ignore)
        dialog.protocol("WM_DELETE_WINDOW", ignore_request)
        
        # Focus on dialog
        dialog.focus_set()
        
        print(f"DEBUG: Friend request dialog created and displayed")

    def show_group_invitation_dialog(self, inviter, group_name, sender_info):
        """Show detailed group invitation dialog with inviter information"""
        print(f"DEBUG: Opening group invitation dialog for {group_name} from {inviter}")
        
        # Validate inputs
        if not inviter or not group_name:
            messagebox.showerror('Error', 'Invalid group invitation data.')
            return
            
        if not sender_info:
            sender_info = {'name': inviter, 'dept': 'Unknown', 'session': 'Unknown'}
        
        # Create group invitation dialog window
        dialog = tk.Toplevel(self.master)
        dialog.title('Group Invitation')
        dialog.geometry('500x450')
        dialog.resizable(False, False)
        dialog.grab_set()  # Make dialog modal
        
        # Center the dialog
        dialog.transient(self.master)
        
        # Main frame
        main_frame = tk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text='Group Invitation', 
                              font=('Arial', 16, 'bold'), fg='green')
        title_label.pack(pady=(0, 15))
        
        # Invitation message
        invite_msg = tk.Label(main_frame, 
                             text=f'{inviter} invited you to join',
                             font=('Arial', 12, 'bold'))
        invite_msg.pack(pady=(0, 5))
        
        # Group name display
        group_label = tk.Label(main_frame, 
                              text=f'"{group_name}"',
                              font=('Arial', 14, 'bold'), fg='blue')
        group_label.pack(pady=(0, 15))
        
        # Inviter details in a simple box
        info_box = tk.Frame(main_frame, bg='lightblue', relief='solid', bd=2)
        info_box.pack(fill=tk.X, pady=10)
        
        tk.Label(info_box, text='Invited by:', 
                font=('Arial', 11, 'bold'), bg='lightblue').pack(pady=5)
        
        # Inviter details
        tk.Label(info_box, text=f"Username: {sender_info.get('name', inviter)}", 
                bg='lightblue', font=('Arial', 10)).pack(pady=2)
        tk.Label(info_box, text=f"Department: {sender_info.get('dept', 'Unknown')}", 
                bg='lightblue', font=('Arial', 10)).pack(pady=2)
        tk.Label(info_box, text=f"Session: {sender_info.get('session', 'Unknown')}", 
                bg='lightblue', font=('Arial', 10)).pack(pady=2)
        
        # Add some padding
        tk.Label(info_box, text='', bg='lightblue').pack(pady=3)
        
        # Group info
        group_info_label = tk.Label(main_frame, 
                                   text='Would you like to join this group?',
                                   font=('Arial', 11))
        group_info_label.pack(pady=15)
        
        # Button functions
        def accept_invitation():
            print(f"DEBUG: Accept button clicked for group {group_name}")
            try:
                # Send acceptance to server
                send_json(self.sock, {
                    'type': 'GROUP_INVITE_RESPONSE',
                    'from': self.username,
                    'group_name': group_name,
                    'inviter': inviter,
                    'accepted': True
                })
                print(f"DEBUG: Sent acceptance to server for group {group_name}")
                
                # Close dialog
                dialog.destroy()
                
                # Note: Success message will be shown when GROUP_JOIN_SUCCESS is received
                
            except Exception as e:
                print(f"DEBUG: Error in accept_invitation: {e}")
                messagebox.showerror('Error', f'Failed to accept group invitation: {e}')
                dialog.destroy()
        
        def decline_invitation():
            print(f"DEBUG: Decline button clicked for group {group_name}")
            try:
                # Send decline to server
                send_json(self.sock, {
                    'type': 'GROUP_INVITE_RESPONSE',
                    'from': self.username,
                    'group_name': group_name,
                    'inviter': inviter,
                    'accepted': False
                })
                print(f"DEBUG: Sent decline to server for group {group_name}")
                
                # Close dialog
                dialog.destroy()
                
                # Show info message
                messagebox.showinfo('Group Invitation', 
                                  f'You declined the invitation to join "{group_name}".')
                
            except Exception as e:
                print(f"DEBUG: Error in decline_invitation: {e}")
                messagebox.showerror('Error', f'Failed to decline group invitation: {e}')
                dialog.destroy()
        
        # Action buttons frame
        action_frame = tk.Frame(main_frame)
        action_frame.pack(pady=30)
        
        # Accept button
        accept_btn = tk.Button(action_frame, text='✓ Accept', 
                              command=accept_invitation,
                              bg='#28A745', fg='white', 
                              font=('Arial', 11, 'bold'),
                              width=15,
                              relief='raised', bd=3,
                              cursor='hand2',
                              activebackground='#218838',
                              activeforeground='white')
        accept_btn.pack(side=tk.LEFT, padx=30)
        
        # Decline button  
        decline_btn = tk.Button(action_frame, text='✗ Decline', 
                               command=decline_invitation,
                               bg='#DC3545', fg='white', 
                               font=('Arial', 11, 'bold'),
                               width=15,
                               relief='raised', bd=3,
                               cursor='hand2',
                               activebackground='#C82333',
                               activeforeground='white')
        decline_btn.pack(side=tk.RIGHT, padx=30)
        
        # Add button hover effects
        def on_accept_enter(e):
            accept_btn.config(bg='#218838')
        def on_accept_leave(e):
            accept_btn.config(bg='#28A745')
        def on_decline_enter(e):
            decline_btn.config(bg='#C82333')
        def on_decline_leave(e):
            decline_btn.config(bg='#DC3545')
            
        accept_btn.bind('<Enter>', on_accept_enter)
        accept_btn.bind('<Leave>', on_accept_leave)
        decline_btn.bind('<Enter>', on_decline_enter)
        decline_btn.bind('<Leave>', on_decline_leave)
        
        # Handle window close (treat as decline)
        dialog.protocol("WM_DELETE_WINDOW", decline_invitation)
        
        # Focus on dialog
        dialog.focus_set()
        
        print(f"DEBUG: Group invitation dialog created and displayed")

    def remove_notification(self, sender):
        """Remove notification from the notification list"""
        if not hasattr(self, 'notification_listbox'):
            return
            
        # Find and remove the notification (iterate backwards to avoid index issues)
        for i in range(self.notification_listbox.size() - 1, -1, -1):
            display = self.notification_listbox.get(i)
            if (display.startswith(f'[FRIEND REQUEST] {sender}:') or 
                display.startswith(f'[GROUP INVITE] {sender}:') or 
                display.startswith(f'{sender}:')):
                self.notification_listbox.delete(i)
                # Don't break here - remove all notifications from this sender
        
        # Remove from notifications dict
        if sender in self.notifications_home:
            del self.notifications_home[sender]

    # ...existing code...

if __name__ == '__main__':
    root = tk.Tk()
    app = ChatClient(root)
    root.mainloop()
