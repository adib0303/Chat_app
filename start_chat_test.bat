@echo off
echo Starting Chat Application...
echo.

echo Starting Server...
start "Chat Server" python server.py
timeout /t 2 >nul

echo Starting Client 1...
start "Chat Client 1" python client_gui.py
timeout /t 1 >nul

echo Starting Client 2...
start "Chat Client 2" python client_gui.py

echo.
echo Both server and clients are starting...
echo Login with different users to test friend requests.
echo.
echo To test friend requests:
echo 1. Login with User A (e.g., 'adib')
echo 2. Login with User B (e.g., 'omar')  
echo 3. User A: Click "Find Friend" -> Select User B -> "Send Friend Request"
echo 4. User B: Check notifications panel -> Click on [FRIEND REQUEST] notification
echo 5. User B: See detailed dialog with User A's info
echo 6. User B: Click "Test Click" to verify dialog works
echo 7. User B: Click "Accept" (green) or "Ignore" (red) button
echo 8. After accepting, both users should be friends and can chat
echo.
echo If buttons are not clickable, run: python test_dialog.py
echo to test basic dialog functionality.
echo.
pause
