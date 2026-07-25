import { motion, AnimatePresence } from 'framer-motion';
import type { ProgressInfo } from '../types';

interface Props {
  progress: ProgressInfo | null;
  visible: boolean;
}

export default function ProgressBar({ progress, visible }: Props) {
  if (!visible || !progress) return null;

  const percent = (progress.current / progress.total) * 100;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="fixed top-0 left-0 right-0 z-50 pointer-events-none"
      >
        <div className="h-[2px] w-full bg-transparent overflow-hidden">
          <motion.div
            className="h-full bg-do-active shadow-[0_0_10px_rgba(10,132,255,0.7)]"
            initial={{ width: '0%' }}
            animate={{ width: `${percent}%` }}
            transition={{ type: 'spring', stiffness: 100, damping: 20 }}
          />
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
