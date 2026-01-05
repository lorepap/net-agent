#!/usr/bin/env python3
"""
Non-interactive test of BMv2 + Mininet setup.
Runs automated tests and reports results.
"""

import os
import sys
import time
import subprocess
import signal

from mininet.net import Mininet
from mininet.node import Host
from mininet.log import setLogLevel, info, error
from mininet.link import Intf

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
P4_JSON = os.path.join(PROJECT_ROOT, "p4src", "basic_forward.json")

# Global for cleanup
bmv2_process = None


def cleanup():
    """Cleanup any leftover processes and interfaces."""
    os.system("killall -9 simple_switch_grpc 2>/dev/null")
    os.system("mn -c 2>/dev/null")
    # Clean up any veth pairs we created
    os.system("ip link del veth0 2>/dev/null")
    os.system("ip link del veth1 2>/dev/null")


def start_bmv2(intf1, intf2, json_path, thrift_port=9090):
    """Start BMv2 switch manually."""
    global bmv2_process
    
    cmd = [
        'simple_switch_grpc',
        '-i', f'1@{intf1}',
        '-i', f'2@{intf2}',
        '--thrift-port', str(thrift_port),
        '--device-id', '1',
        '--log-console',
        json_path,  # JSON path must come before --
        '--',
        '--grpc-server-addr', '0.0.0.0:50051',
    ]
    
    print(f"Starting BMv2: {' '.join(cmd)}")
    
    log_file = open('/tmp/bmv2_test.log', 'w')
    bmv2_process = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    
    # Wait for switch to start and check if it's running
    time.sleep(3)
    
    if bmv2_process.poll() is not None:
        print(f"BMv2 failed to start! Exit code: {bmv2_process.returncode}")
        log_file.close()
        with open('/tmp/bmv2_test.log', 'r') as f:
            print(f"Log output:\n{f.read()}")
        return False
    
    print(f"BMv2 started (PID: {bmv2_process.pid})")
    return True


def stop_bmv2():
    """Stop BMv2 switch."""
    global bmv2_process
    if bmv2_process:
        bmv2_process.terminate()
        bmv2_process.wait()
        print("BMv2 stopped")


def install_rules(thrift_port=9090):
    """Install forwarding rules."""
    rules = [
        "table_add forward_table forward 1 => 2",
        "table_add forward_table forward 2 => 1",
    ]
    for rule in rules:
        result = os.system(f"echo '{rule}' | simple_switch_CLI --thrift-port {thrift_port} 2>&1")
        if result != 0:
            return False
    return True


def clear_rules(thrift_port=9090):
    """Clear forwarding rules."""
    os.system(f"echo 'table_clear forward_table' | simple_switch_CLI --thrift-port {thrift_port} 2>&1")


def run_test():
    """Run the BMv2 test."""
    
    print("="*60)
    print("BMv2 + MININET INTEGRATION TEST")
    print("="*60)
    
    # Cleanup first
    print("\n*** Cleaning up previous runs...")
    cleanup()
    time.sleep(1)
    
    # Check P4 JSON exists
    if not os.path.exists(P4_JSON):
        print(f"❌ P4 JSON not found: {P4_JSON}")
        return False
    print(f"✓ P4 JSON found: {P4_JSON}")
    
    # Create veth pairs for the switch
    print("\n*** Creating virtual interfaces...")
    os.system("ip link add veth0 type veth peer name veth1")
    os.system("ip link add veth2 type veth peer name veth3")
    os.system("ip link set veth0 up")
    os.system("ip link set veth1 up")
    os.system("ip link set veth2 up")
    os.system("ip link set veth3 up")
    print("✓ Virtual interfaces created")
    
    # Start BMv2 switch
    print("\n*** Starting BMv2 switch...")
    if not start_bmv2('veth1', 'veth3', P4_JSON):
        print("❌ Failed to start BMv2")
        cleanup()
        return False
    print("✓ BMv2 switch started")
    
    # Create network with hosts
    print("\n*** Creating Mininet hosts...")
    setLogLevel('warning')
    net = Mininet(controller=None)
    
    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    
    net.start()
    
    # Move veth0 and veth2 into host namespaces
    # First we need to get the PIDs
    h1_pid = h1.pid
    h2_pid = h2.pid
    
    # Move interfaces into namespaces
    os.system(f'ip link set veth0 netns {h1_pid}')
    os.system(f'ip link set veth2 netns {h2_pid}')
    
    # Configure h1's interface
    h1.cmd('ip link set veth0 up')
    h1.cmd('ip addr add 10.0.0.1/24 dev veth0')
    h1.cmd('ip link set veth0 address 00:00:00:00:00:01')
    h1.cmd('ip route add default dev veth0')
    h1.cmd('arp -s 10.0.0.2 00:00:00:00:00:02')
    
    # Configure h2's interface
    h2.cmd('ip link set veth2 up')
    h2.cmd('ip addr add 10.0.0.2/24 dev veth2')
    h2.cmd('ip link set veth2 address 00:00:00:00:00:02')
    h2.cmd('ip route add default dev veth2')
    h2.cmd('arp -s 10.0.0.1 00:00:00:00:00:01')
    
    print("✓ Mininet hosts created and configured")
    
    try:
        # Test 1: Ping should fail (no rules installed)
        print("\n--- Test 1: Ping without forwarding rules ---")
        result = h1.cmd('ping -c 2 -W 1 10.0.0.2')
        if '0 received' in result or '100% packet loss' in result:
            print("✓ Ping failed as expected (no rules)")
            test1_pass = True
        else:
            print(f"⚠ Unexpected ping result:\n{result}")
            test1_pass = False
        
        # Install forwarding rules
        print("\n--- Installing forwarding rules ---")
        if install_rules():
            print("✓ Rules installed")
        else:
            print("⚠ Rule installation had issues")
        time.sleep(1)
        
        # Test 2: Ping should now work
        print("\n--- Test 2: Ping with forwarding rules ---")
        result = h1.cmd('ping -c 3 -W 2 10.0.0.2')
        print(f"Ping result:\n{result}")
        if ' 0% packet loss' in result or 'bytes from' in result:
            print("✓ Ping successful!")
            test2_pass = True
        else:
            print("❌ Ping still failing")
            test2_pass = False
        
        # Test 3: Read counters
        print("\n--- Test 3: Reading P4 registers ---")
        counter_output = subprocess.run(
            "echo 'register_read packet_counter 1' | simple_switch_CLI --thrift-port 9090",
            shell=True, capture_output=True, text=True
        )
        if 'packet_counter' in counter_output.stdout:
            print("✓ Counter read successful")
            for line in counter_output.stdout.split('\n'):
                if 'packet_counter' in line:
                    print(f"   {line.strip()}")
            test3_pass = True
        else:
            print(f"⚠ Could not read counters: {counter_output.stderr}")
            test3_pass = False
        
        # Test 4: Clear rules (simulate incident)
        print("\n--- Test 4: Clear rules (simulate incident) ---")
        clear_rules()
        time.sleep(1)
        result = h1.cmd('ping -c 2 -W 1 10.0.0.2')
        if '0 received' in result or '100% packet loss' in result:
            print("✓ Incident simulated - connectivity lost")
            test4_pass = True
        else:
            print("⚠ Ping still works after clearing rules")
            test4_pass = False
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        all_pass = test1_pass and test2_pass and test3_pass and test4_pass
        print(f"Test 1 (No rules = no ping):    {'✓ PASS' if test1_pass else '❌ FAIL'}")
        print(f"Test 2 (With rules = ping OK):  {'✓ PASS' if test2_pass else '❌ FAIL'}")
        print(f"Test 3 (Read P4 registers):     {'✓ PASS' if test3_pass else '❌ FAIL'}")
        print(f"Test 4 (Incident simulation):   {'✓ PASS' if test4_pass else '❌ FAIL'}")
        print("="*60)
        print(f"Overall: {'✓ ALL TESTS PASSED' if all_pass else '❌ SOME TESTS FAILED'}")
        print("="*60)
        
        return all_pass
        
    finally:
        print("\n*** Cleaning up...")
        net.stop()
        stop_bmv2()
        cleanup()


if __name__ == '__main__':
    if os.geteuid() != 0:
        print("Error: Must run as root (sudo)")
        sys.exit(1)
    
    success = run_test()
    sys.exit(0 if success else 1)
