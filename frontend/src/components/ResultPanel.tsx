import { motion } from 'framer-motion';
import { AlertCircle, CheckCircle2, RotateCcw, Copy, Download } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../utils/utils';
import { MarkdownRenderer } from './MarkdownRenderer';

interface Props {
  result: string | null;
  error: string | null;
  status: string;
  onNewGoal: () => void;
}

export default function ResultPanel({ result, error, status, onNewGoal }: Props) {
  const isError = status === 'failed';

  const handleCopy = () => {
    if (result) {
      navigator.clipboard.writeText(result);
      toast.success('Result copied to clipboard');
    }
  };

  const handleExport = () => {
    if (result) {
      const blob = new Blob([result], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `do-it-result-${new Date().getTime()}.md`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Result exported as Markdown');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98, y: 20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 200, damping: 25 }}
      className="bg-white dark:bg-do-bg-secondary rounded-[32px] border border-do-bg-tertiary shadow-do-soft overflow-hidden mt-6"
    >
      <div className={cn(
        "px-8 py-6 border-b",
        isError ? "bg-red-50 dark:bg-red-900/10 border-red-100 dark:border-red-900/20" : "border-do-bg-tertiary"
      )}>
        <div className="flex items-center gap-3">
          {isError ? (
            <AlertCircle size={24} className="text-red-500" />
          ) : (
            <CheckCircle2 size={24} className="text-emerald-500" />
          )}
          <h2 className="text-xl font-semibold text-do-text-primary">
            {isError ? 'I ran into a problem' : 'Here is the result'}
          </h2>
        </div>
        {isError && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400 font-medium">
            {error || 'Unknown execution failure'}
          </p>
        )}
      </div>

      <div className="p-8">
        <div className="max-w-none text-do-text-secondary leading-relaxed">
          {result ? (
            <MarkdownRenderer content={result} />
          ) : !isError && (
            <div className="text-sm italic opacity-50">No text content provided in result.</div>
          )}
        </div>

        <div className="mt-10 flex justify-between items-center">
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              disabled={!result}
              className="flex items-center gap-2 px-4 py-2 text-[14px] font-medium text-do-text-secondary hover:text-do-text-primary hover:bg-do-bg-tertiary rounded-xl transition-colors disabled:opacity-50"
            >
              <Copy size={16} />
              Copy
            </button>
            <button
              onClick={handleExport}
              disabled={!result}
              className="flex items-center gap-2 px-4 py-2 text-[14px] font-medium text-do-text-secondary hover:text-do-text-primary hover:bg-do-bg-tertiary rounded-xl transition-colors disabled:opacity-50"
            >
              <Download size={16} />
              Export
            </button>
          </div>
          <button
            onClick={onNewGoal}
            className="flex items-center gap-2 px-6 py-2.5 text-[14px] font-medium text-do-text-primary bg-[#F8FAFC] dark:bg-do-bg-tertiary hover:bg-[#F1F5F9] dark:hover:bg-do-bg-secondary border border-do-bg-tertiary rounded-xl transition-all"
          >
            <RotateCcw size={16} />
            Start New Task
          </button>
        </div>
      </div>
    </motion.div>
  );
}
