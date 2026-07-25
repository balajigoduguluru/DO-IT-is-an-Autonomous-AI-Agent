
export interface RiskAssessment {
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
}

interface RiskPanelProps {
  assessments?: RiskAssessment[];
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

const levelConfig: Record<string, { label: string; textCls: string; bgCls: string; borderCls: string }> = {
  low: { label: 'Low', textCls: 'text-green-700', bgCls: 'bg-green-50', borderCls: 'border-green-200' },
  medium: { label: 'Medium', textCls: 'text-yellow-700', bgCls: 'bg-yellow-50', borderCls: 'border-yellow-200' },
  high: { label: 'High', textCls: 'text-orange-700', bgCls: 'bg-orange-50', borderCls: 'border-orange-200' },
  critical: { label: 'Critical', textCls: 'text-red-700', bgCls: 'bg-red-50', borderCls: 'border-red-200' },
};

export default function RiskPanel({
  assessments,
  loading = false,
  error = null,
  onRetry,
}: RiskPanelProps) {
  // Loading
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="skeleton h-40 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  // Error
  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-6">
        <div className="text-center">
          <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-red-50 flex items-center justify-center">
            <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          </div>
          <p className="text-sm text-gray-500 mb-3">{error}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="px-4 py-2 bg-primary text-white text-sm font-medium rounded-lg hover:bg-primary-600 transition-colors"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    );
  }

  // Empty
  if (!assessments || assessments.length === 0) {
    return (
      <div className="flex items-center justify-center h-full p-6">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-gray-100 flex items-center justify-center">
            <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-gray-700">No risk assessments yet</p>
          <p className="text-xs text-gray-400 mt-1">Risk analysis will appear once execution begins.</p>
        </div>
      </div>
    );
  }

  // Success
  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {assessments.map((a) => {
          const lvl = levelConfig[a.level] || levelConfig.low;
          const confidencePct = Math.round(a.confidence * 100);
          const cost = a.cost_estimate.estimated;
          const currency = a.cost_estimate.currency?.toUpperCase() || 'USD';

          return (
            <div
              key={a.id}
              className={`rounded-lg border ${lvl.borderCls} bg-white p-5 shadow-sm`}
            >
              {/* Header */}
              <div className="flex items-center justify-between gap-2 mb-3">
                <h3 className="text-sm font-semibold text-gray-900">{a.category}</h3>
                <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${lvl.bgCls} ${lvl.textCls}`}>
                  {lvl.label}
                </span>
              </div>

              {/* Description */}
              <p className="text-xs text-gray-600 mb-3 leading-relaxed">{a.description}</p>

              {/* Confidence */}
              <div className="mb-3">
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-gray-500">Confidence</span>
                  <span className="font-medium text-gray-700">{confidencePct}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-gray-200 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      confidencePct >= 80 ? 'bg-green-500' : confidencePct >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${confidencePct}%` }}
                  />
                </div>
              </div>

              {/* Security Flags */}
              {a.security_flags && a.security_flags.length > 0 && (
                <div className="mb-3">
                  <p className="text-[11px] font-medium text-gray-500 mb-1.5">Security Flags</p>
                  <div className="flex flex-wrap gap-1.5">
                    {a.security_flags.map((flag, idx) => (
                      <span key={idx} className="rounded-md bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700">
                        {flag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Cost */}
              <div className="rounded-md bg-gray-50 px-3 py-2.5">
                <p className="text-[11px] text-gray-500 mb-0.5">Estimated Cost</p>
                <p className="text-sm font-semibold text-gray-900">
                  {currency} {cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </p>
                {a.cost_estimate.breakdown && (
                  <div className="mt-1.5 space-y-0.5">
                    {Object.entries(a.cost_estimate.breakdown).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between text-[11px]">
                        <span className="text-gray-500 capitalize">{key.replace(/_/g, ' ')}</span>
                        <span className="text-gray-700 font-medium">{currency} {value.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
