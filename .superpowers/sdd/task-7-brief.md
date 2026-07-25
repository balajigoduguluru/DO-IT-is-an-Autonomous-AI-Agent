### Task 7: Build UI Components (StatusCard, GoalInput, CurrentTask, ThinkingPanel, ProgressBar, ActivityFeed, ApprovalDialog)

**Files:**
- Create: `frontend/src/components/StatusCard.tsx`
- Create: `frontend/src/components/GoalInput.tsx`
- Create: `frontend/src/components/CurrentTask.tsx`
- Create: `frontend/src/components/ThinkingPanel.tsx`
- Create: `frontend/src/components/ProgressBar.tsx`
- Create: `frontend/src/components/ActivityFeed.tsx`
- Create: `frontend/src/components/ApprovalDialog.tsx`

**Interfaces:**
- Consumes: `useExecution()` hook (Task 6)
- Produces: Pure presentational components with Tailwind styling

- [ ] **Step 1: Create StatusCard**

Write `frontend/src/components/StatusCard.tsx`:

```typescriptx
import React from 'react';
import type { BackendStatus } from '../types';

interface Props {
  backendStatus: BackendStatus;
  devMode: boolean;
  onToggleDevMode: () => void;
}

export default function StatusCard({ backendStatus, devMode, onToggleDevMode }: Props) {
  const isOnline = backendStatus === 'online';

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-lg font-semibold text-gray-900">AI Ready</span>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-50 border border-green-200">
          <span className={`h-2 w-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'} ${isOnline ? '' : 'animate-pulse'}`} />
          <span className="text-xs font-medium text-green-700">
            {isOnline ? 'Connected' : 'Offline'}
          </span>
        </div>
      </div>
      <button
        onClick={onToggleDevMode}
        className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
          devMode
            ? 'bg-primary/10 border-primary/30 text-primary'
            : 'bg-gray-50 border-gray-200 text-gray-400 hover:text-gray-600'
        }`}
      >
        ⚙ Dev Mode
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Create GoalInput**

Write `frontend/src/components/GoalInput.tsx`:

```typescriptx
import React, { useState } from 'react';

interface Props {
  onSubmit: (goal: string) => void;
  disabled: boolean;
  backendOnline: boolean;
}

export default function GoalInput({ onSubmit, disabled, backendOnline }: Props) {
  const [goal, setGoal] = useState('');

  const handleSubmit = () => {
    if (!goal.trim() || disabled || !backendOnline) return;
    onSubmit(goal.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        What would you like me to help you with?
      </label>
      <div className="flex gap-3">
        <input
          type="text"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Plan my Goa trip under ₹25,000..."
          disabled={disabled}
          className="flex-1 h-12 px-4 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 shadow-sm focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none transition-all disabled:bg-gray-50 disabled:text-gray-400"
        />
        <button
          onClick={handleSubmit}
          disabled={!goal.trim() || disabled || !backendOnline}
          className="h-12 px-6 bg-primary text-white text-sm font-medium rounded-xl hover:bg-primary-600 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow flex items-center gap-2"
        >
          {disabled ? (
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
            </svg>
          )}
          Start AI
        </button>
      </div>
      {!backendOnline && (
        <p className="text-sm text-red-600 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
          Backend offline — please start the server
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create CurrentTask**

Write `frontend/src/components/CurrentTask.tsx`:

```typescriptx
import React from 'react';

interface Props {
  task: string;
  visible: boolean;
}

export default function CurrentTask({ task, visible }: Props) {
  if (!visible || !task) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">
        Current Task
      </div>
      <div className="flex items-center gap-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-primary animate-pulse" />
        <span className="text-base font-medium text-gray-900">{task}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create ThinkingPanel**

Write `frontend/src/components/ThinkingPanel.tsx`:

```typescriptx
import React from 'react';
import type { ThinkingStep } from '../types';

interface Props {
  steps: ThinkingStep[];
  visible: boolean;
}

export default function ThinkingPanel({ steps, visible }: Props) {
  if (!visible || steps.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
        Thinking
      </div>
      <div className="space-y-2">
        {steps.map((step) => (
          <div key={step.id} className="flex items-center gap-2.5 text-sm">
            {step.status === 'done' && (
              <span className="flex-shrink-0 h-5 w-5 rounded-full bg-green-100 flex items-center justify-center">
                <svg className="h-3 w-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              </span>
            )}
            {step.status === 'current' && (
              <span className="flex-shrink-0 h-5 w-5 rounded-full border-2 border-primary flex items-center justify-center">
                <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
              </span>
            )}
            {step.status === 'pending' && (
              <span className="flex-shrink-0 h-5 w-5 rounded-full border-2 border-gray-200" />
            )}
            {step.status === 'error' && (
              <span className="flex-shrink-0 h-5 w-5 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="h-3 w-3 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </span>
            )}
            <span
              className={`${
                step.status === 'done'
                  ? 'text-gray-500'
                  : step.status === 'current'
                  ? 'text-gray-900 font-medium'
                  : step.status === 'error'
                  ? 'text-red-600'
                  : 'text-gray-300'
              }`}
            >
              {step.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create ProgressBar**

Write `frontend/src/components/ProgressBar.tsx`:

```typescriptx
import React from 'react';
import type { ProgressInfo } from '../types';

interface Props {
  progress: ProgressInfo | null;
  visible: boolean;
}

export default function ProgressBar({ progress, visible }: Props) {
  if (!visible || !progress) return null;

  const { current, total } = progress;
  const pct = Math.round((current / total) * 100);

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs font-medium text-gray-400 uppercase tracking-wider">
          Progress
        </div>
        <span className="text-sm font-medium text-gray-600">
          Step {current} of {total}
        </span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create ActivityFeed**

Write `frontend/src/components/ActivityFeed.tsx`:

```typescriptx
import React, { useRef, useEffect } from 'react';
import type { Activity } from '../types';

interface Props {
  activities: Activity[];
  visible: boolean;
}

export default function ActivityFeed({ activities, visible }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activities.length]);

  if (!visible || activities.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
        Activity
      </div>
      <div className="space-y-1.5 max-h-48 overflow-y-auto">
        {activities.map((activity) => (
          <div key={activity.id} className="flex items-start gap-2 text-sm">
            <span className="text-gray-400 font-mono text-xs mt-0.5 flex-shrink-0">
              {activity.time}
            </span>
            <span className="text-gray-700">{activity.text}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Create ApprovalDialog**

Write `frontend/src/components/ApprovalDialog.tsx`:

```typescriptx
import React from 'react';
import type { ApprovalInfo } from '../types';

interface Props {
  approval: ApprovalInfo | null;
  onRespond: (approved: boolean) => void;
}

export default function ApprovalDialog({ approval, onRespond }: Props) {
  if (!approval) return null;

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full mx-4 p-6 space-y-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">👤</span>
          <div>
            <h3 className="text-base font-semibold text-gray-900">Action Required</h3>
            <p className="text-sm text-gray-500 mt-0.5">
              {approval.action}
            </p>
          </div>
        </div>
        <p className="text-sm text-gray-700">
          I found the best option. Would you like me to continue?
        </p>
        <div className="flex gap-3 justify-end pt-2">
          <button
            onClick={() => onRespond(false)}
            className="px-5 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onRespond(true)}
            className="px-5 py-2 text-sm font-medium text-white bg-primary hover:bg-primary-600 rounded-lg transition-colors shadow-sm"
          >
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

