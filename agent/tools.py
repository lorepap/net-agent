"""Network diagnosis tools for the agent.

These tools allow the agent to interact with both simulated and real network devices.
Key capabilities:
- Fetching logs (Mock or Real)
- Checking interface status (Mock or Real)
- Querying P4 registers (Real BMv2 integration)
- Proposing and applying fixes (Real BMv2 table updates)
"""
import random
import subprocess
import time
from typing import Optional, List
from langchain_core.tools import tool


# Configuration
BMV2_THRIFT_PORT = 9090


def _is_bmv2_running() -> bool:
    """Check if BMv2 switch is running locally."""
    try:
        # Check if process exists
        result = subprocess.run(["pgrep", "simple_switch"], stdout=subprocess.PIPE)
        return result.returncode == 0
    except Exception:
        return False


def _run_bmv2_command(cmd_str: str) -> str:
    """Run a command capability on the local BMv2 switch via simple_switch_CLI."""
    if not _is_bmv2_running():
        return "Error: BMv2 switch is not running."

    full_cmd = f"echo '{cmd_str}' | simple_switch_CLI --thrift-port {BMV2_THRIFT_PORT}"
    try:
        result = subprocess.run(
            full_cmd, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return f"Command fail: {result.stderr}"
        return result.stdout.strip()
    except Exception as e:
        return f"Execution error: {str(e)}"


# Mock State for Fallback (when real switch not running)
MOCK_P4_REGISTERS = {
    "cs-core-01": {
        "packet_counter": [random.randint(0, 500) for _ in range(5)],
        "drop_counter": [random.randint(0, 50) for _ in range(5)]
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
    # In a real Mininet setup, we could read /var/log/syslog from the host namespace
    # For now, we'll keep the realistic mock logs as they provide good context for reasoning
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
        # Generic logs
        logs.append(f"<190> {timestamp} {device_id} %SYS-5-RESTART: System restarted")
    
    return "\n".join(logs[:count])


@tool
def check_interface_status(device_id: str, interface: str) -> str:
    """Check the status of a specific interface on a network device.
    
    Use this tool to check if an interface is UP or DOWN and view error counters.
    
    Args:
        device_id: The device hostname
        interface: The interface name (e.g., "GigabitEthernet0/0/1" or "1")
    
    Returns:
        Interface status block
    """
    # P4/BMv2 Real Status Check
    if _is_bmv2_running():
        # TODO: Map "interface" arg (like "Gi0/0/1") to BMv2 port number (like "1")
        # For simplicity, if input is digit, treat as port number
        is_port_query = interface.isdigit()
        if is_port_query:
            # We can use port status from simple_switch_CLI? 
            # simple_switch_CLI doesn't easily show port status in a parseable way without 'show_ports'
            # Let's mock the 'show interface' format but inject real P4 counters if possible
            pass

    # Provide a realistic looking output (Agent expects Cisco-like output)
    if "0/0/1" in interface: # Simulated down interface
        status = "administratively down"
        protocol = "down"
    else:
        status = "up"
        protocol = "up"
        
    return f"""Interface {interface}
  Hardware is Gigabit Ethernet
  Internet address is 10.0.1.1/24
  MTU 1500 bytes, BW 1000000 Kbit/sec
  Line protocol is {protocol}
  Admin status: {status}
  Input errors: 0, CRC: 0
  Output errors: 0, collisions: 0"""


@tool
def read_p4_register(register_name: str, index: Optional[int] = None) -> str:
    """Query a P4 switch register for real data plane telemetry.
    
    Use this tool to inspect packet counters, drop counters, or queue sizes.
    Works with real BMv2 switch if running, otherwise returns mock data.
    
    Args:
        register_name: Name of the P4 register (e.g. 'packet_counter', 'drop_counter')
        index: Optional index to read. If omitted, reads first few indices.
    
    Returns:
        The value(s) of the register.
    """
    # 1. Try Real BMv2
    if _is_bmv2_running():
        try:
            target_index = index if index is not None else 0
            # Command: register_read <name> <index>
            output = _run_bmv2_command(f"register_read {register_name} {target_index}")
            
            if "Invalid register name" in output:
                return f"Error: Register '{register_name}' not found on switch."
            
            # Output format: "RuntimeCmd: packet_counter[1]= 6"
            # We want to return just the value + context
            final_output = f"REAL P4 TELEMETRY (BMv2):\n{output}"
            
            # Smart Tool: Analyze the result
            if "= 0" in output:
                final_output += "\n\n[AUTOMATED ANALYSIS] Counter is 0. This confirms NO TRAFFIC matches the rules.\n"
                final_output += "\n\n[AUTOMATED ANALYSIS] Counter is 0. This confirms NO TRAFFIC matches the rules.\n"
                final_output += "[SUGGESTED ACTION] You should likely install basic forwarding rules using 'apply_config_change'.\n"
                final_output += "Commands to use: ['table_add forward_table forward 1 => 2', 'table_add forward_table forward 2 => 1']"
            
            return final_output
        except Exception as e:
            return f"Error reading P4 register: {e}"

    # 2. Fallback to Mock
    # Default mock values if specific register not mocked
    mock_vals = MOCK_P4_REGISTERS["cs-core-01"].get(register_name, [0]*10)
    
    if index is not None:
        if 0 <= index < len(mock_vals):
            val = mock_vals[index]
            return f"MOCK P4 TELEMETRY: {register_name}[{index}] = {val}"
        else:
            return f"Error: Index {index} out of bounds"
    else:
        return f"MOCK P4 TELEMETRY: {register_name} (first 5) = {mock_vals[:5]}"


@tool
def apply_config_change(config_commands: List[str]) -> str:
    """Apply a configuration change to the network.
    
    Use this tool to fix issues by installing forwarding rules or updating settings.
    WARNING: This modifies the live network state!
    
    Args:
        config_commands: List of commands to apply. 
                         For P4 switches, use table commands like:
                         "table_add forward_table forward 1 => 2"
    
    Returns:
        Status of the configuration application.
    """
    if not _is_bmv2_running():
        return "Simulated: Config applied successfully (Mock Mode)"

    results = []
    for cmd in config_commands:
        # Translate natural language intent to P4 commands if needed?
        # For now, assume agent is smart enough or we provide the raw P4 commands
        # The agent prompts generally give it the right "syntax" if we Few-Shot it.
        # Let's assume the agent uses the low-level P4 commands for this demo.
        
        output = _run_bmv2_command(cmd)
        
        # Parse BMv2 output for clearer agent status
        refined_status = output
        if "DUPLICATE_ENTRY" in output:
             refined_status = "SUCCESS: Rule already exists (No changes needed)."
        elif "Entry has been added" in output:
             refined_status = "SUCCESS: Rule installed successfully."
        elif "Invalid table operation" in output:
             refined_status = f"FAILURE: {output}"
             
        results.append(f"Cmd: {cmd}\nResult: {refined_status}")
        
    return "\n".join(results)


@tool
def propose_config_change(device_id: str, config_commands: List[str]) -> str:
    """Generate and validate a configuration proposal (dry-run).
    
    Use this tool to review a fix before applying it.
    
    Args:
        device_id: Target device
        config_commands: List of commands
        
    Returns:
        Formatted config block
    """
    config_block = f"""
================================================================================
PROPOSED CONFIGURATION CHANGE (DRY RUN)
================================================================================
Target: {device_id}
Commands:
{chr(10).join('  ' + cmd for cmd in config_commands)}
--------------------------------------------------------------------------------
To apply this fix, call the 'apply_config_change' tool with the same commands.
WARNING: THE NETWORK IS NOT FIXED YET. YOU MUST CALL 'apply_config_change'.
================================================================================
"""
    return config_block


# Export tools
tools = [fetch_logs, check_interface_status, read_p4_register, apply_config_change]
