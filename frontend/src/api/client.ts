const BASE = '';

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE}${endpoint}`;
  const config: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    let errorMessage: string;
    try {
      const errorBody = await response.json();
      errorMessage =
        errorBody.detail || errorBody.message || JSON.stringify(errorBody);
    } catch {
      errorMessage = response.statusText || `HTTP ${response.status}`;
    }
    throw new Error(`API Error (${response.status}): ${errorMessage}`);
  }

  const text = await response.text();
  if (!text) return {} as T;
  return JSON.parse(text) as T;
}

export async function createSession(): Promise<{ session_id: string }> {
  return request<{ session_id: string }>('/api/sessions', {
    method: 'POST',
  });
}

export async function setGoal(
  sessionId: string,
  goal: string,
  constraints?: Record<string, unknown>,
): Promise<{ session_id: string }> {
  return request<{ session_id: string }>(`/api/sessions/${sessionId}/goal`, {
    method: 'POST',
    body: JSON.stringify({ goal, constraints: constraints ?? {} }),
  });
}

export async function startExecution(
  sessionId: string,
): Promise<{ session_id: string }> {
  return request<{ session_id: string }>(
    `/api/sessions/${sessionId}/execute`,
    {
      method: 'POST',
    },
  );
}

export async function getSession(
  sessionId: string,
): Promise<{
  session_id: string;
  goal: string;
  status: string;
  created_at: string;
  updated_at: string;
  phases: string[];
  current_phase: string;
}> {
  return request(`/api/sessions/${sessionId}`);
}

export async function getGraph(
  sessionId: string,
): Promise<{
  nodes: Array<{
    id: string;
    label: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'replanning';
    type?: string;
    metadata?: Record<string, unknown>;
  }>;
  edges: Array<{
    from: string;
    to: string;
    label?: string;
  }>;
}> {
  return request(`/api/sessions/${sessionId}/graph`);
}

export async function getLedger(
  sessionId: string,
): Promise<{
  entries: Array<{
    id: string;
    timestamp: string;
    agent_name: string;
    action: string;
    description: string;
    confidence: number;
    metadata?: Record<string, unknown>;
  }>;
}> {
  return request(`/api/sessions/${sessionId}/ledger`);
}

export async function getTools(): Promise<{
  tools: Array<{
    name: string;
    description: string;
    parameters: Record<string, unknown>;
  }>;
}> {
  return request('/api/tools');
}

export async function respondApproval(
  sessionId: string,
  approvalId: string,
  approved: boolean,
): Promise<{ status: string }> {
  return request<{ status: string }>(
    `/api/sessions/${sessionId}/approvals/${approvalId}`,
    {
      method: 'POST',
      body: JSON.stringify({ approved }),
    },
  );
}

export async function getRiskAssessments(
  sessionId: string,
): Promise<{
  assessments: Array<{
    id: string;
    category: string;
    level: 'low' | 'medium' | 'high' | 'critical';
    confidence: number;
    description: string;
    security_flags: string[];
    cost_estimate: {
      estimated: number;
      currency: string;
      breakdown?: Record<string, number>;
    };
    timestamp: string;
  }>;
}> {
  return request(`/api/sessions/${sessionId}/risks`);
}

export async function getApprovals(
  sessionId: string,
): Promise<{
  requests: Array<{
    id: string;
    action: string;
    description: string;
    risk_level: 'low' | 'medium' | 'high' | 'critical';
    confidence: number;
    reasoning: string;
    status: 'pending' | 'approved' | 'rejected';
    expires_at?: string;
    created_at: string;
  }>;
}> {
  return request(`/api/sessions/${sessionId}/approvals`);
}
