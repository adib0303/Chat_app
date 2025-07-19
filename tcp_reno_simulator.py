#!/usr/bin/env python3
"""
TCP Reno Algorithm Implementation for Chat Application
Complete implementation of TCP Reno congestion control with Fast Recovery
"""

import random
import time

# Import graphing module for automated CWND graphing
try:
    from tcp_reno_graph import record_cwnd_point
    GRAPH_AVAILABLE = True
except ImportError:
    GRAPH_AVAILABLE = False
    def record_cwnd_point(*args, **kwargs):
        pass  # No-op if graphing not available

class TCPRenoController:
    def __init__(self, username="User"):
        self.username = username
        
        # TCP Reno state variables
        self.cwnd = 1.0          # Congestion window (MSS units)
        self.ssthresh = 64.0     # Slow start threshold
        self.state = "SLOW_START"
        
        # Fast retransmit/recovery variables
        self.duplicate_acks = 0
        self.last_ack = 0
        self.high_seq = 0        # Highest sequence number sent
        
        # Statistics
        self.packets_sent = 0
        self.retransmissions = 0
        self.fast_retransmits = 0
        self.timeouts = 0
        self.enabled = True
        
        # Network simulation
        self.base_loss_rate = 0.02
        self.current_loss_rate = 0.02
        
    def simulate_reno_transmission(self, data, data_type="message"):
        """Simulate TCP Reno transmission with full algorithm"""
        if not self.enabled:
            return True
            
        data_size = len(str(data))
        
        # Adjust network conditions based on data size
        self._adjust_network_conditions(data_size)
        
        # Calculate packets needed (MSS = 500 bytes)
        mss = 500
        total_packets = max(1, (data_size + mss - 1) // mss)
        
        print(f"[RENO-{self.username}] 🚀 {data_type.upper()}: {data_size}B → {total_packets} packets")
        print(f"[RENO-{self.username}] 📊 Initial: CWND={self.cwnd:.1f}, SSTHRESH={self.ssthresh:.1f}, STATE={self.state}")
        
        # Record initial state for graph
        record_cwnd_point(self.cwnd, self.ssthresh, self.state)
        
        # Simulate packet-by-packet transmission with Reno algorithm
        packets_acked = 0
        consecutive_losses = 0
        
        for seq_num in range(total_packets):
            self.high_seq = seq_num
            
            # Check if we can send (congestion window constraint)
            window_full = (seq_num - packets_acked) >= int(self.cwnd)
            if window_full:
                print(f"[RENO-{self.username}] ⏸️  Window full (outstanding: {seq_num - packets_acked}, cwnd: {int(self.cwnd)})")
                # Simulate waiting for ACKs to open window
                if random.random() < 0.7:  # 70% chance ACK arrives
                    packets_acked += 1
                    self._process_ack(packets_acked - 1, is_new_ack=True)
            
            # Simulate packet transmission
            if self._simulate_packet_loss():
                # Packet lost
                print(f"[RENO-{self.username}] 💥 Packet {seq_num} LOST")
                consecutive_losses += 1
                
                if consecutive_losses >= 3:
                    # Simulate 3 duplicate ACKs → Fast Retransmit
                    print(f"[RENO-{self.username}] ⚡ 3 Duplicate ACKs → Fast Retransmit")
                    self._handle_fast_retransmit()
                    consecutive_losses = 0
                elif consecutive_losses >= 1 and random.random() < 0.3:
                    # Simulate timeout
                    print(f"[RENO-{self.username}] ⏰ Timeout → Slow Start")
                    self._handle_timeout()
                    consecutive_losses = 0
            else:
                # Packet successfully transmitted
                consecutive_losses = 0
                self.packets_sent += 1
                
                # Simulate ACK reception (80% success rate)
                if random.random() < 0.8:
                    packets_acked += 1
                    is_new_ack = seq_num >= self.last_ack
                    self._process_ack(seq_num, is_new_ack)
                    print(f"[RENO-{self.username}] ✅ ACK {seq_num} → CWND={self.cwnd:.1f}")
                else:
                    print(f"[RENO-{self.username}] ⏳ ACK {seq_num} delayed/lost")
        
        # Final statistics
        efficiency = (packets_acked / total_packets) * 100 if total_packets > 0 else 100
        print(f"[RENO-{self.username}] 🎯 === TCP RENO COMPLETE ===")
        print(f"[RENO-{self.username}] 📈 Efficiency: {efficiency:.0f}%")
        print(f"[RENO-{self.username}] 📊 Final CWND: {self.cwnd:.1f}")
        print(f"[RENO-{self.username}] 🏁 Final State: {self.state}")
        print(f"[RENO-{self.username}] 🔄 Fast Retransmits: {self.fast_retransmits}")
        print(f"[RENO-{self.username}] ⏰ Timeouts: {self.timeouts}")
        print(f"[RENO-{self.username}] ================================")
        
        return True
    
    def _process_ack(self, ack_seq, is_new_ack):
        """Process ACK according to TCP Reno algorithm"""
        old_cwnd = self.cwnd
        old_state = self.state
        
        if is_new_ack:
            # New ACK received
            self.duplicate_acks = 0
            self.last_ack = ack_seq
            
            if self.state == "SLOW_START":
                # Slow Start: cwnd += 1 for each ACK (exponential growth)
                self.cwnd += 1
                
                # Transition to Congestion Avoidance when cwnd >= ssthresh
                if self.cwnd >= self.ssthresh:
                    self.state = "CONGESTION_AVOIDANCE"
                    print(f"[RENO-{self.username}] 🚦 SLOW_START → CONGESTION_AVOIDANCE (cwnd={self.cwnd:.1f})")
                
            elif self.state == "CONGESTION_AVOIDANCE":
                # Congestion Avoidance: cwnd += 1/cwnd for each ACK (linear growth)
                self.cwnd += 1.0 / self.cwnd
                
            elif self.state == "FAST_RECOVERY":
                # Fast Recovery: exit when new ACK received
                self.cwnd = self.ssthresh
                self.state = "CONGESTION_AVOIDANCE"
                print(f"[RENO-{self.username}] 🏃 FAST_RECOVERY → CONGESTION_AVOIDANCE (cwnd={self.cwnd:.1f})")
        else:
            # Duplicate ACK
            self.duplicate_acks += 1
            
            if self.duplicate_acks == 3 and self.state != "FAST_RECOVERY":
                # Triple duplicate ACK → Fast Retransmit
                self._handle_fast_retransmit()
            elif self.state == "FAST_RECOVERY":
                # In Fast Recovery: inflate window for each additional duplicate ACK
                self.cwnd += 1
                print(f"[RENO-{self.username}] 🎈 Fast Recovery window inflation → CWND={self.cwnd:.1f}")
        
        # Record CWND change for graph if significant change occurred
        if abs(self.cwnd - old_cwnd) > 0.01 or self.state != old_state:
            record_cwnd_point(self.cwnd, self.ssthresh, self.state)
    
    def _handle_fast_retransmit(self):
        """Handle Fast Retransmit and enter Fast Recovery (TCP Reno)"""
        print(f"[RENO-{self.username}] ⚡ === FAST RETRANSMIT TRIGGERED ===")
        
        # 1. Set ssthresh = cwnd / 2
        self.ssthresh = max(self.cwnd / 2, 2)
        
        # 2. Set cwnd = ssthresh + 3 (for the 3 duplicate ACKs)
        self.cwnd = self.ssthresh + 3
        
        # 3. Enter Fast Recovery state
        self.state = "FAST_RECOVERY"
        
        # 4. Retransmit the lost packet
        self.fast_retransmits += 1
        self.retransmissions += 1
        
        print(f"[RENO-{self.username}] 📉 SSTHRESH: {self.ssthresh:.1f}")
        print(f"[RENO-{self.username}] 📊 CWND: {self.cwnd:.1f} (ssthresh + 3)")
        print(f"[RENO-{self.username}] 🏃 STATE: FAST_RECOVERY")
        print(f"[RENO-{self.username}] 🔄 Retransmitting lost packet")
        
        # Record fast retransmit event for graph
        record_cwnd_point(self.cwnd, self.ssthresh, self.state, "fast_retransmit")
    
    def _handle_timeout(self):
        """Handle timeout (severe congestion)"""
        print(f"[RENO-{self.username}] ⏰ === TIMEOUT OCCURRED ===")
        
        # 1. Set ssthresh = cwnd / 2
        self.ssthresh = max(self.cwnd / 2, 2)
        
        # 2. Set cwnd = 1 (back to slow start)
        self.cwnd = 1
        
        # 3. Enter Slow Start state
        self.state = "SLOW_START"
        
        # 4. Reset duplicate ACK counter
        self.duplicate_acks = 0
        
        # 5. Update statistics
        self.timeouts += 1
        self.retransmissions += 1
        
        print(f"[RENO-{self.username}] 📉 SSTHRESH: {self.ssthresh:.1f}")
        print(f"[RENO-{self.username}] 📊 CWND: 1.0 (reset)")
        print(f"[RENO-{self.username}] 🐌 STATE: SLOW_START")
        print(f"[RENO-{self.username}] 🔄 Retransmitting from beginning")
        
        # Record timeout event for graph
        record_cwnd_point(self.cwnd, self.ssthresh, self.state, "timeout")
    
    def _simulate_packet_loss(self):
        """Simulate packet loss based on current network conditions"""
        return random.random() < self.current_loss_rate
    
    def _adjust_network_conditions(self, data_size):
        """Adjust network conditions based on data size"""
        if data_size > 2000:  # Large files
            self.current_loss_rate = 0.12  # 12% loss rate
            congestion_level = "SEVERE"
        elif data_size > 1000:
            self.current_loss_rate = 0.08  # 8% loss rate
            congestion_level = "HIGH"
        elif data_size > 500:
            self.current_loss_rate = 0.05  # 5% loss rate
            congestion_level = "MEDIUM"
        else:
            self.current_loss_rate = 0.02  # 2% loss rate
            congestion_level = "LOW"
        
        print(f"[RENO-{self.username}] 🌐 Network Congestion: {congestion_level} (Loss: {self.current_loss_rate*100:.0f}%)")
    
    def get_detailed_stats(self):
        """Get detailed TCP Reno statistics"""
        return {
            'cwnd': self.cwnd,
            'ssthresh': self.ssthresh,
            'state': self.state,
            'packets_sent': self.packets_sent,
            'retransmissions': self.retransmissions,
            'fast_retransmits': self.fast_retransmits,
            'timeouts': self.timeouts,
            'loss_rate': self.current_loss_rate,
            'enabled': self.enabled,
            'algorithm': 'TCP Reno'
        }
    
    def reset_stats(self):
        """Reset statistics counters"""
        self.packets_sent = 0
        self.retransmissions = 0
        self.fast_retransmits = 0
        self.timeouts = 0
        print(f"[RENO-{self.username}] 🔄 Statistics reset")

# Global TCP Reno controller
reno_controller = None

def initialize_reno(username):
    """Initialize TCP Reno controller"""
    global reno_controller
    reno_controller = TCPRenoController(username)
    
    # Initialize graph recording if available
    if GRAPH_AVAILABLE:
        from tcp_reno_graph import get_grapher
        grapher = get_grapher(username)
        print(f"[RENO] 📊 Graph recording initialized for {username}")
    
    print(f"[RENO] 🚀 TCP Reno algorithm initialized for {username}")

def simulate_reno_transmission(data, data_type="message"):
    """Simulate TCP Reno transmission"""
    global reno_controller
    if reno_controller is None:
        return True
    return reno_controller.simulate_reno_transmission(data, data_type)

def get_reno_stats():
    """Get TCP Reno statistics"""
    global reno_controller
    if reno_controller is None:
        return "TCP Reno not initialized"
    return reno_controller.get_detailed_stats()

def toggle_reno(enabled=None):
    """Enable/disable TCP Reno simulation"""
    global reno_controller
    if reno_controller is None:
        return False
    if enabled is None:
        reno_controller.enabled = not reno_controller.enabled
    else:
        reno_controller.enabled = enabled
    status = "ENABLED" if reno_controller.enabled else "DISABLED"
    print(f"[RENO] 🔧 TCP Reno simulation {status}")
    return reno_controller.enabled

def reset_reno_stats():
    """Reset TCP Reno statistics"""
    global reno_controller
    if reno_controller is not None:
        reno_controller.reset_stats()
        return True
    return False

def show_reno_graph(master_window=None):
    """Show TCP Reno CWND graph"""
    if GRAPH_AVAILABLE:
        from tcp_reno_graph import get_grapher, show_graph
        # Initialize grapher for current user if needed
        username = reno_controller.username if reno_controller else "User"
        grapher = get_grapher(username)
        return show_graph(master_window)
    else:
        print("[RENO] Graphing module not available")
        return None

def start_graph_recording():
    """Start recording data for graph"""
    if GRAPH_AVAILABLE:
        from tcp_reno_graph import start_graph_recording as start_recording
        start_recording()
        return True
    return False

def stop_graph_recording():
    """Stop recording data for graph"""
    if GRAPH_AVAILABLE:
        from tcp_reno_graph import stop_graph_recording as stop_recording
        stop_recording()
        return True
    return False

def save_reno_graph(file_path=None):
    """Save current graph as image"""
    if GRAPH_AVAILABLE:
        from tcp_reno_graph import save_graph
        return save_graph(file_path)
    return None
