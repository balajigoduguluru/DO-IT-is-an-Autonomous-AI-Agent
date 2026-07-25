### Task 3: Build API Service Layer

**Files:**
- Create: `frontend/src/api/api.ts`

**Interfaces:**
- Consumes: Types from Task 2
- Produces: `healthCheck(): Promise<boolean>`, `createSession(): Promise<string>`, `setGoal(sessionId, goal): Promise<void>`, `startExecution(sessionId): Promise<void>`, `respondApproval(sessionId, approvalId, approved): Promise<void>`, `getGraphData(sessionId): Promise<{nodes, edges}>`, `getLedger(sessionId): Promise<unknown[]>`

- [ ] **Step 1: Create the API client**

Write `frontend/src/api/api.ts`:

```typescript
const BASE = '/api';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const options: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) {
    options.body = JSON.stringify(body);
  }

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, options);
  } catch (err) {
    throw new ApiError(0, 'Network error — is the server running?');
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || body.message || detail;
    } catch {
      // keep default
    }
    throw new ApiError(res.status, detail);
  }

  const text = await res.text();
  if (!text) return {} as T;
  return JSON.parse(text) as T;
}

// ---- Public API ----

export async function healthCheck(): Promise<boolean> {
  try {
    const result = await request<{ status: string }>('GET', '/health');
    return result.status === 'ok';
  } catch {
    return false;
  }
}

export async function createSession(): Promise<string> {
  const result = await request<{ session_id: string }>('POST', '/session');
  return result.session_id;
}

export async function setGoal(sessionId: string, goal: string): Promise<void> {
  await request('POST', `/session/${sessionId}/goal`, {
    goal,
    constraints: {},
  });
}

export async function startExecution(sessionId: string): Promise<void> {
  await request('POST', `/session/${sessionId}/start`);
}

export async function respondApproval(
  sessionId: string,
  approvalId: string,
  approved: boolean,
): Promise<void> {
  await request('POST', `/approval/${sessionId}/respond`, {
    approval_id: approvalId,
    approved,
  });
}

export async function getGraphData(
  sessionId: string,
): Promise<{ nodes: Record<string, unknown>; edges: string[][] }> {
  return request('GET', `/session/${sessionId}/graph`);
}

export async function getLedger(sessionId: string): Promise<Record<string, unknown>[]> {
  const result = await request<{ entries: Record<string, unknown>[] }>(
    'GET',
    `/session/${sessionId}/ledger`,
  );
  return result.entries ?? [];
}
```

---

