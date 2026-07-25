import { motion } from 'framer-motion';
import { HelpCircle, CheckCircle2 } from 'lucide-react';
import { useExecutionContext } from '../../context/ExecutionContext';
import { useMemo } from 'react';

export default function ReasoningPanel() {
  const { state } = useExecutionContext();

  if (state.status === 'idle' || !state.currentTask) return null;

  // Generate dynamic reasoning based on the current task and state
  const reasons = useMemo(() => {
    const list = [];
    
    if (state.currentTask) {
      if (state.currentTask.toLowerCase().includes('plan')) {
        list.push('Breaking down the goal into executable sub-tasks.');
        list.push('Evaluating dependencies to ensure optimal execution order.');
      } else if (state.currentTask.toLowerCase().includes('search') || state.currentTask.toLowerCase().includes('gather')) {
        list.push('Fetching real-time data to ensure accuracy.');
        list.push('Filtering out irrelevant information to save processing time.');
      } else if (state.currentTask.toLowerCase().includes('execut') || state.currentTask.toLowerCase().includes('run')) {
        list.push('Executing the planned steps sequentially.');
        list.push('Monitoring for any unexpected errors during execution.');
      } else if (state.currentTask.toLowerCase().includes('finaliz')) {
        list.push('Aggregating all gathered data into a cohesive result.');
        list.push('Verifying that the final output satisfies the original goal.');
      } else {
        list.push(`Actively processing the "${state.currentTask}" phase.`);
        list.push('Matching the core intent of your request.');
      }
    }
    
    return list;
  }, [state.currentTask]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-6 p-6 bg-[#F8FAFC] dark:bg-do-bg-tertiary rounded-[24px] border border-blue-100 dark:border-transparent"
    >
      <div className="flex items-center gap-2 mb-4">
        <HelpCircle size={18} className="text-blue-500" />
        <h4 className="font-semibold text-do-text-primary text-[15px]">Why this approach?</h4>
      </div>
      
      <div className="space-y-3">
        {reasons.map((reason, idx) => (
          <div key={idx} className="flex items-start gap-3">
            <CheckCircle2 size={16} className="text-blue-500 mt-0.5 shrink-0" />
            <p className="text-[14px] text-do-text-secondary leading-snug">
              {reason}
            </p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
