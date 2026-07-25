import React from 'react';

export interface ApprovalRequest {
  id: string;
  action: string;
  description: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
  reasoning: string;
  status: 'pending' | 'approved' | 'rejected';
  expires_at?: string;
  created_at: string;
}

interface ApprovalGateProps {
  requests?: ApprovalRequest[];
  onRespond?: (id: string, approved: boolean) => void;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

function getRiskBadgeClass(level: string): string {
  switch (level) {
    case 'low':
      return 'risk-bg-low risk-low';
    case 'medium':
      return 'risk-bg-medium risk-medium';
    case 'high':
      return 'risk-bg-high risk-high';
    case 'critical':
      return 'risk-bg-critical risk-critical';
    default:
      return 'bg-gray-500/20 text-gray-400';
  }
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'text-green-400';
  if (confidence >= 0.5) return 'text-yellow-400';
  return 'text-red-400';
}

export default function ApprovalGate({
  requests,
  onRespond,
  loading = false,
  error = null,
  onRetry,
}: ApprovalGateProps) {
  if (loading) {
    return (
      <div className="space-y-3 p-4">
        {[1, 2].map((i) => (
          <div key={i} className="skeleton h-36 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-4">
        <div className="flex flex-col items-center gap-4 rounded-xl border border-red-500/30 bg-red-500/10 px-6 py-5 text-center">
          <svg
            className="h-8 w-8 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
            />
          </svg>
          <p className="text-sm text-red-300">{error}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="rounded-lg bg-red-500/20 px-4 py-2 text-sm font-medium text-red-300 transition-colors hover:bg-red-500/30"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  const pendingRequests = (requests || []).filter(
    (r) => r.status === 'pending',
  );

  if (!requests || requests.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-4">
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-gray-700 px-6 py-10 text-center">
          <svg
            className="h-10 w-10 text-gray-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
            />
          </svg>
          <p className="text-sm text-gray-500">No pending approvals</p>
          <p className="text-xs text-gray-600">
            All decisions have been made.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-300">
          Approval Requests
        </h3>
        {pendingRequests.length > 0 && (
          <span className="rounded-full bg-yellow-500/20 px-2.5 py-0.5 text-[11px] font-semibold text-yellow-400">
            {pendingRequests.length} pending
          </span>
        )}
      </div>
      <div className="space-y-3">
        {requests.map((req) => {
          const confidencePct = Math.round(req.confidence * 100);
          const isPending = req.status === 'pending';
          const isApproved = req.status === 'approved';
          const isRejected = req.status === 'rejected';

          return (
            <div
              key={req.id}
              className={`animate-fade-in rounded-xl border p-4 transition-all ${
                isApproved
                  ? 'border-green-500/30 bg-green-500/5'
                  : isRejected
                    ? 'border-red-500/30 bg-red-500/5'
                    : 'border-gray-800 bg-gray-900/60'
              }`}
            >
              <div className="mb-3 flex items-start justify-between gap-2">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-200">
                    {req.action}
                  </p>
                  <p className="mt-1 text-xs text-gray-400">
                    {req.description}
                  </p>
                </div>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${getRiskBadgeClass(req.risk_level)}`}
                >
                  {req.risk_level}
                </span>
              </div>

              <div className="mb-3 rounded-lg bg-gray-800/50 p-3">
                <p className="text-[11px] italic text-gray-400">
                  {req.reasoning}
                </p>
              </div>

              <div className="mb-3 flex items-center gap-3">
                <span
                  className={`text-[11px] font-semibold ${getConfidenceColor(req.confidence)}`}
                >
                  {confidencePct}% confident
                </span>
                <div className="flex-1 overflow-hidden rounded-full bg-gray-800">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-500 ${confidencePct >= 80 ? 'confidence-high' : confidencePct >= 50 ? 'confidence-medium' : 'confidence-low'}`}
                    style={{ width: `${confidencePct}%` }}
                  />
                </div>
              </div>

              {req.expires_at && isPending && (
                <p className="mb-3 text-[11px] text-gray-500">
                  Expires:{' '}
                  {new Date(req.expires_at).toLocaleTimeString()}
                </p>
              )}

              {isPending && onRespond && (
                <div className="flex gap-2">
                  <button
                    onClick={() => onRespond(req.id, true)}
                    className="flex-1 rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-2 text-xs font-medium text-green-400 transition-colors hover:bg-green-500/20"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => onRespond(req.id, false)}
                    className="flex-1 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs font-medium text-red-400 transition-colors hover:bg-red-500/20"
                  >
                    Reject
                  </button>
                </div>
              )}

              {!isPending && (
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[11px] font-medium ${
                      isApproved ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    {isApproved ? 'Approved' : 'Rejected'}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
