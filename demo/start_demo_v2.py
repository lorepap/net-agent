#!/usr/bin/env python3
"""
Interactive Demo Environment for Network Agent (V2).
Starts Mininet + BMv2 (Thrift Mode) and drops into CLI.
"""

import os
import sys
import time
import subprocess
from mininet.net import Mininet
from mininet.node import Host
from mininet.cli import CLI
from mininet.link import Intf
from mininet.log import setLogLevel

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
P4_JSON = os.path.join(PROJECT_ROOT, "p4src", "basic_forward.json")

bmv2_process = None

def start_bmv2(intf1, intf2, json_path, thrift_port=9090):
    global bmv2_process
    # Using simple_switch (Thrift) guarantees port 9090 is available
    cmd = [
        'simple_switch',
        '-i', f'1@{intf1}', '-i', f'2@{intf2}',
        '--thrift-port', str(thrift_port),
        '--device-id', '1',
        '--log-console',
        json_path
    ]
    print(f"Starting BMv2 (Thrift): {' '.join(cmd)}")
    
    # Log to file for debugging
    with open('/tmp/bmv2_demo.log', 'w') as f:
        bmv2_process = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
    time.sleep(2)
    return bmv2_process.poll() is None

def install_rules(thrift_port=9090):
    rules = ["table_add forward_table forward 1 => 2", "table_add forward_table forward 2 => 1"]
    for rule in rules:
        cmd = f"echo '{rule}' | simple_switch_CLI --thrift-port {thrift_port} > /dev/null"
        if os.system(cmd) != 0:
            print(f"⚠️ Failed to install rule: {rule}")
    print("✓ Initial forwarding rules installed (Ping should work)")

def cleanup():
    os.system("killall -9 simple_switch 2>/dev/null")
    os.system("killall -9 simple_switch_grpc 2>/dev/null")
    os.system("mn -c 2>/dev/null")
    os.system("ip link del veth0 2>/dev/null; ip link del veth1 2>/dev/null")
    os.system("ip link del veth2 2>/dev/null; ip link del veth3 2>/dev/null")

def run_demo():
    print("="*60 + "\n🚀 STARTING DEMO ENVIRONMENT V2 (Thrift)\n" + "="*60)
    cleanup()
    
    # 1. Setup Link Pairs
    os.system("ip link add veth0 type veth peer name veth1")
    os.system("ip link add veth2 type veth peer name veth3")
    for v in ["veth0", "veth1", "veth2", "veth3"]: os.system(f"ip link set {v} up")
    
    # 2. Start BMv2
    if not start_bmv2('veth1', 'veth3', P4_JSON):
        print("❌ BMv2 Failed -- check /tmp/bmv2_demo.log"); return

    # 3. Create Mininet
    net = Mininet(controller=None)
    h1 = net.addHost('h1')
    h2 = net.addHost('h2')
    
    # 4. Attach interfaces
    Intf('veth0', node=h1)
    Intf('veth2', node=h2)
    
    net.start()

    # 5. Configure Hosts
    h1.cmd('ip addr add 10.0.0.1/24 dev veth0')
    h1.cmd('ip link set veth0 address 00:00:00:00:00:01')
    h1.cmd('arp -s 10.0.0.2 00:00:00:00:00:02')
    
    h2.cmd('ip addr add 10.0.0.2/24 dev veth2')
    h2.cmd('ip link set veth2 address 00:00:00:00:00:02')
    h2.cmd('arp -s 10.0.0.1 00:00:00:00:00:01')

    # 6. Install Rules
    install_rules()
    
    print("\n✅ NETWORK READY!")
    print("   h1 (10.0.0.1) -- [BMv2] -- h2 (10.0.0.2)")
    print("\n   📊 MONITORING MODE: Checking connectivity every 2s...")
    print("   (Use Agent in Terminal 3 to fix the network)")
    print("   --------------------------------------------------")
    
    # Automatic Monitor Loop (No stdin/input required)
    import time
    failure_count = 0
    while True:
        try:
            # Run simple ping (timeout 0.5s)
            result = h1.cmd('ping -c 1 -W 0.5 10.0.0.2')
            timestamp = time.strftime('%H:%M:%S')
            
            if '1 received' in result:
                print(f"[ {timestamp} ] ✅ Ping SUCCESS")
                failure_count = 0
            else:
                print(f"[ {timestamp} ] ❌ Ping FAILED")
                failure_count += 1
                
            time.sleep(2)
        except KeyboardInterrupt:
            break
    
    # Cleanup only after exit


    net.stop()
    if bmv2_process: bmv2_process.terminate()
    cleanup()

if __name__ == '__main__':
    if os.geteuid() != 0: sys.exit("Run as root")
    run_demo()
