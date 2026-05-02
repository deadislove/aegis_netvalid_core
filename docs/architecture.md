# 🏗️ Aegis NetValid Core Architecture

## Overview
Aegis NetValid Core is designed with a **Modular, Engine-Driven Architecture**. The primary design philosophy is to decouple the control logic (Orchestrator) from the execution logic (Engines) and the data processing logic (Aggregator), ensuring high scalability and fault isolation.

## High-Level System Design
The following diagram illustrates the relationship between the core components and the external environment.

```mermaid
graph TD
    User([User/TUI Interface]) --> Orchestrator
    
    subgraph Core_Framework [Core Framework]
        Orchestrator[Orchestrator]
        Config[Config Manager]
        Aggregator[Data Aggregator]
        Logger[Async Logger]
    end

    Orchestrator --> Config
    Orchestrator --> Engines
    
    subgraph Engines [Integrated Engines]
        IDS[IDS Guardian]
        Sim[IoT Simulator]
        Stress[Traffic Stresser]
        WiFi[WiFi Monitor]
        SoC[SoC Guardian]
        NetSvc[Net Service Engine]
    end

    Engines -.->|Metrics/Events| Aggregator
    Aggregator -->|Processed Data| Cloud[Cloud Validator]
    Aggregator -->|Real-time Stats| User
    Aggregator -->|Persistence| Reports[Report Generator]
```

---

## Component Breakdown

### 1. Orchestrator (The Brain)
The Orchestrator manages the entire system lifecycle using a **Non-blocking Process Management** model.
- **Process Isolation**: Each engine is spawned as an independent OS process using Python's `multiprocessing` to bypass the Global Interpreter Lock (GIL).
- **Interlock Logic**: Ensures dependencies are met (e.g., the `IDS` must be healthy and capturing before the `Traffic Stresser` begins).
- **State Synchronization**: Uses shared memory or Inter-Process Communication (IPC) to monitor engine health in real-time.

### 2. Data Aggregator (The Hub)
Acting as the central nervous system, the Aggregator handles high-throughput data streams.
- **Unified Timestamping**: Normalizes events from different engines onto a single timeline to enable accurate correlation analysis (e.g., matching a latency spike with a specific DDoS attack).
- **Async Buffering**: Uses `asyncio.Queue` to ingest data from engines without introducing backpressure to the testing logic.

### 3. Engine Layer
Engines are autonomous units designed to perform specific validation tasks. They follow a standardized interface (`start`, `stop`, `get_status`), making the framework easily extensible.

---

## Data Flow & Interaction
The sequence below demonstrates a typical **Automated Validation Scenario**: Launching a Simulator and then triggering a Stress Test while monitoring performance.

```mermaid
sequenceDiagram
    autonumber
    participant U as User (TUI)
    participant O as Orchestrator
    participant S as IoT Simulator
    participant T as Traffic Stresser
    participant A as Data Aggregator
    participant C as Cloud Validator

    U->>O: Command: Run Scenario
    O->>S: Spawn Process
    S-->>A: Register Device IPs
    Note over S,A: Simulator heartbeat established
    
    O->>T: Start Stress Test (Targeting Simulator)
    T->>S: High-Bandwidth UDP Traffic
    
    T-->>A: Push Network Metrics (Packet Loss)
    S-->>A: Push Application Metrics (Latency)
    
    A->>A: Correlate Stress vs. Latency
    A->>C: Sync to Cloud (AWS/CloudWatch)
    A->>U: Update Real-time Dashboard
```

## Reliability & Resilience
- **Fault Isolation**: A crash in a specific engine (e.g., Scapy buffer overflow in the Stresser) will not terminate the Orchestrator or other monitoring engines.
- **Graceful Teardown**: Upon exit, the Orchestrator ensures all child processes are terminated and the Data Aggregator flushes all remaining buffers to the `outputs/` directory to prevent data loss.