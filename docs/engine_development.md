# 🔌 Engine Development Guide

Aegis NetValid Core is built on a "Plug-and-Play" philosophy. This guide explains how to develop a new engine (e.g., a **Bluetooth Low Energy (BLE) Validator**) and integrate it into the Aegis orchestration framework.

## 📋 The Engine Lifecycle
All engines in Aegis are managed by the `Orchestrator` as independent processes. An engine must adhere to a specific lifecycle:
1. **Initialization**: Loading configurations and pre-flight checks.
2. **Execution**: Running the main task loop (non-blocking).
3. **Reporting**: Periodically pushing metrics to the `Data Aggregator`.
4. **Termination**: Graceful shutdown and resource cleanup.

---

## 🛠️ Step 1: Define the Engine Class
Every engine should inherit from a base structure (or follow the interface) that the Orchestrator expects. Create a new directory in `engines/your_engine_name/`.

### Interface Specification
Your engine should implement the following methods:

```python
class BaseEngine:
    def __init__(self, config: dict, data_queue: multiprocessing.Queue):
        self.config = config
        self.data_queue = data_queue # Used to send data to Aggregator
        self.is_running = False

    def start(self):
        """Entry point called by the Orchestrator process."""
        pass

    def stop(self):
        """Logic to stop loops and release hardware (e.g., radio sockets)."""
        pass

    def get_status(self) -> dict:
        """Returns health and performance metrics."""
        return {"status": "healthy", "metrics": {}}
```

---

## 🧪 Step 2: Implementation Example (BLE Engine)
Imagine we are adding a `BluetoothEngine` to validate IoT mesh connectivity.

```python
# engines/bluetooth_engine/ble_validator.py
import time

class BluetoothEngine(BaseEngine):
    def start(self):
        self.is_running = True
        print("Bluetooth Engine: Scanning for BLE advertisements...")
        
        while self.is_running:
            # 1. Perform validation task
            rssi_value = self._scan_device("Smart_Lock_01")
            
            # 2. Package and push data to Aggregator
            self.data_queue.put({
                "engine": "Bluetooth",
                "timestamp": time.time(),
                "type": "metric",
                "data": {"device": "Smart_Lock_01", "rssi": rssi_value}
            })
            time.sleep(1)

    def stop(self):
        self.is_running = False
```

---

## 🔗 Step 3: Registration
To make the Orchestrator aware of your new engine, update the configuration and the entry point:

1.  **Update `global_config.yaml`**:
    ```yaml
    engines:
      bluetooth:
        enabled: true
        scan_interval: 1.0
        target_uuid: "0xFEAA"
    ```

2.  **Register in `main_aegis.py`**:
    ```python
    # Add your engine to the startup sequence
    from engines.bluetooth_engine.ble_validator import BluetoothEngine
    
    orchestrator.register_engine("Bluetooth", BluetoothEngine)
    ```

## 🛡️ Best Practices
- **Error Handling**: Use `try-except` blocks within the `start()` method to prevent a single engine crash from leaving zombie processes.
- **Data Schema**: Ensure your data dictionary includes a `timestamp` and `engine` name for the Aggregator to perform correct time-series correlation.
- **Resource Management**: Always release hardware resources (like Scapy sockets or Bluetooth adapters) in the `stop()` method.

By following this pattern, Aegis can scale to support any protocol—from Zigbee to 5G slice validation.