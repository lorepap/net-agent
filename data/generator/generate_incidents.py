import os
import sys
import json
import subprocess
import argparse
from pathlib import Path

# Ground Truth Database
INCIDENT_TYPES = {
    "missing_rules": {
        "description": "H1 cannot ping H2 (Packet Loss).",
        "root_cause": "Missing forwarding rules (packet_counter[0] == 0).",
        "recommended_fix": "Install forwarding rules.",
        "commands": [
            "table_add forward_table forward 1 => 2",
            "table_add forward_table forward 2 => 1"
        ]
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
