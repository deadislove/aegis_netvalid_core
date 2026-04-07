import boto3
import time
from datetime import datetime
from typing import Dict, Any

class CloudValidator:
    def __init__(self, core, config: Dict[str, Any]):
        self.core = core
        self.config = config.get("cloud", {})
        self.enabled = self.config.get("enabled", False)
        self.region = self.config.get("region", "us-east-1")
        self.namespace = self.config.get("namespace", "Aegis/NetValidCore")
        
        self.cw = None
        if self.enabled:
            self._init_aws_client()

    def _init_aws_client(self):
        if self.enabled:
            try:
                # Initialize the CloudWatch client
                self.cw = boto3.client('cloudwatch', region_name=self.region)
                self.core.aegis_log(f"AWS CloudValidator initialized in {self.region}", "Cloud")
            except Exception as e:
                self.core.aegis_log(f"Failed to initialize AWS clients: {e}", "Cloud")
                self.enabled = False

    def refresh_config(self, full_config: Dict[str, Any]):
        """
        Re-apply configuration settings and re-init client if enabled
        """
        self.config = full_config.get("cloud", {})
        was_enabled = self.enabled
        self.enabled = self.config.get("enabled", False)
        self.region = self.config.get("region", "us-east-1")
        
        if self.enabled and (not was_enabled or self.cw is None):
            self._init_aws_client()
        elif not self.enabled:
            self.cw = None

    def sync_to_cloud(self, snapshot: Dict[str, Any]):
        """
        Synchronize Aggregator snapshot data to CloudWatch
        """
        if not self.enabled or not snapshot:
            return

        engine_data = snapshot.get("engines", {})
        metric_data = []
        timestamp = datetime.utcnow()

        # 1. Extract Traffic Stresser metrics
        if "Stresser" in engine_data:
            metric_data.append({
                'MetricName': 'NetworkThroughput',
                'Value': engine_data["Stresser"].get("current_mbps", 0),
                'Unit': 'Megabits/Second',
                'Timestamp': timestamp
            })

        # 2. Extract IDS threat indicators
        if "IDS" in engine_data:
            metric_data.append({
                'MetricName': 'ThreatCount',
                'Value': engine_data["IDS"].get("threats", 0),
                'Unit': 'Count',
                'Timestamp': timestamp
            })

        # 3. Extract Simulator Device Specifications
        if "Simulator" in engine_data:
            metric_data.append({
                'MetricName': 'ActiveDevices',
                'Value': engine_data["Simulator"].get("active_devices", 0),
                'Unit': 'Count',
                'Timestamp': timestamp
            })

        if metric_data:
            try:
                self.cw.put_metric_data(Namespace=self.namespace, MetricData=metric_data)
                # self.core.aegis_log("Metrics successfully synced to CloudWatch", "Cloud")
            except Exception as e:
                self.core.aegis_log(f"CloudWatch sync error: {e}", "Cloud")