import logging
from core.aegis_core import AegisCore

class Orchestrator:
    def __init__(self, core: AegisCore, engines: dict):
        self.core = core
        self.engines = engines
        self.logger = logging.getLogger("Aegis.Orchestrator")

    def start_all(self):
        self.core.aegis_log("Initiating sequence: Starting all engines...", "Orchestrator")
        
        # Priority management example: Start the monitoring class first, then start the simulation class.
        priority_order = ["WiFi", "IDS", "Simulator", "Stresser"]
        
        for name in priority_order:
            if name in self.engines:
                try:
                    self.core.aegis_log(f"Starting engine: {name}", "Orchestrator")
                    self.engines[name].start()
                except Exception as e:
                    self.core.aegis_log(f"Failed to start {name}: {e}", "Orchestrator")

    def stop_all(self):
        self.core.aegis_log("Shutdown sequence initiated.", "Orchestrator")
        for name, engine in self.engines.items():
            try:
                engine.stop()
            except Exception as e:
                self.core.aegis_log(f"Error stopping {name}: {e}", "Orchestrator")

    def start_engine(self, name: str):
        if name in self.engines:
            self.core.aegis_log(f"Starting {name} engine...", "Orchestrator")
            self.engines[name].start()

    def stop_engine(self, name: str):
        if name in self.engines:
            self.core.aegis_log(f"Stopping {name} engine...", "Orchestrator")
            self.engines[name].stop()

    def get_system_health(self):
        """
        Check that all engines are actually running.
        """
        health = {}
        for name, engine in self.engines.items():
            is_alive = False
            if hasattr(engine, 'is_running'):
                is_alive = engine.is_running
            elif hasattr(engine, 'thread'):
                is_alive = engine.thread.is_alive()
            health[name] = "OK" if is_alive else "DOWN"
        return health