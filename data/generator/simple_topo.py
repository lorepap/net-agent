#!/usr/bin/env python3
"""
Simple BMv2 Mininet Topology for Demo
--------------------------------------
Creates a minimal topology:
    h1 -- [s1 (BMv2)] -- h2

Usage:
    sudo python3 data/generator/simple_topo.py
"""

import os
import sys
import time
import subprocess
from mininet.net import Mininet
from mininet.node import Host
from mininet.cli import CLI
from mininet.log import setLogLevel, info, error
from mininet.link import TCLink

# Path to the compiled P4 program
P4_JSON = os.path.join(os.path.dirname(__file__), "../../p4src/basic_forward.json")

class P4Host(Host):
    """Host with ARP disabled (we're doing L2 forwarding)."""
    def config(self, **params):
        super().config(**params)
        # Disable offloading
        for intf in self.intfList():
            self.cmd(f'ethtool -K {intf} tx off rx off')


class BMv2Switch:
    """BMv2 software switch manager."""
    
    def __init__(self, name, grpc_port=50051, thrift_port=9090, device_id=1):
        self.name = name
        self.grpc_port = grpc_port
        self.thrift_port = thrift_port
        self.device_id = device_id
        self.process = None
        self.interfaces = []
        self.log_file = f"/tmp/{name}.log"
        
    def add_interface(self, intf_name, port_num):
        """Add an interface to the switch."""
        self.interfaces.append((intf_name, port_num))
        
    def start(self, p4_json):
        """Start the BMv2 switch."""
        # Build command
        cmd = ["simple_switch_grpc"]
        
        # Add interfaces
        for intf_name, port_num in self.interfaces:
            cmd.extend(["-i", f"{port_num}@{intf_name}"])
        
        # Add device ID and ports
        cmd.extend([
            "--device-id", str(self.device_id),
            "--log-console",
            "--log-level", "warn",
            "--",
            "--grpc-server-addr", f"0.0.0.0:{self.grpc_port}",
            "--cpu-port", "255"
        ])
        
        # Add P4 program
        cmd.append(p4_json)
        
        info(f"*** Starting {self.name}: {' '.join(cmd)}\n")
        
        with open(self.log_file, 'w') as log:
            self.process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT
            )
        
        # Wait for switch to start
        time.sleep(2)
        
        if self.process.poll() is not None:
            error(f"*** {self.name} failed to start! Check {self.log_file}\n")
            return False
            
        info(f"*** {self.name} started (PID: {self.process.pid}, gRPC: {self.grpc_port})\n")
        return True
        
    def stop(self):
        """Stop the BMv2 switch."""
        if self.process:
            self.process.terminate()
            self.process.wait()
            info(f"*** {self.name} stopped\n")


def create_network():
    """Create and start the network."""
    
    # Check for P4 JSON
    p4_json = os.path.abspath(P4_JSON)
    if not os.path.exists(p4_json):
        error(f"P4 JSON not found: {p4_json}\n")
        error("Run: p4c-bm2-ss --p4v 16 -o p4src/basic_forward.json p4src/basic_forward.p4\n")
        return None, None
        
    info(f"*** Using P4 program: {p4_json}\n")
    
    # Create Mininet (no controller, no switch - we manage BMv2 ourselves)
    net = Mininet(host=P4Host, link=TCLink, controller=None, switch=None)
    
    # Add hosts
    info("*** Adding hosts\n")
    h1 = net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
    
    # Create virtual ethernet pairs for the switch
    info("*** Creating veth pairs for switch\n")
    os.system("ip link add s1-eth1 type veth peer name s1-eth1-br")
    os.system("ip link add s1-eth2 type veth peer name s1-eth2-br")
    os.system("ip link set s1-eth1 up")
    os.system("ip link set s1-eth2 up")
    os.system("ip link set s1-eth1-br up")
    os.system("ip link set s1-eth2-br up")
    
    # Link hosts to veth pairs
    info("*** Adding links\n")
    net.addLink(h1, net.addHost('dummy1', inNamespace=False), 
                intfName1='h1-eth0', intfName2='s1-eth1-br')
    net.addLink(h2, net.addHost('dummy2', inNamespace=False),
                intfName1='h2-eth0', intfName2='s1-eth2-br')
    
    # Start network
    info("*** Starting network\n")
    net.start()
    
    # Create and start BMv2 switch
    switch = BMv2Switch('s1', grpc_port=50051)
    switch.add_interface('s1-eth1', 1)
    switch.add_interface('s1-eth2', 2)
    
    if not switch.start(p4_json):
        net.stop()
        return None, None
    
    return net, switch


def install_forwarding_rules(thrift_port=9090):
    """Install basic forwarding rules using simple_switch_CLI."""
    info("*** Installing forwarding rules\n")
    
    # Rules: port 1 -> port 2, port 2 -> port 1
    rules = """
table_add forward_table forward 1 => 2
table_add forward_table forward 2 => 1
"""
    
    cmd = f"echo '{rules}' | simple_switch_CLI --thrift-port {thrift_port}"
    result = os.system(cmd)
    
    if result == 0:
        info("*** Forwarding rules installed\n")
    else:
        error("*** Failed to install rules\n")


def clear_forwarding_rules(thrift_port=9090):
    """Clear all forwarding rules (simulate incident)."""
    info("*** Clearing forwarding rules (simulating incident)\n")
    
    cmd = f"echo 'table_clear forward_table' | simple_switch_CLI --thrift-port {thrift_port}"
    os.system(cmd)


def main():
    setLogLevel('info')
    
    if os.geteuid() != 0:
        print("Error: This script must be run as root (use sudo)")
        sys.exit(1)
    
    net, switch = create_network()
    
    if net is None:
        sys.exit(1)
    
    try:
        info("\n*** Network ready!\n")
        info("*** Hosts: h1 (10.0.0.1), h2 (10.0.0.2)\n")
        info("*** BMv2 gRPC: localhost:50051\n")
        info("\n*** Commands:\n")
        info("    h1 ping h2  - Test connectivity (will fail without rules)\n")
        info("    install     - Install forwarding rules\n")
        info("    clear       - Clear rules (simulate incident)\n")
        info("    exit        - Stop and exit\n\n")
        
        CLI(net)
        
    finally:
        info("*** Stopping network\n")
        switch.stop()
        net.stop()
        
        # Cleanup veth pairs
        os.system("ip link del s1-eth1 2>/dev/null")
        os.system("ip link del s1-eth2 2>/dev/null")


if __name__ == '__main__':
    main()
