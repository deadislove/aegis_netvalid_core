# ☁️ Cloud Validation & AWS Integration

Aegis NetValid Core supports real-time synchronization of edge metrics to the cloud. This allows for long-term trend analysis, alerting, and cross-site comparison.

## 1. CloudWatch Metrics Mapping

The `CloudValidator` automatically translates internal engine data into AWS CloudWatch Metrics. By default, these are sent to the `Aegis/NetValid` namespace.

| Aegis Metric | CloudWatch Metric Name | Unit | Source Engine |
|--------------|------------------------|------|---------------|
| Mbps         | `NetworkThroughput`    | Megabits/Second | Traffic Stresser |
| Threat Count | `ThreatCount`          | Count | IDS Guardian |
| Active Devs  | `ActiveDevices`        | Count | IoT Simulator |

## 2. Configuration Parameters

Settings are managed via `last_config.json` under the `cloud` key:

- `enabled`: (bool) Toggle cloud synchronization.
- `region`: (string) AWS Region (e.g., `us-east-1`).
- `sync_interval`: (int) Frequency of updates in seconds (default: 60).
- `namespace`: (string) The custom namespace for CloudWatch.

## 3. Security & IAM

Aegis uses the standard AWS SDK (`boto3`) credential provider chain. We recommend using a dedicated IAM user with the following **Least Privilege** policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "cloudwatch:PutMetricData",
            "Resource": "*"
        }
    ]
}
```

## 4. Extending to AWS IoT Core

If you wish to update a **Device Shadow** instead of just sending metrics, you can modify `core/cloud_validator.py` to include the `iot-data` client:

1. Initialize the client: `self.iot = boto3.client('iot-data')`.
2. Use `update_thing_shadow()` to push state updates.

## 5. Troubleshooting

- **No Data in Console**: Ensure the `region` in your config matches your AWS CLI settings.
- **Permission Error**: Check the `Aegis_System.log` to see if `PutMetricData` was denied (403).
- **Sync Lag**: If the `sync_interval` is too short, you may encounter AWS API rate limiting.