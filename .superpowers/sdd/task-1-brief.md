### Task 1: Add Backend Health Endpoint

**Files:**
- Modify: `src/api/routes.py` — add health endpoint

**Interfaces:**
- Consumes: (none)
- Produces: `GET /api/health` → `{"status": "ok", "timestamp": "..."}`

- [ ] **Step 1: Add the import and endpoint**

Add the `datetime` import and health endpoint to `src/api/routes.py`.

```python
# Add to imports at the top (not present yet):
from datetime import datetime, timezone

# Add before "Session endpoints" section:
@router.get("/health")
async def health_check():
    """Lightweight health check for frontend availability detection."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
```

- [ ] **Step 2: Verify the endpoint works**

```bash
cd C:/Users/balaj/OneDrive/Documents/Projects/Agentic\ AI
curl -s http://localhost:8000/api/health 2>/dev/null || echo "Server not running — start with: uvicorn src.api.server:app --reload"
```

Expected: `{"status":"ok","timestamp":"2026-07-25T..."}`

---

