# Cognituv Connect MCP Server

This project provides a Model Context Protocol (MCP) server that acts as a bridge between the myDevices IoT platform (used by Cognituv Connect) and AI agents like Claude. It enables AI-powered analysis and interaction with real-time sensor data from your facilities.

The server is built with Python using FastAPI for the web framework and FastMCP for the MCP implementation. It listens for incoming webhooks from myDevices, stores the data in a local SQLite database, and exposes a rich set of tools for querying and analyzing that data.

## Features

- **Webhook Receiver**: A robust FastAPI endpoint that receives `uplink`, `alert`, and `ping` events from myDevices.
- **Data Persistence**: All incoming data is stored in a structured SQLite database, creating a historical record of sensor readings and alerts.
- **AI-Ready Tools**: A suite of 9 powerful MCP tools allows AI agents to perform complex queries and analysis on your IoT data.
- **Containerized Deployment**: Comes with a `Dockerfile` and `docker-compose.yml` for easy, repeatable deployment.
- **Extensible**: The code is modular and well-documented, making it easy to add new tools or support custom data processing.

## Getting Started

### Prerequisites

- Docker and Docker Compose
- A myDevices / Cognituv Connect account with active devices
- A publicly accessible server or a tunneling service (like ngrok) to expose the webhook endpoint

### 1. Configuration

1.  Clone this repository.
2.  Copy the `.env.example` file to `.env`:
    ```bash
    cp .env.example .env
    ```
3.  (Optional) Edit the `.env` file to set a `COGNITUV_WEBHOOK_SECRET`. This is a shared secret that the server will use to authenticate incoming webhooks.

### 2. Running the Server

You can run the server using Docker Compose:

```bash
docker-compose up --build -d
```

This will build the Docker image and start the server in the background. The server will be accessible on port 8000.

To check the logs:

```bash
docker-compose logs -f
```

### 3. Webhook Configuration in myDevices

1.  Log in to your [myDevices dashboard](https://cognituv.mydevices.com/).
2.  Navigate to **Integrations** and select **Webhook**.
3.  Click **Add New**.
4.  Configure the webhook with the following settings:
    - **Name**: A descriptive name, e.g., `Cognituv MCP Server`.
    - **URL**: The publicly accessible URL of your server's webhook endpoint (e.g., `https://your-domain.com/webhook`).
    - **Headers**: If you set a `COGNITUV_WEBHOOK_SECRET` in your `.env` file, add a header here. The key should be `x-api` and the value should be your secret.
    - **Event Subscriptions**: Select `Alert`, `Uplink`, and `Ping`.
    - **Device Subscriptions**: Select `Any Devices`.
    - **Data Fields**: Ensure `All Data Points` is checked.
5.  Save the integration.

Your server will now start receiving data from your Cognituv Connect devices.

## MCP Tools

The server exposes the following tools for AI agents to use. These tools allow for powerful, natural language queries into your facility data.

*   `list_devices`: List all registered devices, with optional filtering.
*   `get_device_details`: Get full metadata for a specific device.
*   `get_latest_readings`: Fetch the most recent sensor reading for each channel on a device.
*   `get_reading_history`: Retrieve historical time-series data for a device.
*   `get_alerts`: Query for active or resolved alerts.
*   `get_facility_summary`: Get a high-level overview of all monitored locations.
*   `query_sensor_data`: Run a custom SQL `WHERE` clause against the sensor data.
*   `get_event_log`: View the raw incoming event log.
*   `get_gateway_status`: Check the health of your gateways based on recent pings.

For detailed documentation on each tool, please see the [TOOLS.md](docs/TOOLS.md) file.

## Architecture

The application consists of three main components:

1.  **`server.py`**: The main FastAPI and FastMCP application. It handles:
    - The `/webhook` endpoint for receiving data.
    - The `/mcp` endpoint for serving MCP tools over Streamable HTTP.
    - Database initialization and session management.
2.  **`database.py`**: Contains the SQLite database schema and helper functions for creating and connecting to the database.
3.  **`tools.py`**: Defines all the MCP tools that are exposed to the AI agents.

Data flows from myDevices to the webhook, is processed and stored in the SQLite database, and then made available for querying via the MCP tools.

## Development

To run the server locally for development:

1.  Create a Python virtual environment and install dependencies:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
2.  Run the server with auto-reloading:
    ```bash
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload
    ```
3.  Use the `test_webhook.py` script to send sample payloads to your local server:
    ```bash
    python3 test_webhook.py
    ```
