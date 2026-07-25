### Task 8: Build ResultPanel with Copy and Export

**Files:**
- Create: `frontend/src/components/ResultPanel.tsx`

**Interfaces:**
- Consumes: `useExecution()` hook
- Produces: Result display with Copy, New Goal, Export buttons

- [ ] **Step 1: Create ResultPanel**

Write `frontend/src/components/ResultPanel.tsx`:

```typescriptx
import React, { useState } from 'react';

interface Props {
  result: string | null;
  error: string | null;
  status: string;
  onNewGoal: () => void;
}

export default function ResultPanel({ result, error, status, onNewGoal }: Props) {
  const [copied, setCopied] = useState(false);

  if (!result && !error) return null;
  if (status !== 'completed' && status !== 'failed') return null;

  const handleCopy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const textarea = document.createElement('textarea');
      textarea.value = result;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleExport = () => {
    if (!result) return;
    const blob = new Blob([result], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agentic-ai-result-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-red-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">😕</span>
          <div>
            <h3 className="text-base font-semibold text-gray-900">Something went wrong</h3>
            <p className="text-sm text-gray-500 mt-0.5">{error}</p>
          </div>
        </div>
        <button
          onClick={onNewGoal}
          className="px-5 py-2.5 text-sm font-medium text-white bg-primary hover:bg-primary-600 rounded-lg transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-xl">✨</span>
        <h3 className="text-base font-semibold text-gray-900">Final Answer</h3>
      </div>

      <div className="prose prose-sm max-w-none text-gray-700 leading-relaxed whitespace-pre-wrap">
        {result}
      </div>

      <div className="flex gap-3 pt-2">
        <button
          onClick={handleCopy}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors flex items-center gap-1.5"
        >
          {copied ? (
            <>
              <svg className="h-4 w-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              Copied
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
              </svg>
              Copy
            </>
          )}
        </button>
        <button
          onClick={onNewGoal}
          className="px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary-600 rounded-lg transition-colors"
        >
          New Goal
        </button>
        <button
          onClick={handleExport}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors flex items-center gap-1.5"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          Export
        </button>
      </div>
    </div>
  );
}
```

---

