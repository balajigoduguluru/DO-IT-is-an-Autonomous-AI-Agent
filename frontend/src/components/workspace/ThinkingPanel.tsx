import { motion } from 'framer-motion';
import { Check, Loader2 } from 'lucide-react';
import { cn } from '../../utils/utils';

interface Props {
  steps: string[];
  visible: boolean;
}

export default function ThinkingPanel({ steps, visible }: Props) {
  if (!visible) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="bg-white dark:bg-do-bg-secondary rounded-[24px] p-6 shadow-do-soft border border-do-bg-tertiary"
    >
      <div className="space-y-4">
        {steps.map((step, idx) => {
          // The last step is usually the active one
          const isLast = idx === steps.length - 1;
          
          return (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className={cn(
                "flex items-center gap-3",
                isLast ? "text-do-text-primary font-medium" : "text-do-text-secondary"
              )}
            >
              <div className="shrink-0 w-6 h-6 flex items-center justify-center">
                {isLast ? (
                  <Loader2 size={16} className="animate-spin text-do-text-tertiary" />
                ) : (
                  <Check size={16} className="text-do-success" />
                )}
              </div>
              <span className="text-[15px]">{step}</span>
            </motion.div>
          );
        })}
        {steps.length === 0 && (
          <div className="flex items-center gap-3 text-do-text-secondary">
             <div className="shrink-0 w-6 h-6 flex items-center justify-center">
                <Loader2 size={16} className="animate-spin text-do-text-tertiary" />
             </div>
             <span className="text-[15px]">Initializing agent...</span>
          </div>
        )}
      </div>
    </motion.div>
  );
}
