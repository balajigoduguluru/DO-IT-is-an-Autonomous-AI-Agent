import { motion, AnimatePresence } from 'framer-motion';

import type { ProgressInfo } from '../../types';

interface Props {
  progress: ProgressInfo | null;
  visible: boolean;
}

export default function ProgressTracker({ progress, visible }: Props) {
  if (!visible || progress === null) return null;

  const percentage = (progress.current / progress.total) * 100;
  
  // Instead of fake percentages, map progress to "Step X of Y"
  let stepText = '';
  if (percentage < 25) stepText = 'Step 1 of 4';
  else if (percentage < 50) stepText = 'Step 2 of 4';
  else if (percentage < 75) stepText = 'Step 3 of 4';
  else if (percentage < 100) stepText = 'Finalizing...';
  else stepText = 'Completed';

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="flex items-center gap-4 mt-6"
      >
        <div className="flex-1 h-1.5 bg-do-bg-tertiary rounded-full overflow-hidden">
          <motion.div 
            className="h-full bg-do-text-primary rounded-full"
            initial={{ width: '0%' }}
            animate={{ width: `${percentage}%` }}
            transition={{ ease: "circOut", duration: 0.5 }}
          />
        </div>
        <span className="text-sm font-medium text-do-text-secondary w-24 text-right">
          {stepText}
        </span>
      </motion.div>
    </AnimatePresence>
  );
}
