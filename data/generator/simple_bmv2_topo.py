#!/usr/bin/env python3
"""
Simple BMv2 Mininet Topology - Minimal Version
-----------------------------------------------
Creates a minimal topology using BMv2 as the switch:
    h1 (10.0.0.1) -- [s1 (BMv2)] -- h2 (10.0.0.2)

Usage:
    sudo python3 data/generator/simple_bmv2_topo.py
"""

import os
import sys
import time
import argparse
import subprocess
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info, error
from mininet.node import Switch, Host

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
P4_JSON = os.path.join(PROJECT_ROOT, "p4src", "basic_forward.json")


class BMv2SimpleSwitch(Switch):
    """A BMv2 software switch for Mininet."""
    
    device_id = 0
    
    def __init__(self, name, sw_path='simple_switch_grpc',
                 json_path=None, grpc_port=50051, thrift_port=9090,
                 log_console=False, verbose=False, **kwargs):
        Switch.__init__(self, name, **kwargs)
        
        # Increment device ID for each switch
        BMv2SimpleSwitch.device_id += 1
        self.sw_id = BMv2SimpleSwitch.device_id
        
        self.sw_path = sw_path
        self.json_path = json_path
        self.grpc_port = grpc_port
        self.thrift_port = thrift_port
        self.log_console = log_console
        self.verbose = verbose
        self.log_file = f"/tmp/bmv2_{name}.log"
        
    @classmethod
    def setup(cls):
        pass

    def start(self, controllers):
        """Start the BMv2 switch."""
        info(f"*** Starting BMv2 switch {self.name}\n")
        
        # Build interface arguments
        args = [self.sw_path]
        
        for port_num, intf in enumerate(self.intfList(), start=1):
            if intf.name != 'lo':
                args.extend(['-i', f'{port_num}@{intf.name}'])
        
        # Add thrift and grpc ports
        args.extend([
            '--thrift-port', str(self.thrift_port),
            '--device-id', str(self.sw_id),
            '--log-file', self.log_file,
        ])
        
        if self.log_console:
            args.append('--log-console')
        
        # gRPC arguments come after --
        args.extend([
            '--',
            '--grpc-server-addr', f'0.0.0.0:{self.grpc_port}',
        ])
        
        # Add P4 JSON path
        if self.json_path and os.path.exists(self.json_path):
            args.append(self.json_path)
        else:
            error(f"*** P4 JSON not found: {self.json_path}\n")
            return
        
        if self.verbose:
            info(f"*** Command: {' '.join(args)}\n")
        
        # Start the switch in the background
        self.cmd(' '.join(args) + ' &')
        
        # Wait for it to start
        time.sleep(2)
        
        info(f"*** {self.name} started (thrift: {self.thrift_port}, grpc: {self.grpc_port})\n")

    def stop(self, deleteIntfs=True):
        """Stop the BMv2 switch."""
        info(f"*** Stopping {self.name}\n")
        self.cmd('kill %simple_switch_grpc 2>/dev/null')
        super().stop(deleteIntfs)


def install_rules(thrift_port=9090):
    """Install forwarding rules to enable connectivity."""
    info("*** Installing forwarding rules\n")
    
    # Port 1 -> Port 2, Port 2 -> Port 1
    commands = [
        f"table_add forward_table forward 1 => 2",
        f"table_add forward_table forward 2 => 1",
    ]
    
    for cmd in commands:
        full_cmd = f"echo '{cmd}' | simple_switch_CLI --thrift-port {thrift_port}"
        os.system(full_cmd)
    
    info("*** Rules installed\n")


def clear_rules(thrift_port=9090):
    """Clear forwarding rules to simulate an incident."""
    info("*** Clearing forwarding rules (simulating incident)\n")
    os.system(f"echo 'table_clear forward_table' | simple_switch_CLI --thrift-port {thrift_port}")


def read_counters(thrift_port=9090):
    """Read packet and drop counters."""
    info("*** Reading counters\n")
    commands = [
        "register_read packet_counter 0",
        "register_read packet_counter 1", 
        "register_read packet_counter 2",
        "register_read drop_counter 0",
    ]
    for cmd in commands:
        os.system(f"echo '{cmd}' | simple_switch_CLI --thrift-port {thrift_port}")


def main():
    parser = argparse.ArgumentParser(description='Simple BMv2 Mininet Topology')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    setLogLevel('info')
    
    if os.geteuid() != 0:
        print("Error: This script must be run as root (sudo)")
        sys.exit(1)
    
    # Check for P4 JSON
    if not os.path.exists(P4_JSON):
        error(f"P4 JSON not found: {P4_JSON}\n")
        error("Compile with: p4c-bm2-ss --p4v 16 -o p4src/basic_forward.json p4src/basic_forward.p4\n")
        sys.exit(1)
    
    info(f"*** Using P4 program: {P4_JSON}\n")
    
    # Create network
    net = Mininet(
        switch=BMv2SimpleSwitch,
        controller=None,
        autoSetMacs=True,
    )
    
    # Add switch
    s1 = net.addSwitch('s1', 
                       json_path=P4_JSON,
                       thrift_port=9090,
                       grpc_port=50051,
                       verbose=args.verbose)
    
    # Add hosts
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')
    
    # Add links
    net.addLink(h1, s1)
    net.addLink(h2, s1)
    
    # Start network
    info("*** Starting network\n")
    net.start()
    
    # Wait for switch to be ready
    time.sleep(2)
    
    info("\n" + "="*60 + "\n")
    info("SIMPLE BMV2 DEMO TOPOLOGY\n")
    info("="*60 + "\n")
    info("Hosts:\n")
    info("  h1: 10.0.0.1 (MAC: 00:00:00:00:00:01)\n")
    info("  h2: 10.0.0.2 (MAC: 00:00:00:00:00:02)\n")
    info("\nSwitch:\n")
    info("  s1: BMv2 (Thrift: 9090, gRPC: 50051)\n")
    info("\nDemo Commands:\n")
    info("  h1 ping -c 3 h2     Test connectivity (fails without rules)\n")
    info("  py install_rules()  Install forwarding rules\n")
    info("  py clear_rules()    Clear rules (simulate incident)\n")
    info("  py read_counters()  Read packet counters\n")
    info("="*60 + "\n\n")
    
    # Make functions available in CLI
    CLI.do_install = lambda self, line: install_rules()
    CLI.do_clear = lambda self, line: clear_rules()
    CLI.do_counters = lambda self, line: read_counters()
    
    try:
        CLI(net)
    finally:
        info("*** Stopping network\n")
        net.stop()


if __name__ == '__main__':
    main()
