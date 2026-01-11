# api_keys.py
from fastapi import HTTPException, Request

API_CLIENTS = {
    "test-key-123": {
        "client_id": "cli_001",
        "name": "demo-client",
        "plan": "starter",
        "status": "active",
        "features": ["sign_invoice", "validate_invoice", "generate_pdf"],
        "rate_limit_per_min": 60
    },
    "prod-key-abc": {
        "client_id": "cli_002",
        "name": "first-customer",
        "plan": "pro",
        "status": "active",
        "features": ["sign_invoice", "validate_invoice", "generate_pdf", "audit"],
        "rate_limit_per_min": 600
    }
}

def get_client(request: Request):
    api_key = request.headers.get("x-api-key")

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")

    client = API_CLIENTS.get(api_key)
    if not client:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")

    if client.get("status") != "active":
        raise HTTPException(status_code=403, detail="Client disabled")

    return client

def require_feature(client: dict, feature: str):
    if feature not in client.get("features", []):
        raise HTTPException(status_code=403, detail=f"Feature '{feature}' not allowed for this client")
