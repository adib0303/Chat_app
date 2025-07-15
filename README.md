# Chat Application with Friend Request System

A comprehensive Python chat application built with Tkinter GUI and socket programming, featuring a robust friend request system with detailed user information display.

## Features

### 🔐 User Authentication
- User registration and login system
- Secure password-based authentication
- User profile management with profile pictures

### 👥 Friend Management
- **Enhanced Friend Request System** with detailed user information
- Find and discover registered users
- Send/receive friend requests with user details (name, department, session)
- Accept/Ignore friend requests through professional dialog
- Friendship verification before allowing communication

### 💬 Real-time Chat
- Private messaging between friends
- Group chat functionality
- File sharing (images, documents)
- Message history persistence
- Online/offline status indicators

### 🔔 Notification System
- Friend request notifications with `[FRIEND REQUEST]` prefix
- Message notifications for offline users
- File sharing notifications

## System Requirements

- Python 3.7+
- Tkinter (usually included with Python)
- Pillow (PIL) for image handling
- Socket programming support

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/Chat_app.git
   cd Chat_app
   ```

2. **Install dependencies**:
   ```bash
   pip install Pillow
   ```

3. **Ensure required files exist**:
   - `default_dp.png` - Default profile picture
   - `green_dot.png` - Online status indicator
   - `red_dot.png` - Offline status indicator
   - `data/users.json` - User database

## Quick Start

### Using the Batch Script (Windows)
```bash
start_chat_test.bat
```

### Manual Setup
1. **Start the server**:
   ```bash
   python server.py
   ```

2. **Start client instances**:
   ```bash
   python client_gui.py  # User A
   python client_gui.py  # User B (in another terminal)
   ```

3. **Test the friend request system**:
   - Login with different users (e.g., 'adib', 'omar')
   - User A: Click "Find Friend" → Select User B → "Send Friend Request"
   - User B: Check notifications → Click on `[FRIEND REQUEST]` notification
   - User B: View detailed dialog → Click "✓ Accept" or "✗ Ignore"
   - Verify both users can now chat

## Friend Request System

### Sending Friend Requests
1. Click "Find Friend" button
2. Browse all registered users with their details
3. Select a user and click "Send Friend Request"
4. Request is sent with complete sender information

### Receiving Friend Requests
1. Friend requests appear in notifications panel with `[FRIEND REQUEST]` prefix
2. Click on notification to open detailed dialog showing:
   - Sender's profile picture
   - Complete user information (username, department, session)
   - Professional Accept/Ignore buttons with hover effects
3. Choose to accept or ignore the request
4. Friendship status updates automatically

## File Structure

```
Chat_app/
├── client_gui.py              # Main chat client application
├── server.py                  # Central chat server
├── data/
│   ├── users.json            # User database
│   ├── groups.json           # Group information
│   ├── offline_messages.json # Stored offline messages
│   └── chat_logs/           # Chat history storage
├── friends_*.json            # Individual user friend lists
├── profile_*.png            # User profile pictures
├── *.png                    # UI icons and default images
├── start_chat_test.bat      # Windows batch script for easy testing
├── test_*.py               # Test scripts for validation
└── FRIEND_REQUEST_DOCS.md  # Detailed documentation

```

## Testing

### Automated Tests
```bash
python test_friend_request.py    # Test friend request data structure
python test_dialog.py           # Test basic dialog functionality  
python test_final_dialog.py     # Test complete friend request dialog
python test_client_dialog.py    # Test dialog integration
```

### Manual Testing
1. Run `start_chat_test.bat` for automated setup
2. Follow the on-screen instructions
3. Test friend requests between different users
4. Verify chat functionality after accepting friend requests

## Technical Architecture

### Client-Server Model
- **Server** (`server.py`): Handles user connections, message relay, friend request processing
- **Client** (`client_gui.py`): Tkinter GUI application with chat interface

### Key Components
- **FriendManager**: Handles local friend list management
- **ChatClient**: Main application class with GUI and networking
- **Friend Request Dialog**: Professional UI for processing friend requests
- **Notification System**: Real-time notification display

### Data Storage
- **JSON-based**: User data, friend lists, groups, offline messages
- **File-based**: Chat logs, media files, profile pictures
- **Real-time**: Socket communication for live messaging

## Security Features

- Friendship verification before allowing communication
- Server-side message blocking for non-friends
- Client-side UI restrictions for non-friends
- Secure user authentication system

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Authors

- **Primary Developer**: Chat Application Team
- **Friend Request System**: Enhanced by AI Assistant

## Support

For issues or questions:
1. Check the troubleshooting section in `FRIEND_REQUEST_DOCS.md`
2. Run test scripts to validate functionality
3. Check console output for debug information
4. Create an issue in the GitHub repository

---

**Note**: This application is designed for educational purposes and local network use. For production deployment, additional security measures should be implemented.
