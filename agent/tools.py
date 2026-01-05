"""Network diagnosis tools for the agent.

These tools simulate querying network devices and P4 switches.
In a production environment, these would connect to real network infrastructure
via Netmiko, gRPC, or vendor APIs.
"""
import random
from typing import Optional
from langchain_core.tools import tool


# Mock State for P4 Registers
# Simulating a Tofino switch register tracking queue depths or drop counters
P4_REGISTERS = {
    "cs-core-01": {
        "egress_queue_depth": [random.randint(0, 100) for _ in range(128)],
        "drop_counter": [random.randint(0, 50) for _ in range(128)]
    },
    "cs-core-02": {
        "egress_queue_depth": [random.randint(0, 100) for _ in range(128)],
        "drop_counter": [random.randint(0, 50) for _ in range(128)]
    }
}


@tool
def fetch_logs(device_id: str, count: int = 10) -> str:
    """Fetch the most recent syslog entries from a network device.
    
    Use this tool when you need to investigate what's happening on a device,
    especially for latency issues, routing problems, or general diagnostics.
    
    Args:
        device_id: The device hostname (e.g., "cs-core-01", "cs-access-01")
        count: Number of log entries to retrieve (default: 10)
    
    Returns:
        Recent syslog entries from the device
    """
    logs = []
    timestamp = "Jan 05 10:00:00"
    
    if "core" in device_id:
        logs.extend([
            f"<189> {timestamp} {device_id} %OSPF-5-ADJCHG: Process 1, Nbr 10.0.0.2 on Gi0/0 from FULL to DOWN",
            f"<190> {timestamp} {device_id} %BGP-5-ADJCHANGE: neighbor 10.0.0.5 Up",
            f"<187> {timestamp} {device_id} %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet0/1, changed state to up",
            f"<186> {timestamp} {device_id} %SYS-5-CONFIG_I: Configured from console by admin",
        ])
    elif "access" in device_id:
        logs.extend([
            f"<189> {timestamp} {device_id} %LINK-3-UPDOWN: Interface GigabitEthernet0/0/1, changed state to down",
            f"<190> {timestamp} {device_id} %LINEPROTO-5-UPDOWN: Line protocol on Interface Gi0/0/1, changed state to down",
            f"<187> {timestamp} {device_id} %SPANNING_TREE-5-TOPOTRANSITION: Topology change on port Gi0/0/2",
        ])
    else:
        logs.append(f"<190> {timestamp} {device_id} %SYS-5-RESTART: System restarted")
    
    return "\n".join(logs[:count])


@tool
def check_interface_status(device_id: str, interface: str) -> str:
    """Check the status of a specific interface on a network device.
    
    Use this tool when you suspect an interface might be down or experiencing errors.
    Simulates 'show interface <interface>' CLI command.
    
    Args:
        device_id: The device hostname (e.g., "cs-access-01")
        interface: The interface name (e.g., "GigabitEthernet0/0/1")
    
    Returns:
        Interface status including admin state, protocol state, and error counters
    """
    # Simulate a down interface for specific scenario
    if device_id == "cs-access-01" and "0/0/1" in interface:
        status = "administratively down"
        protocol = "down"
        input_errors = 0
        crc_errors = 0
    else:
        status = "up"
        protocol = "up"
        input_errors = random.randint(0, 100)
        crc_errors = random.randint(0, 10)
    
    return f"""Interface {interface}
  Hardware is Gigabit Ethernet
  Internet address is 10.0.1.1/24
  MTU 1500 bytes, BW 1000000 Kbit/sec
  Line protocol is {protocol}
  Admin status: {status}
  Input errors: {input_errors}, CRC: {crc_errors}
  Output errors: 0, collisions: 0"""


@tool
def read_p4_register(device_id: str, register_name: str, index: Optional[int] = None) -> str:
    """Query a P4 switch register for data plane telemetry.
    
    Use this tool to get low-level telemetry from P4/Tofino switches,
    such as queue depths (for congestion) or drop counters (for packet loss).
    
    Args:
        device_id: The P4 switch identifier (e.g., "cs-core-01")
        register_name: Register to query ("egress_queue_depth" or "drop_counter")
        index: Optional specific index in the register array
    
    Returns:
        Register values indicating queue depth or drop counts
    """
    if device_id not in P4_REGISTERS:
        return f"Error: Device {device_id} not found or not P4-capable."
        
    if register_name not in P4_REGISTERS[device_id]:
        return f"Error: Register {register_name} not found. Available: egress_queue_depth, drop_counter"
    
    reg_array = P4_REGISTERS[device_id][register_name]
    
    # Simulate congestion scenario randomly
    if register_name == "egress_queue_depth" and random.random() < 0.4:
        high_values = [random.randint(8000, 15000) for _ in range(5)]
        return f"""Register {register_name} on {device_id}:
  WARNING: High queue depth detected!
  Indices 0-4: {high_values}
  Threshold: 5000
  Status: CONGESTION DETECTED"""
    
    if index is not None:
        if 0 <= index < len(reg_array):
            return f"Register {register_name}[{index}] = {reg_array[index]}"
        else:
            return "Error: Index out of bounds (valid: 0-127)"
    
    return f"""Register {register_name} on {device_id}:
  Values (indices 0-9): {reg_array[:10]}
  Status: Normal"""


@tool  
def propose_config_change(device_id: str, config_commands: list[str]) -> str:
    """Generate a configuration change proposal for a network device.
    
    Use this tool AFTER you have diagnosed the root cause and want to propose a fix.
    This validates the commands and generates a config block (does NOT apply it).
    
    Args:
        device_id: The target device for the configuration
        config_commands: List of CLI commands to propose
    
    Returns:
        A formatted configuration block ready for review, or an error if unsafe commands detected
    """
    # Safety validation
    forbidden_commands = ["reload", "delete flash:", "no router bgp", "write erase"]
    
    for cmd in config_commands:
        for forbidden in forbidden_commands:
            if forbidden in cmd.lower():
                return f"ERROR: Unsafe command detected: '{cmd}'. This command is not allowed."
    
    config_block = f"""
================================================================================
PROPOSED CONFIGURATION CHANGE
================================================================================
Target Device: {device_id}
Generated by: NetworkAgent
Status: PENDING REVIEW

--------------------------------------------------------------------------------
configure terminal
{chr(10).join('  ' + cmd for cmd in config_commands)}
end
write memory
--------------------------------------------------------------------------------

⚠️  This configuration has NOT been applied.
    Please review and apply manually or approve for automated deployment.
================================================================================
"""
    return config_block


# Export all tools for the agent
tools = [fetch_logs, check_interface_status, read_p4_register, propose_config_change]
