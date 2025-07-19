#!/usr/bin/env python3
"""
TCP Reno CWND Graphing Module
Automated real-time graphing of TCP Reno congestion window behavior
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import threading
import time
import json
import os
from datetime import datetime
import tkinter as tk
from tkinter import ttk

class TCPRenoGrapher:
    def __init__(self, username="User"):
        self.username = username
        self.data_file = f"reno_graph_data_{username}.json"
        
        # Graph data storage
        self.timestamps = []
        self.cwnd_values = []
        self.ssthresh_values = []
        self.states = []
        self.events = []  # Special events (Fast Retransmit, Timeout, etc.)
        
        # Graph window reference
        self.graph_window = None
        self.figure = None
        self.canvas = None
        self.animation = None
        self.is_recording = False
        
        # Load existing data if available
        self.load_data()
        
    def record_data_point(self, cwnd, ssthresh, state, event_type=None):
        """Record a data point for graphing"""
        if not self.is_recording:
            return
            
        current_time = time.time()
        
        # Store data point
        self.timestamps.append(current_time)
        self.cwnd_values.append(cwnd)
        self.ssthresh_values.append(ssthresh)
        self.states.append(state)
        
        # Record special events
        if event_type:
            self.events.append({
                'time': current_time,
                'cwnd': cwnd,
                'event': event_type
            })
        
        # Save data to file for persistence
        self.save_data()
        
        # Limit data points to prevent memory issues (keep last 1000 points)
        if len(self.timestamps) > 1000:
            self.timestamps = self.timestamps[-1000:]
            self.cwnd_values = self.cwnd_values[-1000:]
            self.ssthresh_values = self.ssthresh_values[-1000:]
            self.states = self.states[-1000:]
    
    def save_data(self):
        """Save graph data to file"""
        try:
            data = {
                'timestamps': self.timestamps,
                'cwnd_values': self.cwnd_values,
                'ssthresh_values': self.ssthresh_values,
                'states': self.states,
                'events': self.events,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass  # Fail silently
    
    def load_data(self):
        """Load existing graph data"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.timestamps = data.get('timestamps', [])
                    self.cwnd_values = data.get('cwnd_values', [])
                    self.ssthresh_values = data.get('ssthresh_values', [])
                    self.states = data.get('states', [])
                    self.events = data.get('events', [])
        except Exception:
            # If loading fails, start fresh
            self.clear_data()
    
    def clear_data(self):
        """Clear all graph data"""
        self.timestamps = []
        self.cwnd_values = []
        self.ssthresh_values = []
        self.states = []
        self.events = []
        try:
            if os.path.exists(self.data_file):
                os.remove(self.data_file)
        except Exception:
            pass
    
    def start_recording(self):
        """Start recording data points"""
        self.is_recording = True
        print(f"[GRAPH-{self.username}] 📊 Started recording CWND data")
    
    def stop_recording(self):
        """Stop recording data points"""
        self.is_recording = False
        print(f"[GRAPH-{self.username}] 📊 Stopped recording CWND data")
    
    def show_realtime_graph(self, master_window=None):
        """Show real-time graph window"""
        if self.graph_window and self.graph_window.winfo_exists():
            self.graph_window.lift()
            return
        
        # Create graph window
        self.graph_window = tk.Toplevel(master_window) if master_window else tk.Tk()
        self.graph_window.title(f'TCP Reno CWND Graph - {self.username}')
        self.graph_window.geometry('1000x700')
        self.graph_window.configure(bg='white')
        
        # Create main frame
        main_frame = tk.Frame(self.graph_window, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_label = tk.Label(main_frame, text=f'🚀 TCP Reno Congestion Window Graph - {self.username}',
                              font=('Arial', 14, 'bold'), bg='white', fg='navy')
        title_label.pack(pady=(0, 10))
        
        # Control frame
        control_frame = tk.Frame(main_frame, bg='white')
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Recording controls
        record_frame = tk.Frame(control_frame, bg='white')
        record_frame.pack(side=tk.LEFT)
        
        def toggle_recording():
            if self.is_recording:
                self.stop_recording()
                record_btn.config(text='▶️ Start Recording', bg='lightgreen')
                status_label.config(text='Status: Stopped', fg='red')
            else:
                self.start_recording()
                record_btn.config(text='⏸️ Stop Recording', bg='lightcoral')
                status_label.config(text='Status: Recording', fg='green')
        
        record_btn = tk.Button(record_frame, text='▶️ Start Recording' if not self.is_recording else '⏸️ Stop Recording',
                              command=toggle_recording, font=('Arial', 10, 'bold'),
                              bg='lightgreen' if not self.is_recording else 'lightcoral')
        record_btn.pack(side=tk.LEFT, padx=2)
        
        def clear_graph():
            self.clear_data()
            status_label.config(text='Status: Data Cleared', fg='orange')
            
        clear_btn = tk.Button(record_frame, text='🗑️ Clear Data', command=clear_graph,
                             font=('Arial', 10, 'bold'), bg='orange')
        clear_btn.pack(side=tk.LEFT, padx=2)
        
        # Status frame
        status_frame = tk.Frame(control_frame, bg='white')
        status_frame.pack(side=tk.RIGHT)
        
        status_label = tk.Label(status_frame, text='Status: Recording' if self.is_recording else 'Status: Stopped',
                               font=('Arial', 10, 'bold'), bg='white',
                               fg='green' if self.is_recording else 'red')
        status_label.pack()
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(12, 8), dpi=80, facecolor='white')
        self.figure.suptitle('TCP Reno Algorithm - Congestion Window Evolution', 
                            fontsize=16, fontweight='bold')
        
        # Create subplot
        self.ax = self.figure.add_subplot(111)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.figure, main_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Start animation
        self.animation = animation.FuncAnimation(
            self.figure, self._update_graph, interval=1000, blit=False
        )
        
        # Handle window close
        def on_closing():
            if self.animation:
                self.animation.event_source.stop()
            self.graph_window.destroy()
            self.graph_window = None
        
        self.graph_window.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Initial graph update
        self._update_graph(0)
        
        return self.graph_window
    
    def _update_graph(self, frame):
        """Update the graph with current data"""
        if not self.timestamps or len(self.timestamps) == 0:
            return
        
        # Clear previous plot
        self.ax.clear()
        
        # Convert timestamps to relative time (seconds from start)
        if len(self.timestamps) > 0:
            start_time = self.timestamps[0]
            relative_times = [(t - start_time) for t in self.timestamps]
        else:
            relative_times = []
        
        # Plot CWND
        if len(relative_times) > 0:
            self.ax.plot(relative_times, self.cwnd_values, 'b-', linewidth=2, 
                        label='CWND (Congestion Window)', marker='o', markersize=3)
            
            # Plot SSTHRESH
            self.ax.plot(relative_times, self.ssthresh_values, 'r--', linewidth=2,
                        label='SSTHRESH (Slow Start Threshold)', alpha=0.7)
            
            # Mark different states with colors
            slow_start_times = []
            slow_start_cwnd = []
            congestion_avoid_times = []
            congestion_avoid_cwnd = []
            fast_recovery_times = []
            fast_recovery_cwnd = []
            
            for i, (time, cwnd, state) in enumerate(zip(relative_times, self.cwnd_values, self.states)):
                if state == "SLOW_START":
                    slow_start_times.append(time)
                    slow_start_cwnd.append(cwnd)
                elif state == "CONGESTION_AVOIDANCE":
                    congestion_avoid_times.append(time)
                    congestion_avoid_cwnd.append(cwnd)
                elif state == "FAST_RECOVERY":
                    fast_recovery_times.append(time)
                    fast_recovery_cwnd.append(cwnd)
            
            # Plot state-specific points
            if slow_start_times:
                self.ax.scatter(slow_start_times, slow_start_cwnd, c='green', s=20, 
                               alpha=0.6, label='Slow Start', marker='^')
            if congestion_avoid_times:
                self.ax.scatter(congestion_avoid_times, congestion_avoid_cwnd, c='blue', s=20,
                               alpha=0.6, label='Congestion Avoidance', marker='s')
            if fast_recovery_times:
                self.ax.scatter(fast_recovery_times, fast_recovery_cwnd, c='red', s=30,
                               alpha=0.8, label='Fast Recovery', marker='X')
            
            # Mark special events
            for event in self.events:
                event_time = event['time'] - start_time
                event_cwnd = event['cwnd']
                event_type = event['event']
                
                if event_time >= min(relative_times) and event_time <= max(relative_times):
                    if 'fast_retransmit' in event_type.lower():
                        self.ax.annotate('Fast Retransmit', xy=(event_time, event_cwnd),
                                        xytext=(event_time, event_cwnd + 2), 
                                        arrowprops=dict(arrowstyle='->', color='red'),
                                        fontsize=8, color='red', weight='bold')
                    elif 'timeout' in event_type.lower():
                        self.ax.annotate('Timeout', xy=(event_time, event_cwnd),
                                        xytext=(event_time, event_cwnd + 2),
                                        arrowprops=dict(arrowstyle='->', color='orange'),
                                        fontsize=8, color='orange', weight='bold')
        
        # Formatting
        self.ax.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
        self.ax.set_ylabel('Window Size (packets)', fontsize=12, fontweight='bold')
        self.ax.set_title('TCP Reno Congestion Control Algorithm\nCongestion Window vs Time', 
                         fontsize=14, fontweight='bold')
        self.ax.grid(True, alpha=0.3)
        self.ax.legend(loc='upper left', fontsize=10)
        
        # Set reasonable y-axis limits
        if self.cwnd_values:
            max_val = max(max(self.cwnd_values), max(self.ssthresh_values))
            self.ax.set_ylim(0, max_val * 1.1)
        
        # Add statistics text box
        if len(self.cwnd_values) > 0:
            current_cwnd = self.cwnd_values[-1]
            current_ssthresh = self.ssthresh_values[-1]
            current_state = self.states[-1] if self.states else "Unknown"
            
            stats_text = f'Current CWND: {current_cwnd:.1f}\n'
            stats_text += f'Current SSTHRESH: {current_ssthresh:.1f}\n'
            stats_text += f'Current State: {current_state}\n'
            stats_text += f'Data Points: {len(self.cwnd_values)}\n'
            stats_text += f'Events: {len(self.events)}'
            
            self.ax.text(0.02, 0.98, stats_text, transform=self.ax.transAxes,
                        fontsize=10, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # Refresh canvas
        if self.canvas:
            self.canvas.draw()
    
    def generate_static_graph(self, save_path=None):
        """Generate and save a static graph image"""
        if not self.timestamps:
            print("No data available for graph generation")
            return None
        
        # Create figure
        fig = plt.figure(figsize=(12, 8), dpi=150)
        ax = fig.add_subplot(111)
        
        # Convert timestamps to relative time
        start_time = self.timestamps[0]
        relative_times = [(t - start_time) for t in self.timestamps]
        
        # Plot data
        ax.plot(relative_times, self.cwnd_values, 'b-', linewidth=2, 
               label='CWND (Congestion Window)', marker='o', markersize=3)
        ax.plot(relative_times, self.ssthresh_values, 'r--', linewidth=2,
               label='SSTHRESH (Slow Start Threshold)', alpha=0.7)
        
        # Mark events
        for event in self.events:
            event_time = event['time'] - start_time
            event_cwnd = event['cwnd']
            event_type = event['event']
            
            if 'fast_retransmit' in event_type.lower():
                ax.scatter([event_time], [event_cwnd], c='red', s=100, marker='X', 
                          label='Fast Retransmit' if 'Fast Retransmit' not in [h.get_label() for h in ax.get_children()] else "")
            elif 'timeout' in event_type.lower():
                ax.scatter([event_time], [event_cwnd], c='orange', s=100, marker='v',
                          label='Timeout' if 'Timeout' not in [h.get_label() for h in ax.get_children()] else "")
        
        # Formatting
        ax.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Window Size (packets)', fontsize=12, fontweight='bold')
        ax.set_title(f'TCP Reno Algorithm - CWND Evolution\nUser: {self.username}', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Save or show
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Graph saved to: {save_path}")
        else:
            save_path = f"tcp_reno_graph_{self.username}_{int(time.time())}.png"
            fig.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Graph saved to: {save_path}")
        
        plt.close(fig)
        return save_path

# Global grapher instance
_grapher_instance = None

def get_grapher(username="User"):
    """Get or create grapher instance"""
    global _grapher_instance
    if _grapher_instance is None:
        _grapher_instance = TCPRenoGrapher(username)
    return _grapher_instance

def record_cwnd_point(cwnd, ssthresh, state, event_type=None):
    """Record a data point for graphing"""
    if _grapher_instance:
        _grapher_instance.record_data_point(cwnd, ssthresh, state, event_type)

def show_graph(master_window=None):
    """Show real-time graph window"""
    if _grapher_instance:
        return _grapher_instance.show_realtime_graph(master_window)
    return None

def start_graph_recording():
    """Start recording graph data"""
    if _grapher_instance:
        _grapher_instance.start_recording()

def stop_graph_recording():
    """Stop recording graph data"""
    if _grapher_instance:
        _grapher_instance.stop_recording()

def clear_graph_data():
    """Clear all graph data"""
    if _grapher_instance:
        _grapher_instance.clear_data()

def save_graph(save_path=None):
    """Save current graph as image"""
    if _grapher_instance:
        return _grapher_instance.generate_static_graph(save_path)
    return None

if __name__ == "__main__":
    # Test the grapher
    print("Testing TCP Reno Grapher...")
    
    # Create test data
    grapher = TCPRenoGrapher("TestUser")
    grapher.start_recording()
    
    # Simulate some data points
    import time
    for i in range(50):
        if i < 10:
            # Slow start phase
            cwnd = 2 ** i if 2 ** i < 32 else 32
            state = "SLOW_START"
        elif i < 30:
            # Congestion avoidance
            cwnd = 32 + (i - 10) * 0.5
            state = "CONGESTION_AVOIDANCE"
        else:
            # With some events
            if i == 35:
                cwnd = 25  # Fast retransmit
                state = "FAST_RECOVERY"
                grapher.record_data_point(cwnd, 32, state, "fast_retransmit")
                continue
            else:
                cwnd = 25 + (i - 35) * 0.3
                state = "CONGESTION_AVOIDANCE"
        
        grapher.record_data_point(cwnd, 32, state)
        time.sleep(0.1)
    
    # Show graph
    window = grapher.show_realtime_graph()
    if window:
        window.mainloop()
