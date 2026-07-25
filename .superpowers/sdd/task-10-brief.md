### Task 10: Build Dashboard Page and App Root

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/App.tsx` (simplify to wrap with ExecutionProvider + render Dashboard)
- Modify: `frontend/src/main.tsx` (add ErrorBoundary)
- Create: `frontend/src/components/ErrorBoundary.tsx`

**Interfaces:**
- Consumes: All components from Tasks 7-9, useExecution hook from Task 6

- [ ] **Step 1: Create ErrorBoundary**

Write `frontend/src/components/ErrorBoundary.tsx`:

```typescriptx
import React, { Component } from 'react';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 max-w-md w-full text-center space-y-4">
            <span className="text-4xl">😕</span>
            <h2 className="text-lg font-semibold text-gray-900">Something went wrong</h2>
            <p className="text-sm text-gray-500">{this.state.error?.message ?? 'An unexpected error occurred.'}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-5 py-2.5 text-sm font-medium text-white bg-primary hover:bg-primary-600 rounded-lg transition-colors"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
```

- [ ] **Step 2: Create Dashboard page**

Write `frontend/src/pages/Dashboard.tsx`:

```typescriptx
import React from 'react';
import { useExecution } from '../hooks/useExecution';
import { useExecutionContext } from '../context/ExecutionContext';
import StatusCard from '../components/StatusCard';
import GoalInput from '../components/GoalInput';
import CurrentTask from '../components/CurrentTask';
import ThinkingPanel from '../components/ThinkingPanel';
import ProgressBar from '../components/ProgressBar';
import ActivityFeed from '../components/ActivityFeed';
import ResultPanel from '../components/ResultPanel';
import ApprovalDialog from '../components/ApprovalDialog';
import DevModePanel from '../components/DevModePanel';

export default function Dashboard() {
  const { dispatch } = useExecutionContext();
  const {
    state,
    devData,
    startExecution,
    resetExecution,
    respondToApproval,
    isBusy,
    backendOnline,
  } = useExecution();

  const showLiveSections = state.status !== 'idle';
  const showResult = state.status === 'completed' || state.status === 'failed';

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* Status + Dev Mode toggle */}
        <StatusCard
          backendStatus={state.backendStatus}
          devMode={state.devMode}
          onToggleDevMode={() => dispatch({ type: 'TOGGLE_DEV_MODE' })}
        />

        {/* Goal Input — always visible */}
        <GoalInput
          onSubmit={startExecution}
          disabled={isBusy}
          backendOnline={backendOnline}
        />

        {/* Live sections — show during and after execution */}
        {showLiveSections && (
          <>
            <CurrentTask task={state.currentTask} visible={state.status === 'running'} />
            <ThinkingPanel steps={state.thinkingSteps} visible={showLiveSections} />
            <ProgressBar progress={state.progress} visible={showLiveSections && !showResult} />
            <ActivityFeed activities={state.activities} visible={showLiveSections} />
          </>
        )}

        {/* Result */}
        {showResult && (
          <ResultPanel
            result={state.result}
            error={state.error}
            status={state.status}
            onNewGoal={resetExecution}
          />
        )}

        {/* Dev Mode Panel — always at bottom when visible */}
        <DevModePanel devData={devData} visible={state.devMode} />
      </div>

      {/* Approval Dialog — rendered as overlay */}
      <ApprovalDialog
        approval={state.pendingApproval}
        onRespond={respondToApproval}
      />
    </div>
  );
}
```

Wait — `Dashboard.tsx` references `dispatch` without importing it. Let me fix that — it should use the context directly.

Actually, looking at this more carefully, `Dashboard.tsx` should get `dispatch` from the execution context. Let me restructure:

```typescriptx
import { useExecutionContext } from '../context/ExecutionContext';
// ...
const { dispatch } = useExecutionContext();
```

- [ ] **Step 3: Simplify App.tsx**

Write `frontend/src/App.tsx`:

```typescriptx
import { ExecutionProvider } from './context/ExecutionContext';
import Dashboard from './pages/Dashboard';

export default function App() {
  return (
    <ExecutionProvider>
      <Dashboard />
    </ExecutionProvider>
  );
}
```

- [ ] **Step 4: Update main.tsx with ErrorBoundary**

Write `frontend/src/main.tsx`:

```typescriptx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import './styles/globals.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
```

---

