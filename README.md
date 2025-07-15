# Chat Application

A comprehensive real-time chat application built with Python, featuring private messaging, group chats, file sharing, and friend management system.

## Features

### � Core Features
- **Real-time Messaging**: Instant private and group messaging
- **Friend System**: Add/remove friends with request system
- **Group Chat**: Create and manage group conversations
- **File Sharing**: Share images and files with preview support
- **Profile Pictures**: Customize user profiles with images
- **Online Status**: Real-time online/offline status indicators
- **Message History**: Persistent chat history storage
- **Offline Messages**: Receive messages even when offline
- **Notifications**: Desktop notifications for new messages

### 💬 Chat Features
- Private one-on-one conversations
- Group chat with multiple members
- File sharing with image previews
- Timestamp support for all messages
- Message history persistence
- Enhanced UI with profile pictures

### � Social Features
- Friend request system
- Bidirectional friend management
- Group creation and management
- Member invitation system
- User discovery and search

### 🔧 Technical Features
- JSON-based protocol communication
- Robust error handling and recovery
- Connection health monitoring
- Automatic reconnection attempts
- Comprehensive logging system

## Installation

### Prerequisites
- Python 3.7 or higher
- Required Python packages (install via pip):

```bash
pip install pillow tkinter socket json datetime threading
```

### Setup
1. Clone the repository:
```bash
git clone https://github.com/adib0303/Chat_app.git
cd Chat_app
```

2. Ensure you have the required image files:
   - `default_dp.png` - Default profile picture
   - `green_dot.png` - Online status indicator
   - `red_dot.png` - Offline status indicator

## Usage

### Starting the Server
1. Run the server script:
```bash
python server.py
```
The server will start on `localhost:12345` by default.

### Starting the Client
1. Run the client application:
```bash
python client_gui.py
```

2. **Login/Register**: Enter your credentials to log in or create a new account

3. **Add Friends**: Use the "Find Friend" feature to search and add friends

4. **Start Chatting**: Double-click on a friend to start a private conversation

5. **Create Groups**: Use the "Create Group" button to start group conversations

6. **Share Files**: Use the file sharing button to send images and documents

## File Structure

```
Chat_app/
├── server.py              # Main server application
├── client_gui.py          # GUI client application
├── default_dp.png         # Default profile picture
├── green_dot.png          # Online status indicator
├── red_dot.png            # Offline status indicator
├── data/                  # Server data directory
│   ├── users.json         # User account information
│   ├── groups.json        # Group information
│   ├── offline_messages.json # Stored offline messages
│   └── chat_logs/         # Chat history logs
├── profile_*.png          # User profile pictures
├── friends_*.json         # User friend lists
├── chat_*.json            # Private chat histories
├── joined_groups_*.json   # User group memberships
└── group_chat_*.json      # Group chat histories
```

## Configuration

### Server Configuration
Edit the following constants in `server.py`:
- `HOST`: Server host address (default: 'localhost')
- `PORT`: Server port (default: 12345)

### Client Configuration
Edit the following constants in `client_gui.py`:
- `SERVER_HOST`: Server address to connect to (default: 'localhost')
- `SERVER_PORT`: Server port (default: 12345)

## Protocol

The application uses a JSON-based protocol for client-server communication. Key message types include:

- `LOGIN`/`REGISTER`: User authentication
- `SEND_MESSAGE`: Private messaging
- `FRIEND_REQUEST`/`FRIEND_RESPONSE`: Friend management
- `CREATE_GROUP`/`JOIN_GROUP`: Group management
- `GROUP_MESSAGE`: Group messaging
- `SEND_FILE`: File sharing
- `GET_ONLINE_USERS`: Status updates

## Features in Detail

### Friend Management
- Send friend requests to other users
- Accept or decline incoming requests
- Unfriend users with confirmation
- Real-time friend status updates

### Group Chat
- Create groups with custom names and descriptions
- Invite friends to groups
- Add members to existing groups
- Leave groups with confirmation
- Group-specific message history

### File Sharing
- Share images with thumbnail previews
- Support for various file types
- Automatic file storage and retrieval
- File download functionality

### User Interface
- Modern, intuitive GUI design
- Profile picture integration
- Status indicators for all contacts
- Organized notification system
- Responsive layout design

## Troubleshooting

### Common Issues

1. **Connection Failed**: Ensure the server is running and accessible
2. **Files Not Loading**: Check file paths and permissions
3. **Profile Pictures Not Showing**: Ensure image files are in the correct directory
4. **Messages Not Sending**: Verify network connection and server status

### Debug Mode
Enable debug mode by setting debug flags in the code for detailed logging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions, please create an issue on the GitHub repository.

---

**Developed by**: Adib
**Repository**: https://github.com/adib0303/Chat_app

For issues or questions:
1. Check the troubleshooting section in `FRIEND_REQUEST_DOCS.md`
2. Run test scripts to validate functionality
3. Check console output for debug information
4. Create an issue in the GitHub repository

---

**Note**: This application is designed for educational purposes and local network use. For production deployment, additional security measures should be implemented.
