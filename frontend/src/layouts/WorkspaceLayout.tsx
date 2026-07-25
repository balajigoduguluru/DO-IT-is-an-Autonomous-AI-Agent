import { motion } from 'framer-motion';
import { Sidebar } from './Sidebar';
import { TopNav } from './TopNav';
import { useExecutionContext } from '../context/ExecutionContext';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';

export function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  useKeyboardShortcuts();
  // Using execution state to know if we're active
  const { state } = useExecutionContext();
  const isExecuting = state.status !== 'idle' && state.status !== 'completed' && state.status !== 'failed';

  return (
    <div className="flex h-screen bg-do-bg-primary overflow-hidden font-sans">
      <Sidebar />
      <main className="flex-1 flex flex-col relative h-full bg-gradient-to-br from-[#FFF5F0] via-[#FFF0E8] to-[#FFE5D9] dark:from-[#110C0A] dark:via-[#1A1412] dark:to-[#221815]">
        <TopNav />
        
        {/* Main Stage & Context Panel */}
        <div className="flex-1 overflow-hidden flex relative">
          
          {/* Main Stage (Center) */}
          <motion.div 
            className="flex-1 overflow-y-auto px-12 py-8 relative"
            layout
          >
            <div className="max-w-4xl mx-auto h-full flex flex-col relative">
               {children}
            </div>
          </motion.div>

          {/* Context Panel (Right side - sliding in when active) */}
          <motion.div
            initial={{ width: 0, opacity: 0, x: 20 }}
            animate={{ 
              width: isExecuting || state.status === 'completed' ? 320 : 0, 
              opacity: isExecuting || state.status === 'completed' ? 1 : 0,
              x: isExecuting || state.status === 'completed' ? 0 : 20 
            }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="border-l border-do-bg-tertiary bg-do-bg-secondary/50 backdrop-blur-xl hidden lg:block overflow-hidden flex-shrink-0 relative"
          >
            <div className="w-[320px] h-full p-6">
              {/* Timeline goes here, we'll implement it later */}
              <div id="timeline-portal" className="h-full" />
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}
