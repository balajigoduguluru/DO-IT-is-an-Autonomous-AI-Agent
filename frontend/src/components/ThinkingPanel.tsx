import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface Props {
  steps: string[];
  visible: boolean;
}

export default function ThinkingPanel({ steps, visible }: Props) {
  const [currentText, setCurrentText] = useState('');
  
  useEffect(() => {
    if (!visible || steps.length === 0) {
      setCurrentText('');
      return;
    }
    
    // Smooth natural typing simulation for the latest step
    const latestStep = steps[steps.length - 1];
    let i = 0;
    setCurrentText('');
    
    const intervalId = setInterval(() => {
      setCurrentText(latestStep.substring(0, i));
      i++;
      if (i > latestStep.length) {
        clearInterval(intervalId);
      }
    }, 15); // Fast, fluid typing
    
    return () => clearInterval(intervalId);
  }, [steps, visible]);

  if (!visible) return null;

  return (
    <AnimatePresence>
      {steps.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="mb-8 flex justify-center"
        >
          <div className="relative overflow-hidden w-full max-w-2xl text-center">
            {/* Fade edges to indicate ephemeral thought */}
            <div className="absolute inset-y-0 left-0 w-8 bg-gradient-to-r from-do-bg-primary to-transparent z-10" />
            <div className="absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-do-bg-primary to-transparent z-10" />
            
            <p className="text-do-text-secondary font-mono text-sm whitespace-nowrap overflow-hidden">
              <span className="opacity-50">❯ </span>
              {currentText}
              <motion.span
                animate={{ opacity: [1, 0] }}
                transition={{ repeat: Infinity, duration: 0.8 }}
                className="inline-block w-2 h-3.5 ml-1 bg-do-text-secondary align-middle"
              />
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
