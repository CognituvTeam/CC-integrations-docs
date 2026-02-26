"""
Test script to send sample webhook payloads to the Cognituv Connect MCP server.
Run the server first: uvicorn server:app --host 0.0.0.0 --port 8000
Then run this script: python3 test_webhook.py
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

# Sample uplink payload (from CC-integrations-docs)
UPLINK_PAYLOAD = {
    "event_type": "uplink",
    "event_data": {
        "device_id": "1eaedbc0-75f7-11eb-8585-01d3d033571a",
        "user_id": "3aa2aa57-3b3e-4a7f-a8e7-9c4b001dfdc0",
        "payload": [
            {"name": "Battery", "sensor_id": "1f201422-75f7-11eb-8585-01d3d033571a", "type": "batt", "unit": "p", "value": 100, "channel": 5, "timestamp": 1614196169569},
            {"name": "Temperature", "sensor_id": "1f1e1850-75f7-11eb-8585-01d3d033571a", "type": "temp", "unit": "c", "value": 22.11, "channel": 3, "timestamp": 1614196169569},
            {"name": "Humidity", "sensor_id": "1f201420-75f7-11eb-8585-01d3d033571a", "type": "rel_hum", "unit": "p", "value": 32.38, "channel": 4, "timestamp": 1614196169569},
            {"name": "RSSI", "sensor_id": "1f201421-75f7-11eb-8585-01d3d033571a", "type": "rssi", "unit": "dbm", "value": -51, "channel": 100, "timestamp": 1614196169569},
            {"name": "SNR", "sensor_id": "", "type": "snr", "unit": "db", "value": 11.3, "channel": 101, "timestamp": 1614196169569}
        ],
        "gateways": [{"gweui": "000080029c493955", "time": 0, "rssi": -51, "snr": 11.3}],
        "fcnt": 12, "fport": 6,
        "raw_payload": "AQEBHgijDKYAAAA=", "raw_format": "base64",
        "client_id": "ebe4c760-d761-11ea-b2ab-f35fff94ad45",
        "hardware_id": "00137a1000000abc",
        "timestamp": 1614196169569,
        "application_id": "simplysense",
        "device_type_id": "26702500-32a0-11e8-867e-ddad6d07d21e"
    },
    "company": {
        "id": 6109, "address": "3333 Arapahoe Rd", "city": "Erie", "country": "United States",
        "created_at": "2020-08-05T21:23:48Z", "industry": "[\"Food & Beverage\"]",
        "latitude": 40.016926, "longitude": -105.10077, "name": "Trane Southeast - Demo",
        "state": "CO", "status": 0, "timezone": "America/Denver",
        "updated_at": "2020-08-05T21:23:48Z", "user_id": "3aa2aa57-3b3e-4a7f-a8e7-9c4b001dfdc0", "zip": "80516"
    },
    "location": {
        "id": 5454, "address": "3333 Arapahoe Rd", "city": "Erie", "country": "United States",
        "created_at": "2020-08-05T21:23:49Z", "industry": "[\"Food & Beverage\"]",
        "latitude": 40.016926, "longitude": -105.10077, "name": "Building A - Warehouse",
        "state": "CO", "status": 0, "timezone": "America/Denver",
        "updated_at": "2020-08-05T21:23:49Z", "user_id": "3aa2aa57-3b3e-4a7f-a8e7-9c4b001dfdc0",
        "zip": "80516", "company_id": 6109
    },
    "device_type": {
        "id": "26702500-32a0-11e8-867e-ddad6d07d21e", "application_id": "iotinabox",
        "category": "module", "codec": "lorawan.netvox.temp",
        "description": "Netvox Temperature and Humidity Sensor",
        "manufacturer": "Netvox", "model": "R711",
        "name": "Netvox Temperature - IoT in a Box",
        "parent_constraint": "NOT_ALLOWED", "proxy_handler": "PrometheusClient",
        "subcategory": "lora", "transport_protocol": "lorawan"
    },
    "device": {
        "id": 70078980, "thing_name": "Temp/Humidity Sensor - AHU-01",
        "sensor_use": "HVAC Supply Air",
        "created_at": "2021-02-23T16:49:40Z", "updated_at": "2021-02-23T16:49:41Z", "status": 0
    }
}

# Sample alert payload
ALERT_PAYLOAD = {
    "event_type": "alert",
    "event_data": {
        "userId": "3aa2aa57-3b3e-4a7f-a8e7-9c4b001dfdc0",
        "applicationId": "simplysense",
        "clientId": "ebe4c760-d761-11ea-b2ab-f35fff94ad45",
        "thingId": "e3d81db0-75f9-11eb-8585-01d3d033571a",
        "sensorId": "e42be300-75f9-11eb-8585-01d3d033571a",
        "ruleId": "913ca554-cce7-441e-98b8-601d6b3fd348",
        "eventType": "alert-state-changed",
        "totalTriggered": 1,
        "hardwareId": "00137a1000000ghi",
        "triggered": True,
        "value": "1",
        "timestamp": "1614201509775",
        "triggerData": {
            "delay": {"count": 1, "time": 600000},
            "trigger_reading": 0, "trigger_type": "trigger", "trigger_unit": "d",
            "triggers": [{"conditions": [{"operator": "eq", "value": 0}], "trigger_reading": 0, "trigger_unit": "d", "triggers_combination": "OR"}],
            "triggers_combination": "OR"
        },
        "title": "Water Leak Detected - Mechanical Room B"
    },
    "company": {
        "id": 6109, "name": "Trane Southeast - Demo", "city": "Erie", "state": "CO"
    },
    "location": {
        "id": 5454, "name": "Building A - Warehouse", "city": "Erie", "state": "CO", "company_id": 6109
    },
    "device_type": {
        "id": "299fbd30-2733-11e8-bd80-0961dfa396b4", "application_id": "iotinabox",
        "codec": "lorawan.netvox.leak",
        "description": "NETVOX LORAWAN WATER LEAK SENSOR R311W US915/AS923/EU868",
        "manufacturer": "NETVOX", "model": "R311W",
        "name": "Netvox Leak - IoT in a Box"
    },
    "device": {
        "id": 70078985, "thing_name": "Leak Sensor - Mech Room B",
        "sensor_use": "Water Leak Detection",
        "created_at": "2021-02-23T17:09:30Z", "updated_at": "2021-02-23T17:09:30Z", "status": 0
    }
}

# Sample ping payload
PING_PAYLOAD = {
    "event_type": "ping",
    "event_data": {
        "correlation_id": "d9b996bf-162e-43ff-a53b-f83c4725d71f",
        "device_id": "f2a4d140-9f5f-11ec-8d8f-0ffa3ba25edd",
        "user_id": "f48cc16e-f6fd-4d11-8b96-cb6b5b66860b",
        "payload": [{"name": "", "sensor_id": "", "type": "digital", "unit": "ping", "value": 1677561910231, "channel": "ping", "timestamp": 0}],
        "gateways": None, "fcnt": 0, "fport": 0,
        "raw_payload": "", "raw_format": "",
        "client_id": "84ce85e0-6078-11e9-bae2-4ffccf8e095d",
        "hardware_id": "", "timestamp": 1677561910261,
        "application_id": "iotinabox",
        "device_type_id": "7e349b80-26d1-11ec-8a59-8d10a9ed061c"
    },
    "company": {"id": 0, "name": ""},
    "location": {"id": 0, "name": "", "company_id": 0},
    "device_type": {"id": "", "name": "", "manufacturer": "", "model": ""},
    "device": {"id": 769140, "thing_name": "Gateway-Tektelic-01", "status": 0}
}


def test_health():
    print("=== Health Check ===")
    r = requests.get(f"{BASE_URL}/health")
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
    print()


def test_webhook(name, payload):
    print(f"=== Sending {name} ===")
    r = requests.post(f"{BASE_URL}/webhook", json=payload)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
    print()


if __name__ == "__main__":
    test_health()
    test_webhook("Uplink Event", UPLINK_PAYLOAD)
    test_webhook("Alert Event", ALERT_PAYLOAD)
    test_webhook("Ping Event", PING_PAYLOAD)

    # Send a few more uplink events with different timestamps to simulate history
    for i in range(5):
        payload = json.loads(json.dumps(UPLINK_PAYLOAD))
        ts = 1614196169569 + (i + 1) * 300000  # 5 min intervals
        for reading in payload["event_data"]["payload"]:
            reading["timestamp"] = ts
            if reading["type"] == "temp":
                reading["value"] = round(22.11 + i * 0.5, 2)
            elif reading["type"] == "rel_hum":
                reading["value"] = round(32.38 - i * 1.2, 2)
        payload["event_data"]["timestamp"] = ts
        test_webhook(f"Uplink #{i+2}", payload)

    print("=== All test events sent successfully! ===")
