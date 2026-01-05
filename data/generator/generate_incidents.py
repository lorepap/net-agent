import os
import sys
import json
import subprocess
import argparse
from pathlib import Path

# Ground Truth Database
INCIDENT_TYPES = {
    "latency_spike": {
        "description": "High latency detected on core uplinks.",
        "root_cause": "Congestion on primary link due to backup",
        "recommended_fix": "Reroute traffic via secondary path using PBR or adjust OSPF cost.",
        "commands": ["router ospf 1", "interface TenGigabitEthernet1/0/1", "ip ospf cost 1000"]
    },
    "packet_drop": {
        "description": "Significant packet loss observed.",
        "root_cause": "BGP Neighbor instability causing route flapping",
        "recommended_fix": "Verify BGP config and check physical layer.",
        "commands": ["show ip bgp summary", "clear ip bgp * soft"]
    },
    "interface_down": {
        "description": "Interface reported as down.",
        "root_cause": "Physical link failure or administrative shutdown",
        "recommended_fix": "Check cable or issue no shutdown.",
        "commands": ["interface GigabitEthernet0/0/1", "no shutdown"]
    },
    "normal": {
        "description": "Network operating normally.",
        "root_cause": "None",
        "recommended_fix": "None",
        "commands": []
    }
}

def generate_incident(output_dir, scenario, incident_id):
    """Generates a single incident folder with logs and a metadata file."""
    incident_dir = Path(output_dir) / f"incident_{incident_id}_{scenario}"
    incident_dir.mkdir(parents=True, exist_ok=True)
    
    syslog_path = incident_dir / "syslog.log"
    netflow_path = incident_dir / "netflow.json"
    
    # Run the log generator
    cmd = [
        sys.executable, "data/generator/generate_logs.py",
        "--count", "200",
        "--scenario", scenario,
        "--output-syslog", str(syslog_path),
        "--output-netflow", str(netflow_path)
    ]
    subprocess.run(cmd, check=True)
    
    # Create the ground truth report
    gt = INCIDENT_TYPES.get(scenario, INCIDENT_TYPES["normal"])
    report = {
        "incident_id": f"INC-{incident_id}",
        "scenario": scenario,
        "logs": {
            "syslog": str(syslog_path),
            "netflow": str(netflow_path)
        },
        "ground_truth": gt
    }
    
    with open(incident_dir / "report.json", "w") as f:
        json.dump(report, f, indent=2)
        
    return report

def main():
    parser = argparse.ArgumentParser(description="Generate incident datasets")
    parser.add_argument("--output-dir", type=str, default="data/custom_dataset", help="Output directory")
    parser.add_argument("--count", type=int, default=5, help="Number of incidents per scenario")
    
    args = parser.parse_args()
    
    summary = []
    
    incident_counter = 1
    for scenario in INCIDENT_TYPES.keys():
        print(f"Generating incidents for scenario: {scenario}")
        for _ in range(args.count):
            report = generate_incident(args.output_dir, scenario, incident_counter)
            summary.append(report)
            incident_counter += 1
            
    # Save a summary index
    with open(Path(args.output_dir) / "dataset_index.json", "w") as f:
        json.dump(summary, f, indent=2)
        
    print(f"Generated {len(summary)} incidents in {args.output_dir}")

if __name__ == "__main__":
    main()
