import { motion } from 'framer-motion';
import { useExecutionContext } from '../../context/ExecutionContext';
import CurrentTask from './CurrentTask';
import ThinkingPanel from './ThinkingPanel';
import ReasoningPanel from './ReasoningPanel';
import ResultPanel from '../ResultPanel';
import ApprovalDialog from '../ApprovalDialog';
import { useAgentExecution } from '../../hooks/useAgentExecution';

export function ExecutionWorkspace() {
  const { state, dispatch } = useExecutionContext();
  const { respondToApproval } = useAgentExecution();
  
  const isExecuting = state.status !== 'idle' && state.status !== 'completed' && state.status !== 'failed';
  const hasFinished = state.status === 'completed' || state.status === 'failed';

  if (!isExecuting && !hasFinished) return null;

  const handleNewGoal = () => {
    dispatch({ type: 'RESET' });
  };

  return (
    <div className="w-full flex-1 flex flex-col pt-8">
      
      {/* Persistent Goal Header */}
      <motion.div
        layoutId="goal-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8 flex items-center justify-between"
      >
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-do-text-primary">
            {state.goal}
          </h2>
          {isExecuting && (
            <p className="text-do-text-tertiary mt-2">Working on your request...</p>
          )}
        </div>
      </motion.div>

      {/* Main Execution Area */}
      <motion.div 
        layout
        className="flex-1 flex flex-col max-w-4xl mx-auto w-full relative"
      >
        {isExecuting && (
          <motion.div
            key="execution-stage"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="w-full flex-1 flex flex-col gap-6"
          >
            <ThinkingPanel 
              steps={state.thinkingSteps.map(s => s.text)}
              visible={isExecuting && !state.pendingApproval}
            />
            
            <ReasoningPanel />
            
            <CurrentTask 
              task={state.currentTask || ''} 
              visible={isExecuting && !state.pendingApproval} 
            />
          </motion.div>
        )}

        {hasFinished && (
          <motion.div
            key="result-stage"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full flex-1"
          >
            <ResultPanel
              result={state.result}
              error={state.error}
              status={state.status}
              onNewGoal={handleNewGoal}
            />
          </motion.div>
        )}
      </motion.div>

      {/* Approval Overlay */}
      {state.pendingApproval && (
        <ApprovalDialog
          approval={state.pendingApproval}
          onRespond={respondToApproval}
        />
      )}
    </div>
  );
}
