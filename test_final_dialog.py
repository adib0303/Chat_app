#!/usr/bin/env python3
"""
Test the final friend request dialog with Accept/Ignore buttons
"""
import tkinter as tk
from tkinter import messagebox

def test_final_dialog():
    """Test the friend request dialog with proper Accept/Ignore buttons"""
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    # Create test dialog similar to the real implementation
    dialog = tk.Toplevel(root)
    dialog.title('Friend Request - Test')
    dialog.geometry('450x400')
    dialog.grab_set()
    
    # Main frame
    main_frame = tk.Frame(dialog)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Title
    tk.Label(main_frame, text='Friend Request', 
             font=('Arial', 16, 'bold'), fg='blue').pack(pady=(0, 15))
    
    # Request message
    tk.Label(main_frame, text='testuser wants to add you as a friend',
             font=('Arial', 12, 'bold')).pack(pady=(0, 10))
    
    # User details
    info_box = tk.Frame(main_frame, bg='lightgray', relief='solid', bd=2)
    info_box.pack(fill=tk.X, pady=10)
    
    tk.Label(info_box, text='User Information:', 
            font=('Arial', 11, 'bold'), bg='lightgray').pack(pady=5)
    tk.Label(info_box, text="Username: testuser", 
            bg='lightgray', font=('Arial', 10)).pack(pady=2)
    tk.Label(info_box, text="Department: Computer Science", 
            bg='lightgray', font=('Arial', 10)).pack(pady=2)
    tk.Label(info_box, text="Session: 2021-22", 
            bg='lightgray', font=('Arial', 10)).pack(pady=2)
    tk.Label(info_box, text='', bg='lightgray').pack(pady=3)
    
    # Button functions
    def accept_request():
        print("✓ Accept button clicked!")
        messagebox.showinfo('Accept', 'Friend request accepted!\nUser added to friends.')
        dialog.destroy()
    
    def ignore_request():
        print("✗ Ignore button clicked!")
        messagebox.showinfo('Ignore', 'Friend request ignored.')
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
    
    # Add hover effects
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
    
    # Status
    tk.Label(main_frame, text='Test the Accept and Ignore buttons above',
             font=('Arial', 10), fg='gray').pack(pady=10)
    
    print("🔧 Friend Request Dialog Test")
    print("✓ Dialog created with Accept and Ignore buttons")
    print("✓ Hover effects enabled")
    print("✓ Click either button to test functionality")
    
    dialog.focus_set()
    root.mainloop()

if __name__ == "__main__":
    test_final_dialog()
