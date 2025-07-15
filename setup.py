#!/usr/bin/env python3
"""
Setup script for Chat Application
Checks dependencies and initializes required files
"""
import os
import json
import sys

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import tkinter
        print("✅ Tkinter available")
    except ImportError:
        print("❌ Tkinter not available")
        return False
    
    try:
        from PIL import Image, ImageTk
        print("✅ Pillow (PIL) available")
    except ImportError:
        print("❌ Pillow not installed. Run: pip install Pillow")
        return False
    
    return True

def create_data_structure():
    """Create required data directories and files"""
    # Create data directory
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/chat_logs", exist_ok=True)
    os.makedirs("data/media", exist_ok=True)
    print("✅ Data directories created")
    
    # Create users.json if it doesn't exist
    users_file = "data/users.json"
    if not os.path.exists(users_file):
        default_users = {
            "adib": {
                "name": "adib",
                "dept": "cse", 
                "session": "2021-22",
                "password": "123456789"
            },
            "omar": {
                "name": "omar",
                "dept": "nu",
                "session": "2020-21", 
                "password": "123456789"
            },
            "sakib": {
                "name": "sakib",
                "dept": "stat",
                "session": "2021-22",
                "password": "123456789"
            }
        }
        with open(users_file, 'w') as f:
            json.dump(default_users, f, indent=2)
        print("✅ Default users.json created")
    else:
        print("✅ users.json already exists")
    
    # Create groups.json if it doesn't exist
    groups_file = "data/groups.json"
    if not os.path.exists(groups_file):
        with open(groups_file, 'w') as f:
            json.dump({}, f)
        print("✅ groups.json created")
    
    # Create offline_messages.json if it doesn't exist
    offline_file = "data/offline_messages.json"
    if not os.path.exists(offline_file):
        with open(offline_file, 'w') as f:
            json.dump({}, f)
        print("✅ offline_messages.json created")

def check_image_files():
    """Check if required image files exist"""
    required_images = [
        "default_dp.png",
        "green_dot.png", 
        "red_dot.png"
    ]
    
    missing_images = []
    for img in required_images:
        if os.path.exists(img):
            print(f"✅ {img} found")
        else:
            missing_images.append(img)
            print(f"⚠️  {img} missing")
    
    if missing_images:
        print("\n📝 Note: Missing image files will be handled gracefully by the application")
        print("   You can add these files later for better visual experience")
    
    return len(missing_images) == 0

def run_setup():
    """Run complete setup process"""
    print("🚀 Chat Application Setup")
    print("=" * 40)
    
    success = True
    
    # Check Python version
    if not check_python_version():
        success = False
    
    # Check dependencies
    if not check_dependencies():
        success = False
    
    # Create data structure
    create_data_structure()
    
    # Check image files
    check_image_files()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ Setup completed successfully!")
        print("\n🎯 Next steps:")
        print("1. Run: python server.py")
        print("2. Run: python client_gui.py (for each user)")
        print("3. Or use: start_chat_test.bat (Windows)")
        print("\n📚 See README.md for detailed instructions")
    else:
        print("❌ Setup incomplete. Please fix the issues above.")
    
    return success

if __name__ == "__main__":
    run_setup()
