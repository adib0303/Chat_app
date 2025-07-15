#!/usr/bin/env python3
"""
Quick test to verify friend request dialog functionality in client_gui.py
"""
import sys
import os

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_dialog_in_client():
    """Test that the friend request dialog can be created from client_gui.py"""
    try:
        # Import the ChatClient class
        from client_gui import ChatClient
        import tkinter as tk
        
        print("✓ Successfully imported ChatClient")
        
        # Create a test root window
        root = tk.Tk()
        root.withdraw()  # Hide main window
        
        # Create a ChatClient instance
        client = ChatClient(root)
        client.username = "test_user"  # Set a test username
        
        print("✓ ChatClient instance created")
        
        # Test data
        sender = "test_sender"
        sender_info = {
            'name': 'test_sender',
            'dept': 'Computer Science',
            'session': '2021-22'
        }
        
        print("✓ Test data prepared")
        print(f"  Sender: {sender}")
        print(f"  Sender info: {sender_info}")
        
        # Try to call the method
        print("\n🔧 Attempting to show friend request dialog...")
        client.show_friend_request_dialog(sender, sender_info)
        
        print("✓ Dialog method called successfully!")
        print("\nIf you see a dialog window, the implementation is working.")
        print("If no dialog appears, there may be an issue with the method.")
        
        # Keep the window open for testing
        root.mainloop()
        
    except Exception as e:
        print(f"✗ Error testing dialog: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Testing Friend Request Dialog in client_gui.py")
    print("=" * 50)
    test_dialog_in_client()
