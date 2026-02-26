# Cognituv Connect MCP Tools

This document provides a detailed reference for all the tools exposed by the Cognituv Connect MCP server. These tools enable AI agents to interact with your IoT data in a structured and powerful way.

## Tool Reference

### 1. `list_devices`

Lists all unique devices that have sent data to the server. This is a great starting point for exploring your connected hardware.

**Parameters:**

- `company_name` (string, optional): Filter devices by the company name (supports partial matches).
- `location_name` (string, optional): Filter devices by the location name (supports partial matches).

**Returns:** A formatted string listing the devices, their type, location, and last seen timestamp.

**Example Usage:**

> `list_devices(company_name="Trane")`

### 2. `get_device_details`

Retrieves all stored metadata for a single device, identified by its unique ID.

**Parameters:**

- `device_id` (string, required): The unique identifier of the device.

**Returns:** A detailed breakdown of the device's properties, including its name, type, manufacturer, model, and location information.

**Example Usage:**

> `get_device_details(device_id="1eaedbc0-75f7-11eb-8585-01d3d033571a")`

### 3. `get_latest_readings`

Fetches the most recent sensor reading for each distinct sensor channel on a given device. This provides a snapshot of the device's current state.

**Parameters:**

- `device_id` (string, required): The unique identifier of the device.

**Returns:** A list of the latest readings, including the sensor name, value, unit, and timestamp.

**Example Usage:**

> `get_latest_readings(device_id="1eaedbc0-75f7-11eb-8585-01d3d033571a")`

### 4. `get_reading_history`

Provides a time-series history of sensor readings for a device. This is useful for trend analysis and historical investigation.

**Parameters:**

- `device_id` (string, required): The unique identifier of the device.
- `sensor_type` (string, optional): Filter the history to a specific sensor type (e.g., `temp`, `rel_hum`, `co2`).
- `limit` (integer, optional, default: 50): The maximum number of historical readings to return.

**Returns:** A list of historical sensor readings, ordered from newest to oldest.

**Example Usage:**

> `get_reading_history(device_id="1eaedbc0-75f7-11eb-8585-01d3d033571a", sensor_type="temp", limit=10)`

### 5. `get_alerts`

Queries the database for alert events. By default, it returns only currently active alerts.

**Parameters:**

- `device_id` (string, optional): Filter alerts to a specific device.
- `triggered_only` (boolean, optional, default: True): If `True`, only returns alerts that are currently in a triggered state. If `False`, it includes resolved alerts as well.
- `limit` (integer, optional, default: 25): The maximum number of alerts to return.

**Returns:** A list of alerts, including the alert title, status (triggered/resolved), device name, and timestamp.

**Example Usage:**

> `get_alerts(triggered_only=True)`

### 6. `get_facility_summary`

Generates a high-level summary of the entire monitored environment, including device counts, total readings, and active alerts.

**Parameters:**

- `company_name` (string, optional): Filter the summary to a specific company.

**Returns:** A formatted summary report.

**Example Usage:**

> `get_facility_summary()`

### 7. `query_sensor_data`

A powerful tool that allows you to run a custom SQL `WHERE` clause against the `sensor_readings` table. This enables highly specific and complex data exploration.

**Parameters:**

- `sql_where` (string, required): A valid SQL `WHERE` clause (without the `WHERE` keyword).
- `limit` (integer, optional, default: 100): The maximum number of rows to return.

**Returns:** A list of sensor readings that match the query.

**Example Usage:**

> `query_sensor_data(sql_where="type = 'temp' AND value > 25 AND device_id LIKE '%1eaedbc0%'")`

### 8. `get_event_log`

Retrieves the raw log of incoming webhook events. This is useful for debugging and understanding the flow of data into the system.

**Parameters:**

- `event_type` (string, optional): Filter the log by event type (`uplink`, `alert`, `ping`).
- `limit` (integer, optional, default: 20): The maximum number of log entries to return.

**Returns:** A list of recent events with their type and timestamp.

**Example Usage:**

> `get_event_log(event_type="alert")`

### 9. `get_gateway_status`

Checks the health and connectivity of your LoRaWAN gateways by showing the most recent `ping` events they have sent.

**Parameters:**

- `limit` (integer, optional, default: 20): The maximum number of ping events to return.

**Returns:** A list of recent gateway pings, indicating when each gateway last checked in.

**Example Usage:**

> `get_gateway_status()`
