import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';

interface Props {
  task: string;
  visible: boolean;
}

export default function CurrentTask({ task, visible }: Props) {
  if (!visible || !task) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex items-center gap-3 text-do-text-secondary"
    >
      <Loader2 size={18} className="animate-spin text-do-text-tertiary" />
      <span className="text-lg font-medium">{task}</span>
    </motion.div>
  );
}
