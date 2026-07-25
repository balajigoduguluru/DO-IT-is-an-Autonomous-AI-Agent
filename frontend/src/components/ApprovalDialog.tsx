import { motion, AnimatePresence } from 'framer-motion';
import { Shield, ArrowRight } from 'lucide-react';
import type { ApprovalInfo } from '../types';

interface Props {
  approval: ApprovalInfo | null;
  onRespond: (approved: boolean) => void;
}

export default function ApprovalDialog({ approval, onRespond }: Props) {
  if (!approval) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-white/40 dark:bg-black/40 backdrop-blur-md"
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="relative bg-white dark:bg-do-bg-secondary rounded-[32px] shadow-do-lg border border-do-bg-tertiary w-full max-w-lg p-8"
        >
          <div className="flex items-center gap-4 mb-6">
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-2xl">
              <Shield size={24} />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-do-text-primary">I need your confirmation</h2>
              <p className="text-do-text-secondary text-sm">Before I proceed with the following action</p>
            </div>
          </div>
          
          <div className="bg-[#F8FAFC] dark:bg-do-bg-tertiary rounded-2xl p-6 mb-8 border border-blue-100 dark:border-transparent">
            <p className="text-[15px] font-medium text-do-text-primary leading-relaxed">
              {approval.action}
            </p>
          </div>

          <div className="flex gap-4">
            <button
              onClick={() => onRespond(false)}
              className="flex-1 py-4 text-[15px] font-medium text-do-text-secondary hover:bg-do-bg-tertiary rounded-2xl transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => onRespond(true)}
              className="flex-1 py-4 bg-do-text-primary text-white text-[15px] font-medium rounded-2xl flex justify-center items-center gap-2 hover:opacity-90 transition-opacity"
            >
              Proceed <ArrowRight size={18} />
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
