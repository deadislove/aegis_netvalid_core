# 🛡️ Aegis NetValid Core

Aegis NetValid Core is a robust, multi-engine validation framework engineered for IoT ecosystems. It integrates network stress testing, real-time threat detection, and edge-to-cloud verification into a unified orchestration platform, providing an end-to-end quality assurance solution for smart environments.

## 🏗️ System Architecture
Aegis Core utilizes a modular, engine-driven architecture designed for scalability and decoupling:

- Orchestrator: The brain of the system. It manages the lifecycle (launch, termination, health checks) of all sub-engines.
- Data Aggregator: A centralized hub that samples metrics from all engines to provide a unified, time-synced data stream.
- Engines: Independent task units (IDS, Simulator, Stresser, WiFi) invoked via decoupled calls from the Orchestrator.
- Core Infrastructure: Provides non-blocking logging, configuration persistence, and TUI (Terminal User Interface) rendering.

## 📂 Detailed Directory Structure

```
Aegis_NetValid_Core/
├── main_aegis.py           # 🚀 Main entry point (CLI)
├── config/                 # Configurations & Test Scenarios
│   ├── global_config.yaml  # Global parameters (IPs, Cloud API Keys)
│   └── scenarios/          # Test cases (ddos_stress_test.yaml, iot_stability.json)
├── engines/                # Integrated Core Engines
│   ├── ids_guardian/       # Threat detection & defense
│   ├── iot_simulator/      # IoT device behavior simulation
│   ├── traffic_stresser/   # Bandwidth & stress testing
│   └── wifi_monitor/       # RF performance & latency monitoring
├── core/                   # Framework Logic
│   ├── orchestrator.py     # Engine scheduling & state synchronization
│   ├── cloud_validator.py  # Cloud validation (AWS IoT / CloudWatch)
│   └── data_aggregator.py  # Data hub for unified timestamping
├── lib/                    # Shared Utilities (Encryption, OS helpers)
├── outputs/                # Reports & Logs
│   ├── logs/               # Integrated system logs
│   └── reports/            # Auto-generated HTML/PDF analysis reports
└── requirements.txt        # Comprehensive dependency list
```

## 🚀 Key Feature Set

1. Heterogeneous Orchestration

- Lifecycle Management: One-click sequential execution (e.g., Start Simulator → Start IDS → Launch Stresser).
- Sync & Interlock: Ensures critical engines (like IDS) are fully operational before stress tests begin to prevent data loss.
- Non-blocking Execution: Leverages multiprocessing and asyncio for simultaneous engine operation.

2. Edge-to-Cloud Validation

- Latency Tracking: Measures the "Time of Flight" for packets from the physical IoT device to the Cloud.
- Data Integrity: Verifies telemetry consistency under high-load scenarios (up to 95% bandwidth saturation).
- **CloudWatch Integration**: Automatically syncs real-time metrics (Throughput, Threat Count, Active Devices) to AWS CloudWatch for long-term monitoring.
- **Infrastructure Health**: Monitors the "Time of Flight" for telemetry and verifies data integrity under high-load scenarios.

3. Intelligent Analysis & Reporting

- Dynamic Scenario Injection: YAML-driven testing allows users to define complex "if-this-then-that" sequences.
- Automated Pass/Fail: Evaluates results against predefined SLAs (Service Level Agreements).
- Visual Trend Analysis: Correlates performance drops (Latency/RSSI) with network events (Attacks/Stress).

## 🛠️ Installation & Prerequisites

### Requirements

- Python: 3.10+ (Utilizes Structural Pattern Matching).
- Privileges: Must be run with Root/Administrator privileges for Scapy raw packet injection.
- Drivers:
    - Linux: libpcap required.
    - Windows: Npcap (installed in "WinPcap API-compatible Mode").
    - macOS: Native support (requires Terminal Network Access permissions).

### AWS Cloud Configuration
To enable the `CloudValidator` to successfully connect and send data to AWS CloudWatch, ensure your environment is properly configured for AWS authentication and permissions. The `CloudValidator` uses the **AWS SDK for Python (boto3)**, which follows the standard AWS credential chain, meaning you **do not** need to hardcode keys in the source code.

1.  **AWS CLI Setup & Authentication**:
    First, install the AWS Command Line Interface (CLI) and configure your credentials. This is the most common way to set up authentication for local development.
    ```bash
    pip install awscli
    aws configure
    ```
    During `aws configure`, you will be prompted to enter your AWS Access Key ID, Secret Access Key, default region, and default output format. This creates the `~/.aws/credentials` file that `boto3` automatically uses.
    
    Alternatively, `boto3` can also pick up credentials from:
    -   Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).
    -   IAM Instance Profile (if running on an EC2 instance).

2.  **IAM Permissions**:
    The AWS user or role whose credentials are being used **must** have the `cloudwatch:PutMetricData` permission. Attach the following IAM policy to your user or role:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [{
           "Effect": "Allow",
           "Action": "cloudwatch:PutMetricData",
           "Resource": "*"
       }]
   }
   ```
    Ensure that the AWS region configured (either via `aws configure` or in `last_config.json` under `cloud.region`) matches the region where you intend to view your CloudWatch metrics.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/da-weilin/Aegis_NetValid_Core.git
cd Aegis_NetValid_Core

# Install dependencies
pip install -r requirements.txt

# Run the framework
sudo python main_aegis.py
```

## 🖥️ Interactive Dashboard

Upon launch, Aegis presents a real-time TUI powered by rich:

| Command              | Action                                                                 |
|---------------------|------------------------------------------------------------------------|
| help                | Display command menu                                                   |
| set <path> <val>    | Update config dynamically (e.g., set ids.rules.threshold 50)           |
| stress start/stop   | Toggle the Traffic Stresser engine                                     |
| spawn               | Instantly add 5 simulated IoT devices                                  |
| set cloud.enabled true | Enable real-time sync to AWS CloudWatch                             |
| infect <IP>         | Simulate malware behavior on a specific target                         |
| quit                | Graceful shutdown of all engines and export reports                    |

## 📊 Configuration Example

Define automated sequences in `config/scenarios/iot_defense.yaml`:

```yaml
name: "IoT DDoS Defense Validation"
steps:
  - action: "start_engine"
    target: "Simulator"
  - action: "wait"
    duration: 15
  - action: "trigger_infection"
    target: "192.168.0.105"
  - action: "stress_start"
```

## 📩 Contact & Contributions

Developed by [Da-Wei Lin](https://github.com/deadislove). Feel free to reach out for collaboration or to discuss network QA automation!

## ⚖️ License

This project is licensed under the MIT License. See the `LICENSE` file for more details.