import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, X, Server, Activity, Database, Key } from 'lucide-react';
import { useExecutionContext } from '../context/ExecutionContext';

export default function DeveloperOverlay() {
  const { state, devData, dispatch } = useExecutionContext();

  if (!state.devMode) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex justify-end bg-black/20 backdrop-blur-sm"
      >
        <motion.div
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="w-full max-w-lg bg-[#111111] h-full shadow-2xl border-l border-[#222] flex flex-col text-[#EAEAEA]"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-[#222]">
            <div className="flex items-center gap-2">
              <Terminal size={18} className="text-do-active" />
              <h2 className="font-mono text-sm font-semibold tracking-wider">Developer Console</h2>
            </div>
            <button
              onClick={() => dispatch({ type: 'TOGGLE_DEV_MODE' })}
              className="p-1 hover:bg-[#222] rounded-md transition-colors"
            >
              <X size={18} className="text-[#888] hover:text-white" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-6">
            
            {/* System Status */}
            <section>
              <h3 className="text-[11px] font-mono text-[#888] uppercase tracking-widest mb-3 flex items-center gap-2">
                <Server size={12} /> System Status
              </h3>
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-[#1A1A1A] p-3 rounded-md border border-[#333]">
                  <div className="text-[10px] text-[#888] font-mono mb-1">BACKEND</div>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${state.backendStatus === 'online' ? 'bg-emerald-500' : 'bg-red-500'}`} />
                    <span className="text-xs font-mono">{state.backendStatus.toUpperCase()}</span>
                  </div>
                </div>
                <div className="bg-[#1A1A1A] p-3 rounded-md border border-[#333]">
                  <div className="text-[10px] text-[#888] font-mono mb-1">SESSION ID</div>
                  <div className="flex items-center gap-2">
                    <Key size={12} className="text-[#555]" />
                    <span className="text-xs font-mono text-blue-400 truncate">
                      {devData.sessionId || 'None'}
                    </span>
                  </div>
                </div>
              </div>
            </section>

            {/* Execution Metrics */}
            <section>
              <h3 className="text-[11px] font-mono text-[#888] uppercase tracking-widest mb-3 flex items-center gap-2">
                <Activity size={12} /> Execution Metrics
              </h3>
              <div className="bg-[#1A1A1A] rounded-md border border-[#333] divide-y divide-[#333]">
                <div className="flex justify-between p-3">
                  <span className="text-xs font-mono text-[#888]">LLM Calls</span>
                  <span className="text-xs font-mono">{devData.llmCalls}</span>
                </div>
                <div className="flex justify-between p-3">
                  <span className="text-xs font-mono text-[#888]">Tool Calls</span>
                  <span className="text-xs font-mono">{devData.toolCalls}</span>
                </div>
                <div className="flex justify-between p-3">
                  <span className="text-xs font-mono text-[#888]">Active Agent</span>
                  <span className="text-xs font-mono text-orange-400">{devData.currentAgent || 'None'}</span>
                </div>
              </div>
            </section>

            {/* Raw Websocket Feed */}
            <section>
              <h3 className="text-[11px] font-mono text-[#888] uppercase tracking-widest mb-3 flex items-center gap-2">
                <Database size={12} /> Raw Event Stream
              </h3>
              <div className="bg-black border border-[#333] rounded-md h-64 overflow-y-auto p-2 font-mono text-[10px] space-y-1">
                {devData.websocketEvents.length === 0 ? (
                  <div className="text-[#555] p-2">Waiting for events...</div>
                ) : (
                  devData.websocketEvents.slice().reverse().map((evt: any, i) => (
                    <div key={i} className="text-[#888] break-all border-b border-[#222] pb-1">
                      <span className="text-emerald-500">[{new Date().toLocaleTimeString()}]</span> {JSON.stringify(evt)}
                    </div>
                  ))
                )}
              </div>
            </section>

          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
