import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, CheckCircle2, XCircle } from 'lucide-react';
import { cn } from '../utils/utils';
import type { Activity } from '../types';

interface Props {
  activities: Activity[];
  visible: boolean;
}

export default function ActivityFeed({ activities, visible }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [activities, autoScroll]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    if (scrollHeight - scrollTop - clientHeight > 10) {
      setAutoScroll(false);
    } else {
      setAutoScroll(true);
    }
  };

  if (!visible) return null;

  return (
    <div className="flex flex-col h-full bg-do-bg-secondary rounded-do-lg border border-do-bg-tertiary overflow-hidden relative">
      <div className="px-4 py-3 border-b border-do-bg-tertiary flex justify-between items-center bg-do-bg-secondary/50 backdrop-blur z-10">
        <h3 className="text-[11px] font-semibold text-do-text-secondary uppercase tracking-wider">
          Activity Log
        </h3>
        <span className="text-[10px] font-mono text-do-text-tertiary">LIVE_FEED</span>
      </div>
      
      <div 
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 space-y-4"
      >
        <AnimatePresence initial={false}>
          {activities.map((activity) => {
            const textLower = activity.text.toLowerCase();
            const isError = textLower.includes('error') || textLower.includes('failed');
            const isSuccess = textLower.includes('success') || textLower.includes('completed');
            
            return (
              <motion.div
                key={activity.id}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                className="relative pl-6 pb-2"
              >
                <div className="absolute left-[9px] top-[14px] bottom-[-22px] w-[2px] bg-do-bg-tertiary last:hidden" />
                
                <div className={cn(
                  "absolute left-0 top-1 w-5 h-5 rounded-full border-2 flex items-center justify-center bg-do-bg-secondary",
                  isError ? "border-do-danger" : isSuccess ? "border-do-success" : "border-do-active"
                )}>
                  {isError && <XCircle size={10} className="text-do-danger" />}
                  {isSuccess && <CheckCircle2 size={10} className="text-do-success" />}
                  {!isError && !isSuccess && <div className="w-1.5 h-1.5 rounded-full bg-do-active animate-pulse" />}
                </div>

                <div className="bg-do-bg-primary rounded-do-sm border border-do-bg-tertiary p-3 ml-2 shadow-sm">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-mono text-do-text-tertiary uppercase">
                      SYSTEM
                    </span>
                    <span className="text-[10px] text-do-text-secondary">
                      {new Date(activity.time).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' })}
                    </span>
                  </div>
                  <p className="text-[13px] text-do-text-primary leading-relaxed">
                    {activity.text}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {!autoScroll && (
          <motion.button
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            onClick={() => setAutoScroll(true)}
            className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-do-text-primary text-do-bg-primary px-3 py-1.5 rounded-do-full text-xs font-medium flex items-center gap-1.5 shadow-lg"
          >
            Resume Live Feed <ChevronDown size={14} />
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}
