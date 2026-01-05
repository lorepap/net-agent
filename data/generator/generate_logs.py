import random
import time
import json
import argparse
from datetime import datetime, timedelta

# Constants
# Constants
DEVICES = ["s1"]

INTERFACES = ["port 1", "port 2"]

SYSLOG_LEVELS = ["INFO"]

# Scenarios
SCENARIOS = {
    "normal": {
        "latency_min": 1, "latency_max": 5,
        "packet_loss_prob": 0.0,
        "error_prob": 0.05
    },
    "missing_rules": {
        "latency_min": 0, "latency_max": 0, # Traffic blocked
        "packet_loss_prob": 1.0, # All packets dropped
        "error_prob": 1.0,
        "specific_error": "MISSING_RULES"
    }
}

def generate_syslog(timestamp, device, scenario_type):
    """Generates a single P4 Runtime log message."""
    scenario = SCENARIOS[scenario_type]
    
    if "specific_error" in scenario and scenario["specific_error"] == "MISSING_RULES":
        if random.random() < 0.8:
            msg = "RuntimeCmd: packet_counter[0]= 0"
        else:
            msg = "Control utility for runtime P4 table manipulation"
    else:
        # Normal traffic
        if random.random() < 0.8:
             count = random.randint(50, 5000)
             msg = f"RuntimeCmd: packet_counter[0]= {count}"
        else:
             msg = "Control utility for runtime P4 table manipulation"

    log = f"{msg}"
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
