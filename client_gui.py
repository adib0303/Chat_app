import socket
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
import json
import os

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 9999

def send_json(sock, obj):
    data = json.dumps(obj).encode()
    length = f'{len(data):08d}'.encode()
    sock.sendall(length + data)

def recv_full(sock, length):
    data = b''
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise ConnectionError('Socket closed')
        data += more
    return data

def recv_json(sock):
    length_bytes = b''
    while len(length_bytes) < 8:
        more = sock.recv(8 - len(length_bytes))
        if not more:
            raise ConnectionError('Socket closed')
        length_bytes += more
    length = int(length_bytes.decode())
    data = recv_full(sock, length)
    return json.loads(data.decode())

class FriendManager:
    def __init__(self, username):
        self.username = username
        self.file = f"friends_{username}.json"
        self.friends = set()
        self.load()

    def load(self):
        if os.path.exists(self.file):
            with open(self.file) as f:
                self.friends = set(json.load(f))

    def save(self):
        with open(self.file, 'w') as f:
            json.dump(list(self.friends), f)

    def add(self, friend):
        self.friends.add(friend)
        self.save()

    def is_friend(self, friend):
        return friend in self.friends

    def get_all(self):
        return list(self.friends)

class ChatClient:
    def load_status_icons(self):
        from PIL import Image, ImageTk
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
        self.find_friend_window = None
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
        self.sock = socket.socket()
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
        # (No Quit button here; only on login page)

    def quit_app(self):
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
            self.sock.connect((SERVER_HOST, SERVER_PORT))
            send_json(self.sock, {'type': 'REGISTER', 'data': self.info})
            resp = recv_json(self.sock)
            if resp.get('type') == 'REGISTER_SUCCESS':
                self.connected = True
                self.username = name
                self.friend_manager = FriendManager(name)
                self.build_main()
                self.refresh_friendlist()
                threading.Thread(target=self.listen_server, daemon=True).start()
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
            self.sock.connect((SERVER_HOST, SERVER_PORT))
            send_json(self.sock, {'type': 'LOGIN', 'name': name, 'password': password})
            resp = recv_json(self.sock)
            if resp.get('type') == 'LOGIN_SUCCESS':
                self.connected = True
                self.username = name
                self.friend_manager = FriendManager(name)
                self.build_main()
                self.refresh_friendlist()
                self.listener_thread = threading.Thread(target=self.listen_server, daemon=True)
                self.listener_thread.start()
            else:
                messagebox.showerror('Error', resp.get('reason', 'Login failed!'))
        except Exception as e:
            messagebox.showerror('Error', f'Could not connect: {e}')


    def build_main(self):
        self.clear_window()
        from PIL import Image, ImageTk
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
        from PIL import Image, ImageTk
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
        tk.Label(profile_frame, text=self.username, font=('Arial', 16, 'bold')).pack(side=tk.LEFT)
        tk.Button(profile_frame, text='Edit Profile', command=self.edit_profile).pack(side=tk.LEFT, padx=10)
        # User/Group controls
        btns_frame = tk.Frame(center_frame)
        btns_frame.pack(anchor='nw', padx=5, pady=5, fill=tk.X)
        tk.Button(btns_frame, text='Refresh Friends', command=self.request_user_list).pack(side=tk.LEFT, padx=2)
        tk.Button(btns_frame, text='Find Friend', command=self.find_friend).pack(side=tk.LEFT, padx=2)
        tk.Button(btns_frame, text='Create Group', command=self.create_group).pack(side=tk.LEFT, padx=2)
        tk.Button(btns_frame, text='Join Group', command=self.join_group).pack(side=tk.LEFT, padx=2)

        # Chat area (shared for private/group)
        self.chat_area = scrolledtext.ScrolledText(center_frame, state='disabled', height=15)
        self.chat_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
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
        self.joined_groups = set()
        self.refresh_joined_groups()

        self.request_user_list()  # Always request latest online info from server
        # self.refresh_friendlist() will be called after LIST_RESPONSE

    def send_file_to_current(self):
        # Send file to current chat (private or group)
        if self.current_chat is None:
            messagebox.showinfo('Info', 'Select a friend or group to send a file.')
            return
        chat_type, name = self.current_chat
        if chat_type == 'private':
            self.send_file(name)
        elif chat_type == 'group':
            self.send_file_to_group()


        # Right: Notifications and Joined Groups
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
        self.joined_groups = set()
        self.refresh_joined_groups()

        self.request_user_list()  # Always request latest online info from server
        # self.refresh_friendlist() will be called after LIST_RESPONSE

    def refresh_joined_groups(self):
        # Update the joined groups listbox
        if not hasattr(self, 'joined_groups_listbox'):
            return
        self.joined_groups_listbox.delete(0, tk.END)
        for g in sorted(self.joined_groups):
            self.joined_groups_listbox.insert(tk.END, g)

    def add_joined_group(self, group_name):
        if not hasattr(self, 'joined_groups'):
            self.joined_groups = set()
        self.joined_groups.add(group_name)
        self.refresh_joined_groups()

    def remove_joined_group(self, group_name):
        if hasattr(self, 'joined_groups') and group_name in self.joined_groups:
            self.joined_groups.remove(group_name)
            self.refresh_joined_groups()

    def edit_profile(self):
        from tkinter import filedialog
        from PIL import Image
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
        img_frame = tk.Frame(win)
        img_frame.pack(pady=10)
        img_label = tk.Label(img_frame, text='No image selected')
        img_label.pack()
        selected_img_path = [self.profile_pic_path if os.path.exists(self.profile_pic_path) else None]
        def select_img():
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
            if selected_img_path[0]:
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
        self.group_chat_area.config(state='normal')
        self.group_chat_area.insert(tk.END, msg + '\n')
        self.group_chat_area.config(state='disabled')
        self.group_chat_area.see(tk.END)

    def send_file_to_group(self):
        import os
        from tkinter import filedialog
        if not self.group_name:
            messagebox.showinfo('Info', 'Join a group to send a file.')
            return
        file_path = filedialog.askopenfilename(title='Select file to send')
        if not file_path:
            return
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            import base64
            encoded = base64.b64encode(data).decode()
            filename = os.path.basename(file_path)
            msg = {'type': 'GROUP_MEDIA', 'group_name': self.group_name, 'from': self.username, 'filename': filename, 'data': encoded}
            send_json(self.sock, msg)
            self.display_group_message(f'You sent a file to group {self.group_name}: {filename}')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to send file: {e}')
    def send_file(self, to_user):
        import os
        from tkinter import filedialog
        
        # Check if the user is a friend before sending file
        if not self.friend_manager.is_friend(to_user):
            messagebox.showwarning('Not Friends', f'You need to be friends with {to_user} to send files.\nSend a friend request first.')
            return
            
        file_path = filedialog.askopenfilename(title='Select file to send')
        if not file_path:
            return
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            import base64
            encoded = base64.b64encode(data).decode()
            filename = os.path.basename(file_path)
            msg = {'type': 'MEDIA', 'to': to_user, 'from': self.username, 'filename': filename, 'data': encoded}
            send_json(self.sock, msg)
            # Display file in chat for sender
            self.display_file_in_main(self.username, filename, encoded, align='right')
            # Save to chat history
            users = sorted([self.username, to_user])
            history_file = f"chat_{users[0]}_{users[1]}.json"
            arr = [self.username, '', 'right', True, filename, encoded]
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(arr) + '\n')
        except Exception as e:
            messagebox.showerror('Error', f'Failed to send file: {e}')

    def request_user_list(self):
        if self.connected:
            send_json(self.sock, {'type': 'LIST'})
            # Do not call refresh_friendlist here; wait for LIST_RESPONSE from server

    def find_friend(self):
        """Open a window to find and add friends from all registered users"""
        if not self.connected:
            messagebox.showinfo('Info', 'Please connect to the server first.')
            return
        
        # Create find friend window
        find_win = tk.Toplevel(self.master)
        find_win.title('Find Friend')
        find_win.geometry('400x500')
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
        
        # Users listbox with scrollbar
        list_frame = tk.Frame(find_win)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        users_listbox = tk.Listbox(list_frame, height=15)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=users_listbox.yview)
        users_listbox.config(yscrollcommand=scrollbar.set)
        
        users_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Load all users from users.json file
        all_users = []
        users_data = {}
        try:
            with open('data/users.json', 'r') as f:
                users_data = json.load(f)
                all_users = list(users_data.keys())
        except Exception as e:
            messagebox.showerror('Error', f'Could not load users: {e}')
            find_win.destroy()
            return
        
        def filter_users():
            """Filter users based on search query"""
            query = search_var.get().lower().strip()
            users_listbox.delete(0, tk.END)
            
            for user in all_users:
                if user == self.username:  # Don't show current user
                    continue
                if not query or query in user.lower():
                    # Show if already friend
                    user_info = users_data.get(user, {})
                    dept = user_info.get('dept', 'Unknown')
                    session = user_info.get('session', 'Unknown')
                    status = " (Friend)" if self.friend_manager.is_friend(user) else ""
                    display_text = f"{user} - {dept}, {session}{status}"
                    users_listbox.insert(tk.END, display_text)
        
        # Initial population of users
        filter_users()
        
        search_var.trace('w', lambda *args: filter_users())
        
        # Buttons
        btn_frame = tk.Frame(find_win)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def send_friend_request():
            selection = users_listbox.curselection()
            if not selection:
                messagebox.showinfo('Info', 'Please select a user to send friend request.')
                return
            
            selected_text = users_listbox.get(selection[0])
            # Extract username (remove department, session and friend status)
            username = selected_text.split(' - ')[0]
            
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
                with open('data/users.json', 'r') as f:
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
            selection = users_listbox.curselection()
            if not selection:
                messagebox.showinfo('Info', 'Please select a user to simulate a friend request from.')
                return
            
            selected_text = users_listbox.get(selection[0])
            username = selected_text.split(' - ')[0]
            
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
        find_win.users_listbox = users_listbox
        find_win.all_users = all_users
        find_win.filter_users = filter_users
        
        # Store the window reference to update it when we get server response
        self.find_friend_window = find_win

    def create_group(self):
        gname = simpledialog.askstring('Create Group', 'Enter group name:')
        if gname:
            # Send create group request to server, with creator as admin
            send_json(self.sock, {'type': 'CREATE_GROUP', 'group_name': gname, 'creator': self.username})
            messagebox.showinfo('Info', f'Group {gname} created. You are the admin.')
            self.add_joined_group(gname)
            # Prompt to invite friends
            if self.friend_manager:
                friends = self.friend_manager.get_all()
                if friends:
                    import tkinter.simpledialog as sd
                    selected = []
                    invite_win = tk.Toplevel(self.master)
                    invite_win.title(f'Invite Friends to {gname}')
                    tk.Label(invite_win, text=f'Select friends to invite to {gname}:').pack(pady=5)
                    lb = tk.Listbox(invite_win, selectmode=tk.MULTIPLE, width=30)
                    for f in sorted(friends):
                        lb.insert(tk.END, f)
                    lb.pack(padx=10, pady=5)
                    def send_invites():
                        indices = lb.curselection()
                        for idx in indices:
                            friend = lb.get(idx)
                            # Send join request to server for each friend
                            send_json(self.sock, {'type': 'GROUP_INVITE', 'group_name': gname, 'from': self.username, 'to': friend})
                        messagebox.showinfo('Info', f'Invitations sent to selected friends.')
                        invite_win.destroy()
                    tk.Button(invite_win, text='Send Invites', command=send_invites).pack(pady=8)
                    tk.Button(invite_win, text='Cancel', command=invite_win.destroy).pack()

    def join_group(self):
        gname = simpledialog.askstring('Join Group', 'Enter group name:')
        if gname:
            send_json(self.sock, {'type': 'JOIN_GROUP', 'group_name': gname, 'user': self.username})
            messagebox.showinfo('Info', f'Requested to join group {gname}.')
            self.group_name = gname
            self.add_joined_group(gname)

    def send_message(self, event=None):
        msg = self.msg_entry.get().strip()
        if not msg:
            return
        if self.current_chat:
            chat_type, name = self.current_chat
            if chat_type == 'private':
                # Check if the user is a friend before sending message
                if not self.friend_manager.is_friend(name):
                    messagebox.showwarning('Not Friends', f'You need to be friends with {name} to send messages.\nSend a friend request first.')
                    return
                send_json(self.sock, {'type': 'PRIVATE_MESSAGE', 'to': name, 'from': self.username, 'msg': msg})
                self.display_message_in_main(self.username, msg, align='right')
                # Save to chat history
                users = sorted([self.username, name])
                history_file = f"chat_{users[0]}_{users[1]}.json"
                arr = [self.username, msg, 'right', False, None, None]
                with open(history_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(arr) + '\n')
            elif chat_type == 'group':
                send_json(self.sock, {'type': 'GROUP_MESSAGE', 'group_name': name, 'from': self.username, 'msg': msg})
                self.display_message_in_main(f'You (Group {name})', msg, align='right')
        else:
            messagebox.showinfo('Info', 'Select a user or join a group to chat.')
        self.msg_entry.delete(0, tk.END)

    def open_chat_from_friendlist(self, event):
        selection = self.friends_listbox.curselection()
        if not selection:
            return
        friend_display = self.friends_listbox.get(selection[0])
        # Remove dot and space prefix to get username
        if friend_display.startswith('🟢') or friend_display.startswith('🔴'):
            friend = friend_display[2:].strip()
        else:
            friend = friend_display.strip()
        self.open_private_chat(friend)

    # No longer used for private chat, handled in ChatWindow

    def listen_server(self):
        try:
            while self.connected:
                try:
                    message = recv_json(self.sock)
                    mtype = message.get('type')
                    if mtype == 'LIST_RESPONSE':
                        self.active_users = message['users']
                        self.refresh_friendlist(self.active_users)
                    elif mtype == 'FRIEND_REQUEST':
                        from_user = message.get('from')
                        sender_info = message.get('sender_info', {})
                        if from_user:
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
                        if from_user:
                            # Add to friend list
                            self.friend_manager.add(from_user)
                            self.refresh_friendlist()
                            messagebox.showinfo('Friend Request Accepted', f'{from_user} accepted your friend request!')
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
                        if self.current_chat and self.current_chat[0] == 'private' and self.current_chat[1] == sender:
                            self.display_message_in_main(sender, msg, align='left')
                            users = sorted([self.username, sender])
                            history_file = f"chat_{users[0]}_{users[1]}.json"
                            arr = [sender, msg, 'left', False, None, None]
                            with open(history_file, 'a', encoding='utf-8') as f:
                                f.write(json.dumps(arr) + '\n')
                        else:
                            self.add_home_notification(sender, msg)
                    elif mtype == 'MEDIA':
                        sender = message['from']
                        filename = message['filename']
                        filedata = message['data']
                        if self.current_chat and self.current_chat[0] == 'private' and self.current_chat[1] == sender:
                            self.display_file_in_main(sender, filename, filedata, align='left')
                            users = sorted([self.username, sender])
                            history_file = f"chat_{users[0]}_{users[1]}.json"
                            arr = [sender, '', 'left', True, filename, filedata]
                            with open(history_file, 'a', encoding='utf-8') as f:
                                f.write(json.dumps(arr) + '\n')
                        else:
                            self.add_home_notification(sender, f'Sent a file: {filename}', is_file=True, filedata=filedata, filename=filename)
                    elif mtype == 'GROUP_MESSAGE':
                        sender = message['from']
                        msg = message['msg']
                        gname = message['group_name']
                        self.group_name = gname
                        self.display_group_message(f'{sender} (Group {gname}): {msg}')
                        self.add_joined_group(gname)
                    elif mtype == 'GROUP_INVITE':
                        group_name = message.get('group_name')
                        from_user = message.get('from')
                        if group_name and from_user:
                            if messagebox.askyesno('Group Invitation', f"{from_user} invited you to join group '{group_name}'.\nDo you want to join?"):
                                send_json(self.sock, {'type': 'JOIN_GROUP', 'group_name': group_name, 'user': self.username})
                                self.add_joined_group(group_name)
                                messagebox.showinfo('Joined Group', f"You have joined group '{group_name}'.")
                            else:
                                messagebox.showinfo('Group Invitation', f"You declined the invitation to join '{group_name}'.")
                    elif mtype == 'GROUP_MEDIA':
                        sender = message['from']
                        filename = message['filename']
                        filedata = message['data']
                        gname = message['group_name']
                        import base64
                        import os
                        save_path = os.path.join(os.getcwd(), f'received_{gname}_{filename}')
                        with open(save_path, 'wb') as f:
                            f.write(base64.b64decode(filedata))
                        self.display_group_message(f'{sender} sent a file to group {gname}: {filename} (saved as {save_path})')
                        self.add_joined_group(gname)
                    elif mtype == 'OFFLINE_MESSAGES':
                        for msg in message.get('messages', []):
                            sender = msg.get('from')
                            sender_info = msg.get('sender_info')
                            if msg.get('is_friend_request'):
                                self.add_home_notification(sender, msg.get('msg', 'sent you a friend request'), 
                                                         is_friend_request=True, sender_info=sender_info)
                            elif msg.get('is_file'):
                                self.add_home_notification(sender, f"Sent a file: {msg.get('filename')}", is_file=True, filedata=msg.get('data'), filename=msg.get('filename'))
                            else:
                                self.add_home_notification(sender, msg.get('msg', ''))
                    elif mtype == 'MESSAGE_ERROR':
                        reason = message.get('reason', 'Message sending failed')
                        messagebox.showerror('Message Error', reason)
                except Exception as e:
                    # Only show error if still connected (not after logout)
                    if self.connected:
                        messagebox.showerror('Error', f'[ERROR] {e}')
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

    def add_home_notification(self, sender, msg, is_file=False, filedata=None, filename=None, is_friend_request=False, sender_info=None):
        # Only one notification per sender (but allow friend requests to override regular messages)
        if not hasattr(self, 'notification_listbox'):
            return
        if sender in self.notifications_home and not is_friend_request:
            return
        
        # Remove existing notification from same sender if this is a friend request
        if is_friend_request and sender in self.notifications_home:
            # Find and remove existing notification
            for i in range(self.notification_listbox.size()):
                if self.notification_listbox.get(i).startswith(f'{sender}:'):
                    self.notification_listbox.delete(i)
                    break
        
        # Format display text differently for friend requests
        if is_friend_request:
            display = f'[FRIEND REQUEST] {sender}: {msg}'
        else:
            display = f'{sender}: {msg}'
            
        self.notification_listbox.insert(tk.END, display)
        self.notifications_home[sender] = {
            'msg': msg, 
            'is_file': is_file, 
            'filedata': filedata, 
            'filename': filename,
            'is_friend_request': is_friend_request,
            'sender_info': sender_info
        }

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
        else:
            # Format: "sender: message"
            sender = display.split(':', 1)[0]
        info = self.notifications_home.get(sender)
        
        # Handle friend request notification
        if info and info.get('is_friend_request'):
            print(f"DEBUG: Friend request notification clicked for {sender}")
            sender_info = info.get('sender_info', {})
            print(f"DEBUG: Sender info: {sender_info}")
            # Show detailed friend request dialog
            self.show_friend_request_dialog(sender, sender_info)
            return
        
        # Open chat in main area for regular messages
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
                    self.display_file_in_main(sender, info['filename'], info['filedata'], align='left')
                # Save to chat history
                arr = [sender, '', 'left', True, info['filename'], info['filedata']]
                with open(history_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(arr) + '\n')
            else:
                if sender != self.username:
                    self.display_message_in_main(sender, info["msg"], align='left')
                arr = [sender, info["msg"], 'left', False, None, None]
                with open(history_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(arr) + '\n')
        # Remove notification from listbox and dict
        self.notification_listbox.delete(idx)
        if sender in self.notifications_home:
            del self.notifications_home[sender]

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
        self.chat_area.config(state='normal')
        self.chat_area.delete(1.0, tk.END)
        # Add header with friend's profile picture and name
        header_frame = tk.Frame(self.chat_area)
        # Always use default_dp.png as fallback profile image
        profile_img = None
        from PIL import Image, ImageTk
        img_path = f'profile_{friend}.png'
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
        # Always show an image: profile_{friend}.png if exists, else default_dp.png
        if profile_img is None:
            try:
                pil_img = Image.open('default_dp.png')
                pil_img.thumbnail((40, 40))
                profile_img = ImageTk.PhotoImage(pil_img)
            except Exception:
                profile_img = None
        if profile_img is not None:
            img_label = tk.Label(header_frame, image=profile_img)
            img_label.image = profile_img
            img_label.pack(side=tk.LEFT, padx=(0,8))
        name_label = tk.Label(header_frame, text=friend, font=('Arial', 14, 'bold'))
        name_label.pack(side=tk.LEFT)
        self.chat_area.window_create(tk.END, window=header_frame)
        self.chat_area.insert(tk.END, '\n')
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
                        if is_file and filename and filedata:
                            self.display_file_in_main(sender, filename, filedata, align=align)
                        else:
                            self.display_message_in_main(sender, msg, align=align)
                    except Exception:
                        continue
        self.chat_area.config(state='disabled')

    def display_message_in_main(self, sender, msg, align=None):
        from PIL import Image, ImageTk
        import os
        self.chat_area.config(state='normal')
        # Determine profile image path
        if sender == self.username:
            img_path = f'profile_{self.username}.png'
            align = 'right'
        else:
            img_path = f'profile_{sender}.png'
            align = 'left'
        try:
            if os.path.exists(img_path):
                pil_img = Image.open(img_path)
            else:
                pil_img = Image.open('default_dp.png')
            pil_img.thumbnail((32, 32))
            profile_img = ImageTk.PhotoImage(pil_img)
        except Exception:
            try:
                pil_img = Image.open('default_dp.png')
                pil_img.thumbnail((32, 32))
                profile_img = ImageTk.PhotoImage(pil_img)
            except Exception:
                profile_img = None
        # Create a frame for the message row
        msg_row = tk.Frame(self.chat_area)
        # Profile image label
        if profile_img is not None:
            img_label = tk.Label(msg_row, image=profile_img)
            img_label.image = profile_img
        else:
            img_label = tk.Label(msg_row, text='[No Image]')
        # Message bubble
        bubble = tk.Label(msg_row, text=msg, bg='#e1ffc7' if align == 'right' else '#ffffff',
                          font=('Arial', 11), wraplength=350, justify='left', bd=1, relief='solid', padx=8, pady=4)
        # Pack widgets according to alignment
        if align == 'right':
            bubble.pack(side=tk.RIGHT, padx=(8,0))
            img_label.pack(side=tk.RIGHT)
        else:
            img_label.pack(side=tk.LEFT)
            bubble.pack(side=tk.LEFT, padx=(0,8))
        self.chat_area.window_create(tk.END, window=msg_row)
        self.chat_area.insert(tk.END, '\n')
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)

    def display_file_in_main(self, sender, filename, filedata, align='left'):
        import base64
        import tempfile
        from tkinter import Button, filedialog
        from PIL import Image, ImageTk
        ext = os.path.splitext(filename)[1].lower()
        is_image = ext in ['.png', '.jpg', '.jpeg', '.gif']
        temp_path = os.path.join(tempfile.gettempdir(), f'{sender}_{filename}')
        with open(temp_path, 'wb') as f:
            f.write(base64.b64decode(filedata))
        self.chat_area.config(state='normal')
        if is_image:
            try:
                pil_img = Image.open(temp_path)
                pil_img.thumbnail((200, 200))
                img = ImageTk.PhotoImage(pil_img)
                if not hasattr(self, '_img_refs_main'):
                    self._img_refs_main = []
                self._img_refs_main.append(img)
                self.chat_area.image_create(tk.END, image=img)
                self.chat_area.insert(tk.END, f'\n{sender} sent an image: {filename}\n')
                if sender != self.username:
                    def download():
                        save_path = filedialog.asksaveasfilename(initialfile=filename)
                        if save_path:
                            with open(temp_path, 'rb') as src, open(save_path, 'wb') as dst:
                                dst.write(src.read())
                    btn = Button(self.chat_area, text='Download', command=download)
                    self.chat_area.window_create(tk.END, window=btn)
                    self.chat_area.insert(tk.END, '\n')
            except Exception:
                self.chat_area.insert(tk.END, f'{sender} sent a file: {filename}\n')
        else:
            self.chat_area.insert(tk.END, f'{sender} sent a file: {filename}\n')
            if sender != self.username:
                def download():
                    save_path = filedialog.asksaveasfilename(initialfile=filename)
                    if save_path:
                        with open(temp_path, 'rb') as src, open(save_path, 'wb') as dst:
                            dst.write(src.read())
                btn = Button(self.chat_area, text='Download', command=download)
                self.chat_area.window_create(tk.END, window=btn)
                self.chat_area.insert(tk.END, '\n')
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)

    def logout(self):
        # Mark as disconnected and reset UI, but do NOT close the socket
        self.connected = False
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
        print(f"DEBUG: Opening friend request dialog for {sender}")
        
        # Validate inputs
        if not sender:
            messagebox.showerror('Error', 'Invalid friend request data.')
            return
            
        if not sender_info:
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
            print(f"DEBUG: Accept button clicked for {sender}")
            try:
                # Send acceptance to server
                send_json(self.sock, {
                    'type': 'FRIEND_REQUEST_RESPONSE',
                    'from': self.username,
                    'to': sender,
                    'accepted': True
                })
                print(f"DEBUG: Sent acceptance to server")
                
                # Add to friend list locally
                self.friend_manager.add(sender)
                self.refresh_friendlist()
                print(f"DEBUG: Added {sender} to friend list")
                
                # Close dialog
                dialog.destroy()
                
                # Show success message
                messagebox.showinfo('Friend Added', 
                                  f'{sender} has been added to your friends!')
                
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

    def remove_notification(self, sender):
        """Remove notification from the notification list"""
        if not hasattr(self, 'notification_listbox'):
            return
            
        # Find and remove the notification
        for i in range(self.notification_listbox.size()):
            display = self.notification_listbox.get(i)
            if display.startswith(f'[FRIEND REQUEST] {sender}:') or display.startswith(f'{sender}:'):
                self.notification_listbox.delete(i)
                break
        
        # Remove from notifications dict
        if sender in self.notifications_home:
            del self.notifications_home[sender]

    # ...existing code...

if __name__ == '__main__':
    root = tk.Tk()
    app = ChatClient(root)
    root.mainloop()
