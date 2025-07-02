# M365 Inbox Connector

Microsoft 365 Email Fetching and Management System - Development Environment

## Project Overview

This project aims to develop an Inbox Connector that enables existing OF products to actively pull delivered emails from Microsoft 365 customer mailboxes, perform deep security analysis and archiving, and execute subsequent actions on original emails in M365 mailboxes based on analysis results.

**Tech Stack**: Python + FastAPI + MongoDB

## Project Structure

```text
inbox-connector/
├── main.py                     # FastAPI application main file
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Application container configuration
├── docker-compose.yaml         # Development environment configuration
├── mongo-init.js               # MongoDB initialization script
├── .gitignore                  # Git ignore settings
├── .devcontainer/              # VS Code Dev Container configuration
│   └── devcontainer.json
├── services/                   # Core service logic
│   ├── authService.py          # Authentication and Graph API client
│   ├── tenantService.py        # Tenant management logic
│   ├── dataService.py          # MongoDB data operations
│   ├── logService.py           # Logging setup
│   ├── mailService.py          # Mail fetching and processing
│   ├── attService.py           # Attachment handling
│   └── m365Connector.py        # Microsoft Graph API connectors
├── logger/                     # Logging utilities
│   ├── basicLogger.py          # Basic logging implementation
│   └── operationLogger.py      # Operation-specific logging
├── common/                     # Shared utilities and constants
│   ├── cipher.py               # Encryption utilities
│   └── constants.py            # Shared constants
└── README.md                   # Project documentation
```

## Quick Start

### Prerequisites

- Docker
- VS Code (recommended, supports Dev Container)

### Start Development Environment

```bash
# 1. Clone the project
git clone https://github.com/andyy0123/inbox-connector.git
cd inbox-connector

# 2. Start development environment
docker-compose up -d

# 3. Check service status
docker-compose ps

# 4. Test API
curl http://localhost:8000/
```

### Using VS Code Dev Container (Advanced)

1. Ensure "Dev Containers" extension is installed.
2. Open the project in VS Code.
3. Press `Ctrl+Shift+P` (macOS: `Cmd+Shift+P`).
4. Select "Dev Containers: Reopen in Container".
5. VS Code will automatically open the project in the container.

## API Endpoints

### Health Check

- **GET** `/`
  - **Description**: Check if the API is running.
  - **Response**: `{ "status": "ok", "message": "Welcome to the Graph Tenant API" }`

### Tenant Management

- **POST** `/tenant/init`
  - **Description**: Initialize a new tenant.
  - **Body**:
    ```json
    {
      "tenant_id": "your-tenant-id",
      "client_id": "your-client-id",
      "client_secret": "your-client-secret"
    }
    ```

- **PUT** `/tenant/update`
  - **Description**: Update tenant credentials.
  - **Body**: Same as `/tenant/init`.

- **GET** `/tenant/{tenant_id}/users`
  - **Description**: Retrieve all users for a tenant.

- **GET** `/tenant/{tenant_id}/users/{user_id}/mails`
  - **Description**: Retrieve all emails for a specific user.

## Development Notes

- Ensure MongoDB is running and accessible at the configured `MONGODB_URL`.
- Logs are stored in `operation.log` for debugging purposes.
- Use `docker-compose logs` to view container logs.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
