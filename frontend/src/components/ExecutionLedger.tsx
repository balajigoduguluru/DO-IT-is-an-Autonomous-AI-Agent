import React, { useEffect, useRef } from 'react';
import { format } from 'date-fns';

export interface LedgerEntry {
  id: string;
  timestamp: string;
  agent_name: string;
  action: string;
  description: string;
  confidence: number;
  metadata?: Record<string, unknown>;
}

interface ExecutionLedgerProps {
  entries?: LedgerEntry[];
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

function getConfidenceBarClass(confidence: number): string {
  if (confidence >= 0.8) return 'confidence-high';
  if (confidence >= 0.5) return 'confidence-medium';
  return 'confidence-low';
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'text-green-400';
  if (confidence >= 0.5) return 'text-yellow-400';
  return 'text-red-400';
}

export default function ExecutionLedger({
  entries,
  loading = false,
  error = null,
  onRetry,
}: ExecutionLedgerProps) {
  const listEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  if (loading) {
    return (
      <div className="space-y-3 p-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="skeleton h-20 w-full rounded-xl" />
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

  if (!entries || entries.length === 0) {
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
              d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
            />
          </svg>
          <p className="text-sm text-gray-500">No entries yet</p>
          <p className="text-xs text-gray-600">
            Start execution to see the ledger.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="space-y-2">
        {entries.map((entry) => {
          const confidencePct = Math.round(entry.confidence * 100);
          return (
            <div
              key={entry.id}
              className="animate-fade-in rounded-xl border border-gray-800 bg-gray-900/60 p-4 transition-colors hover:border-gray-700"
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-800 text-[10px] font-bold text-gray-400 uppercase">
                    {entry.agent_name.charAt(0)}
                  </span>
                  <span className="text-xs font-medium text-gray-300">
                    {entry.agent_name}
                  </span>
                </div>
                <span className="text-[11px] text-gray-500">
                  {format(new Date(entry.timestamp), 'HH:mm:ss')}
                </span>
              </div>

              <p className="mb-1 text-sm font-medium text-gray-200">
                {entry.action}
              </p>
              <p className="mb-3 text-xs text-gray-400">{entry.description}</p>

              <div className="flex items-center gap-3">
                <span
                  className={`text-[11px] font-semibold ${getConfidenceColor(entry.confidence)}`}
                >
                  {confidencePct}%
                </span>
                <div className="flex-1 overflow-hidden rounded-full bg-gray-800">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-500 ${getConfidenceBarClass(entry.confidence)}`}
                    style={{ width: `${confidencePct}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div ref={listEndRef} />
    </div>
  );
}
