import tkinter as tk
from tkinter import messagebox

def test_friend_dialog():
    """Test the friend request dialog functionality"""
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    # Create test dialog
    dialog = tk.Toplevel(root)
    dialog.title('Test Friend Request Dialog')
    dialog.geometry('400x300')
    dialog.grab_set()
    
    # Main frame
    main_frame = tk.Frame(dialog)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # Title
    tk.Label(main_frame, text='Friend Request Test', 
             font=('Arial', 16, 'bold')).pack(pady=10)
    
    # Info
    tk.Label(main_frame, text='Test User wants to add you as a friend', 
             font=('Arial', 12)).pack(pady=10)
    
    # User details
    info_frame = tk.Frame(main_frame, bg='lightgray', relief='solid', bd=1)
    info_frame.pack(fill=tk.X, pady=10)
    
    tk.Label(info_frame, text='Username: testuser', bg='lightgray').pack(pady=2)
    tk.Label(info_frame, text='Department: Computer Science', bg='lightgray').pack(pady=2)
    tk.Label(info_frame, text='Session: 2021-22', bg='lightgray').pack(pady=2)
    
    # Button frame
    btn_frame = tk.Frame(main_frame)
    btn_frame.pack(pady=20)
    
    def accept_clicked():
        messagebox.showinfo('Test', 'Accept button works!')
        dialog.destroy()
        
    def ignore_clicked():
        messagebox.showinfo('Test', 'Ignore button works!')
        dialog.destroy()
    
    # Simple buttons
    accept_btn = tk.Button(btn_frame, text='Accept', 
                          command=accept_clicked,
                          bg='green', fg='white',
                          font=('Arial', 12, 'bold'),
                          width=10, height=2)
    accept_btn.pack(side=tk.LEFT, padx=10)
    
    ignore_btn = tk.Button(btn_frame, text='Ignore', 
                          command=ignore_clicked,
                          bg='red', fg='white',
                          font=('Arial', 12, 'bold'),
                          width=10, height=2)
    ignore_btn.pack(side=tk.RIGHT, padx=10)
    
    # Test button functionality
    test_frame = tk.Frame(main_frame)
    test_frame.pack(pady=10)
    
    def test_click():
        print("Test button clicked!")
        messagebox.showinfo('Test', 'Test button works!')
    
    tk.Button(test_frame, text='Test Click', command=test_click).pack()
    
    root.mainloop()

if __name__ == "__main__":
    test_friend_dialog()
