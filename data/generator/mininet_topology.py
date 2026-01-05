#!/usr/bin/env python3
"""
Mininet Topology for Network Agent Training
-------------------------------------------
Supports Dual-Mode:
1. **P4 Mode**: Uses 'simple_switch_grpc' (BMv2) if installed.
2. **Simulation Mode**: Uses OVS and a background script to fake P4 registers.

Usage:
    sudo python3 data/generator/mininet_topology.py
"""

import os
import sys
import time
import json
import shutil
from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch, Host, Switch
from mininet.cli import CLI
from mininet.log import setLogLevel, info, error
from mininet.link import TCLink

# Check if BMv2 is available
BMV2_PATH = shutil.which('simple_switch_grpc')
HAS_BMV2 = BMV2_PATH is not None

class P4Switch(Switch):
    """P4-programmable switch using BMv2."""
    def __init__(self, name, sw_path = None, json_path = None, grpc_port = 50051, **kwargs):
        Switch.__init__(self, name, **kwargs)
        self.sw_path = sw_path if sw_path else 'simple_switch_grpc'
        self.json_path = json_path
        self.grpc_port = grpc_port
        self.verbose = True
        self.logfile = '/tmp/p4s.{}.log'.format(self.name)
        self.output = open(self.logfile, 'w')

    @classmethod
    def setup(cls):
        pass

    def start(self, controllers):
        "Start BMv2 switch"
        info("Starting P4 Switch %s\n" % self.name)
        args = [self.sw_path]
        for intf in self.intfs.values():
            if not intf.IP():
                args.extend(['-i', str(intf.name)])
        args.extend(['--device-id', str(self.dpid)])
        args.extend(['--thrift-port', str(9090 + int(self.dpid))]) # Mock Thrift
        args.extend(['--log-console'])
        if self.json_path:
            args.extend(['--p4runtime-files', self.json_path])
        
        # simple_switch_grpc arguments
        args.extend(['--'])
        args.extend(['--grpc-server-addr', '0.0.0.0:{}'.format(self.grpc_port)])
        
        info(' '.join(args) + "\n")

        self.cmd(' '.join(args) + ' >' + self.logfile + ' 2>&1 &')

    def stop(self):
        "Stop BMv2"
        self.cmd('kill %' + self.sw_path)
        self.cmd('wait')
        super(P4Switch, self).stop()

class LinuxRouter(Host):
    """A Node with IP forwarding enabled."""
    def config(self, **params):
        super(LinuxRouter, self).config(**params)
        self.cmd('sysctl -w net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl -w net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()

def create_topology():
    
    if HAS_BMV2:
        info(f"*** BMv2 found at {BMV2_PATH}. Running in P4 MODE.\n")
        # In a real setup, we need a compiled p4info.txt and bmv2.json
        # Check for dummy p4 file or warn
        p4_json = "p4src/build/switch.json" # Hypothetical path
        if not os.path.exists(p4_json):
             error("WARNING: P4 compiled JSON not found at {}. P4 Switch will start without program.\n".format(p4_json))
             p4_json = None
             
        SwitchClass = P4Switch
        switch_args = {'sw_path': BMV2_PATH, 'json_path': p4_json}
    else:
        info("*** BMv2 NOT found. Running in SIMULATION MODE (OVS).\n")
        SwitchClass = OVSKernelSwitch
        switch_args = {}

    net = Mininet(controller=Controller, link=TCLink, switch=SwitchClass)

    info( '*** Adding controller\\n' )
    net.addController('c0')

    info( '*** Adding routers/switches\\n' )
    
    # In this hybrid topology, we treat the Routers as Hosts (generating traffic)
    # And we add a Core P4 Switch in the middle to measure the telemetry?
    # Or, following the previous design, the Routers ARE the switches.
    # For P4, usually the switch is the forwarding plane.
    # Let's keep the existing Router model but if P4 is enabled, R1 acts as a P4 switch + Host agent.
    # For simplicity in this script:
    # If P4 mode: R1 is a P4Switch (doing L3 forwarding via P4 program).
    # If Sim mode: R1 is a LinuxRouter.
    
    if HAS_BMV2:
        # P4 Mode: R1 is the DUT (Device Under Test)
        r1 = net.addSwitch('r1', cls=P4Switch, grpc_port=50051, **switch_args)
        # R2/R3 are standard hosts/routers to generate traffic
        r2 = net.addHost('r2', cls=LinuxRouter, ip='10.0.2.1/24')
        r3 = net.addHost('r3', cls=LinuxRouter, ip='10.0.3.1/24')
    else:
        # Simulation Mode: All Linux Routers
        r1 = net.addHost('r1', cls=LinuxRouter, ip='10.0.1.1/24')
        r2 = net.addHost('r2', cls=LinuxRouter, ip='10.0.2.1/24')
        r3 = net.addHost('r3', cls=LinuxRouter, ip='10.0.3.1/24')

    info( '*** Creating links\\n' )
    # R1-R2
    net.addLink(r1, r2, intfName1='r1-eth1', intfName2='r2-eth1', 
                params1={'ip':'10.0.12.1/24'}, params2={'ip':'10.0.12.2/24'},
                bw=10, delay='5ms', loss=0)
    
    # R1-R3
    net.addLink(r1, r3, intfName1='r1-eth2', intfName2='r3-eth1',
                params1={'ip':'10.0.13.1/24'}, params2={'ip':'10.0.13.3/24'},
                bw=10, delay='5ms', loss=0)
    
    # R2-R3 (Completing triangle)
    net.addLink(r2, r3, intfName1='r2-eth2', intfName2='r3-eth2',
                params1={'ip':'10.0.23.2/24'}, params2={'ip':'10.0.23.3/24'},
                bw=10, delay='5ms', loss=0)

    info( '*** Starting network\\n' )
    net.start()

    if not HAS_BMV2:
        info( '*** SIMULATION MODE: Configuring Static Routes\\n' )
        r1.cmd("ip route add 10.0.23.0/24 via 10.0.12.2")
        r2.cmd("ip route add 10.0.13.0/24 via 10.0.12.1")
        r3.cmd("ip route add 10.0.12.0/24 via 10.0.13.1")
        
        info( '*** Simulating "P4 Register" Telemetry on R1\\n' )
        p4_sim_script = """
import time
import random
import json

drop_counter = 0
while True:
    if int(time.time()) % 10 == 0:
        drop_counter += random.randint(50, 200)
    
    data = {"device": "r1", "register": "egress_drop_counter", "value": drop_counter}
    with open('/tmp/r1_p4_register.json', 'w') as f:
        json.dump(data, f)
    time.sleep(1)
"""
        with open('p4_sim_backend.py', 'w') as f:
            f.write(p4_sim_script)
        r1.cmd('python3 p4_sim_backend.py &')

    else:
        info( '*** P4 MODE: Switch R1 started on gRPC 50051.\\n' )
        info( '*** NOTE: You must push a P4 program using the Controller or Agent to enable forwarding.\\n')

    info( '*** Running CLI (type "exit" to stop)\\n' )
    CLI( net )

    info( '*** Stopping network\\n' )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    if os.geteuid() != 0:
        print("Error: Mininet must be run as root.")
        exit(1)
    create_topology()

