import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useRef } from 'react';
import type { Activity } from '../../types';

interface Props {
  activities: Activity[];
  visible: boolean;
}

export default function ActivityTimeline({ activities, visible }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [activities]);

  if (!visible) return null;

  return (
    <div className="h-full flex flex-col">
      <h3 className="text-sm font-semibold text-do-text-primary mb-6 shrink-0">Activity Timeline</h3>
      
      <div 
        ref={containerRef}
        className="flex-1 overflow-y-auto pr-2 space-y-4"
      >
        <AnimatePresence initial={false}>
          {activities.map((activity) => (
            <motion.div
              key={activity.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex gap-4 relative"
            >
              {/* Timeline dot and line */}
              <div className="flex flex-col items-center">
                <div className="w-2 h-2 rounded-full bg-do-text-tertiary shrink-0 mt-1.5" />
                <div className="w-px h-full bg-do-bg-tertiary mt-2" />
              </div>
              
              <div className="pb-4">
                <span className="text-xs font-mono text-do-text-tertiary block mb-1">
                  {new Date(activity.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
                <p className="text-[14px] text-do-text-secondary">
                  {activity.text}
                </p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
