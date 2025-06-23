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
├── mongo-init.js              # MongoDB initialization script
├── .gitignore                 # Git ignore settings
├── .devcontainer/             # VS Code Dev Container configuration
│   └── devcontainer.json
└── README.md                  # Project documentation
```

## Quick Start

### Prerequisites

- Docker
- VS Code (recommended, supports Dev Container)

### Start Development Environment

```bash
# 1. Clone the project
git clone [<repository-url>](https://github.com/andyy0123/inbox-connector.git)
cd inbox-connector

# 2. Start development environment
docker-compose up -d

# 3. Check service status
docker-compose ps

# 4. Test API
curl http://localhost:8000/health
```

### Using VS Code Dev Container (Advanced)

1. Ensure "Dev Containers" extension is installed
2. Open project in VS Code
3. Press `Ctrl+Shift+P` (macOS: `Cmd+Shift+P`)
4. Select "Dev Containers: Reopen in Container"
5. VS Code will automatically open the project in container
