import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Code, FileText, Lightbulb, Globe, Settings, Terminal, Zap, Palette } from 'lucide-react';
import GoalInput from '../GoalInput';
import { useExecutionContext } from '../../context/ExecutionContext';
import { useAgentExecution } from '../../hooks/useAgentExecution';
import { useUser } from '../../hooks/useUser';

const ALL_QUICK_STARTS = [
  { icon: Code, title: 'Write a script', desc: 'Write a TypeScript script that fetches data from an API and processes it.', color: 'orange' },
  { icon: FileText, title: 'Analyze document', desc: 'Analyze this document and provide a comprehensive summary with key insights.', color: 'blue' },
  { icon: Lightbulb, title: 'Brainstorm ideas', desc: 'Brainstorm 10 innovative product ideas for AI-powered tools in 2025.', color: 'yellow' },
  { icon: Globe, title: 'Research topic', desc: 'Provide a comprehensive research overview on quantum computing and its applications.', color: 'emerald' },
  { icon: Settings, title: 'Configure server', desc: 'Generate an optimized nginx.conf for a Node.js API with rate limiting.', color: 'gray' },
  { icon: Terminal, title: 'CLI Tool', desc: 'Build a rust-based CLI tool to convert JSON files to CSV format.', color: 'indigo' },
  { icon: Zap, title: 'Optimize Code', desc: 'Review and optimize this React component to prevent unnecessary re-renders.', color: 'amber' },
  { icon: Palette, title: 'Design System', desc: 'Create a JSON schema mapping out typography and color tokens for a new brand.', color: 'pink' },
];

const getColorClasses = (color: string) => {
  const map: Record<string, string> = {
    orange: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400',
    blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    yellow: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400',
    emerald: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400',
    gray: 'bg-gray-100 dark:bg-gray-800/30 text-gray-600 dark:text-gray-400',
    indigo: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400',
    amber: 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400',
    pink: 'bg-pink-100 dark:bg-pink-900/30 text-pink-600 dark:text-pink-400',
  };
  return map[color] || map.blue;
};

export function LandingView() {
  const { state } = useExecutionContext();
  const { submitGoal } = useAgentExecution();
  const { userName } = useUser();
  
  const [dynamicStarts, setDynamicStarts] = useState(ALL_QUICK_STARTS.slice(0, 4));

  useEffect(() => {
    // Randomize quick starts on load to feel dynamic
    const shuffled = [...ALL_QUICK_STARTS].sort(() => 0.5 - Math.random());
    setDynamicStarts(shuffled.slice(0, 4));
  }, []);

  const isExecuting = state.status !== 'idle' && state.status !== 'completed' && state.status !== 'failed';
  const hasFinished = state.status === 'completed' || state.status === 'failed';

  if (isExecuting || hasFinished) return null;

  return (
    <div className="flex-1 flex flex-col justify-center max-w-4xl mx-auto w-full relative z-10 py-12 px-4 h-full">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20, filter: 'blur(10px)' }}
        transition={{ duration: 0.3 }}
        className="w-full text-center mb-10"
      >
        <h1 className="text-5xl font-medium tracking-tight text-do-text-primary mb-2">
          Good afternoon, {userName}
        </h1>
      </motion.div>

      <GoalInput
        onSubmit={submitGoal}
        disabled={false}
        backendOnline={state.backendStatus !== 'offline'}
      />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 20, filter: 'blur(10px)' }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="mt-12"
      >
        <h3 className="text-xs font-bold text-do-text-tertiary uppercase tracking-widest mb-4">Quick Start</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {dynamicStarts.map((item, idx) => (
            <button 
              key={idx}
              onClick={() => submitGoal(item.desc)}
              className="bg-white dark:bg-do-bg-secondary p-5 rounded-[24px] text-left border border-transparent hover:border-do-bg-tertiary hover:shadow-do-soft transition-all group"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className={`p-2 rounded-xl ${getColorClasses(item.color)}`}>
                  <item.icon size={16} />
                </div>
                <h4 className="font-semibold text-do-text-primary">{item.title}</h4>
              </div>
              <p className="text-[13px] text-do-text-secondary">{item.desc}</p>
            </button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
