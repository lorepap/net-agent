import random
import time
import json
import argparse
from datetime import datetime, timedelta

# Constants
DEVICES = [
    "cs-core-01", "cs-core-02", 
    "cs-dist-01", "cs-dist-02", 
    "cs-access-01", "cs-access-02", "cs-access-03"
]

INTERFACES = [
    "TenGigabitEthernet1/0/1", "TenGigabitEthernet1/0/2",
    "GigabitEthernet0/0/1", "GigabitEthernet0/0/2"
]

SYSLOG_LEVELS = ["INFO", "WARNING", "ERROR", "CRITICAL"]

# Scenarios
SCENARIOS = {
    "normal": {
        "latency_min": 1, "latency_max": 20,
        "packet_loss_prob": 0.001,
        "error_prob": 0.01
    },
    "latency_spike": {
        "latency_min": 150, "latency_max": 800,
        "packet_loss_prob": 0.05,
        "error_prob": 0.1
    },
    "packet_drop": {
        "latency_min": 20, "latency_max": 50,
        "packet_loss_prob": 0.3,
        "error_prob": 0.3,
        "specific_error": "BGP_NEIGHBOR_DOWN"
    },
    "interface_down": {
        "latency_min": 0, "latency_max": 0,
        "packet_loss_prob": 1.0,
        "error_prob": 1.0,
        "specific_error": "LINK_DOWN"
    }
}

def generate_syslog(timestamp, device, scenario_type):
    """Generates a single syslog message."""
    scenario = SCENARIOS[scenario_type]
    
    if "specific_error" in scenario and random.random() < scenario["error_prob"]:
        error_code = scenario["specific_error"]
        level = "CRITICAL"
        if error_code == "BGP_NEIGHBOR_DOWN":
            msg = f"%BGP-5-ADJCHANGE: neighbor 10.0.0.2 Down BGP Notification sent"
        elif error_code == "LINK_DOWN":
            interface = random.choice(INTERFACES)
            msg = f"%LINK-3-UPDOWN: Interface {interface}, changed state to down"
        else:
             msg = "Unknown Error"
    elif random.random() < scenario["error_prob"]:
        level = random.choice(["WARNING", "ERROR"])
        interface = random.choice(INTERFACES)
        msg = f"%INTF-4-EXCESSIVE_ERRORS: Excessive errors on {interface}"
    else:
        level = "INFO"
        msg = "Configured from console by console"

    log = f"<{random.randint(1, 190)}> {timestamp} {device} {level}: {msg}"
    return log

def generate_netflow(timestamp, device, scenario_type):
    """Generates a single netflow record."""
    scenario = SCENARIOS[scenario_type]
    
    src_ip = f"192.168.{random.randint(1,255)}.{random.randint(1,255)}"
    dst_ip = f"10.0.{random.randint(1,255)}.{random.randint(1,255)}"
    src_port = random.randint(1024, 65535)
    dst_port = random.choice([80, 443, 22, 53, 8080])
    proto = random.choice([6, 17]) # TCP, UDP
    
    # Latency simulation
    latency = random.randint(scenario["latency_min"], scenario["latency_max"])
    
    # Packet loss simulation
    packets_sent = random.randint(100, 10000)
    if random.random() < scenario["packet_loss_prob"]:
         packets_lost = int(packets_sent * random.uniform(0.1, 0.5))
    else:
         packets_lost = 0
    
    bytes_transferred = packets_sent * random.randint(64, 1500)
    
    record = {
        "timestamp": timestamp,
        "device": device,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": src_port,
        "dst_port": dst_port,
        "protocol": proto,
        "packets_sent": packets_sent,
        "packets_lost": packets_lost,
        "bytes": bytes_transferred,
        "rtt_ms": latency
    }
    return record

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic network logs")
    parser.add_argument("--count", type=int, default=100, help="Number of logs to generate")
    parser.add_argument("--scenario", type=str, default="normal", choices=SCENARIOS.keys(), help="Network scenario")
    parser.add_argument("--output-syslog", type=str, default="syslog.log", help="Output file for syslogs")
    parser.add_argument("--output-netflow", type=str, default="netflow.json", help="Output file for netflow")
    
    args = parser.parse_args()
    
    syslogs = []
    netflows = []
    
    base_time = datetime.now()
    
    for i in range(args.count):
        timestamp = (base_time - timedelta(seconds=args.count - i)).strftime("%b %d %H:%M:%S")
        iso_timestamp = (base_time - timedelta(seconds=args.count - i)).isoformat()
        device = random.choice(DEVICES)
        
        syslogs.append(generate_syslog(timestamp, device, args.scenario))
        netflows.append(generate_netflow(iso_timestamp, device, args.scenario))
        
    with open(args.output_syslog, "w") as f:
        for log in syslogs:
            f.write(log + "\n")
            
    with open(args.output_netflow, "w") as f:
        json.dump(netflows, f, indent=2)

    print(f"Generated {args.count} logs for scenario '{args.scenario}'")
    print(f"Syslogs saved to {args.output_syslog}")
    print(f"Netflows saved to {args.output_netflow}")

if __name__ == "__main__":
    main()
