import { motion } from 'framer-motion';
import { Layers, AlertCircle, RotateCcw } from 'lucide-react';
import { cn } from '../utils/utils';

interface Props {
  task: string;
  visible: boolean;
}

export default function CurrentTask({ task, visible }: Props) {
  // In a real implementation, we would pass the full DAG state here.
  // For now, we simulate the "LiveDAG" visual using the single current task string 
  // to match the requested component structure without changing backend APIs.

  if (!visible || !task) return null;

  // Mock parsing to demonstrate graph mutation handling if task changes or fails
  const isFallback = task.toLowerCase().includes('fallback') || task.toLowerCase().includes('train');
  const isFailed = task.toLowerCase().includes('failed');

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="mb-12 relative flex justify-center"
    >
      {/* Mock DAG Node Card */}
      <motion.div
        layout
        className={cn(
          "relative bg-do-bg-secondary rounded-do-md border shadow-sm w-72 overflow-hidden",
          isFallback ? "border-do-warning" : isFailed ? "border-do-danger" : "border-do-bg-tertiary"
        )}
        animate={isFailed ? { x: [-4, 4, -4, 4, 0] } : {}} // Failure shake
        transition={isFailed ? { duration: 0.3 } : {}}
      >
        {/* Breathing glow for active tasks */}
        {!isFailed && !isFallback && (
          <motion.div
            className="absolute inset-0 bg-do-active/5 z-0"
            animate={{ opacity: [0.3, 0.7, 0.3] }}
            transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
          />
        )}

        <div className="relative z-10 p-4 flex items-start gap-3">
          <div className={cn(
            "p-2 rounded-do-sm shrink-0",
            isFallback ? "bg-do-warning/10 text-do-warning" : 
            isFailed ? "bg-do-danger/10 text-do-danger" : 
            "bg-do-bg-tertiary text-do-text-secondary"
          )}>
            {isFallback ? <RotateCcw size={16} /> : 
             isFailed ? <AlertCircle size={16} /> : 
             <Layers size={16} />}
          </div>
          
          <div className="min-w-0 flex-1">
            <div className="text-[10px] font-mono font-medium tracking-wider mb-1 uppercase text-do-text-tertiary">
              {isFallback ? 'MUTATION / FALLBACK' : 'EXECUTING NODE'}
            </div>
            <div className="text-sm font-medium text-do-text-primary truncate">
              {task}
            </div>
          </div>
        </div>

        {/* Micro progress bar attached to bottom edge */}
        {!isFailed && (
          <div className="h-[2px] w-full bg-do-bg-tertiary absolute bottom-0 left-0">
            <motion.div
              className={cn("h-full", isFallback ? "bg-do-warning" : "bg-do-active")}
              initial={{ width: '0%' }}
              animate={{ width: '75%' }} // Simulated progress
              transition={{ duration: 2, ease: "easeOut" }}
            />
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
