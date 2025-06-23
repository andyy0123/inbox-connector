from fastapi import FastAPI
import uvicorn
from datetime import datetime

# 初始化 FastAPI 應用
app = FastAPI(
    title="M365 Inbox Connector",
    description="M365 Inbox Connector",
    version="1.0.0"
)

# Health Check
@app.get("/health")
async def health_check():
    """health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "M365 Inbox Connector"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)