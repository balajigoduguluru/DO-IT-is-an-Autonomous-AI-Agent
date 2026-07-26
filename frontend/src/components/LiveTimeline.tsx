import React from 'react';

interface LiveTimelineProps {
  phases?: string[];
  currentPhase?: string;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export default function LiveTimeline({
  phases = [],
  currentPhase,
  loading = false,
  error = null,
  onRetry,
}: LiveTimelineProps) {
  if (loading) {
    return (
      <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-4">
        <div className="flex items-center justify-center gap-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="skeleton h-3 w-20 rounded-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4">
        <div className="flex items-center justify-center gap-3">
          <svg
            className="h-5 w-5 text-red-400"
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
              className="text-xs font-medium text-red-400 underline underline-offset-2"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!phases || phases.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-700 p-6 text-center">
        <p className="text-sm text-gray-500">No phases defined yet</p>
        <p className="text-xs text-gray-600">
          Set a goal to begin the planning process.
        </p>
      </div>
    );
  }

  const currentIdx = currentPhase
    ? phases.indexOf(currentPhase)
    : -1;

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-4">
      <div className="flex items-center justify-start gap-0 overflow-x-auto py-2">
        {phases.map((phase, idx) => {
          const isCompleted = currentIdx > idx;
          const isCurrent = currentIdx === idx;

          return (
            <React.Fragment key={phase}>
              {/* Phase step */}
              <div className="flex flex-col items-center gap-1.5 shrink-0">
                {/* Circle */}
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-full border-2 transition-all duration-500 ${
                    isCompleted
                      ? 'border-green-500 bg-green-500/20'
                      : isCurrent
                        ? 'border-blue-500 bg-blue-500/20 animate-pulse'
                        : 'border-gray-700 bg-gray-800/50'
                  }`}
                >
                  {isCompleted ? (
                    <svg
                      className="h-4 w-4 text-green-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2.5}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M4.5 12.75l6 6 9-13.5"
                      />
                    </svg>
                  ) : isCurrent ? (
                    <span className="h-2.5 w-2.5 rounded-full bg-blue-400" />
                  ) : (
                    <span className="h-2.5 w-2.5 rounded-full bg-gray-600" />
                  )}
                </div>

                {/* Label */}
                <span
                  className={`whitespace-nowrap text-[11px] font-medium transition-colors duration-300 ${
                    isCompleted
                      ? 'text-green-400'
                      : isCurrent
                        ? 'text-blue-400'
                        : 'text-gray-600'
                  }`}
                >
                  {phase
                    .replace(/_/g, ' ')
                    .replace(/\b\w/g, (c) => c.toUpperCase())}
                </span>
              </div>

              {/* Connector line */}
              {idx < phases.length - 1 && (
                <div
                  className={`mx-1 h-0.5 w-12 shrink-0 transition-colors duration-500 ${
                    isCompleted
                      ? 'bg-green-500/50'
                      : isCurrent
                        ? 'bg-blue-500/30'
                        : 'bg-gray-800'
                  }`}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
