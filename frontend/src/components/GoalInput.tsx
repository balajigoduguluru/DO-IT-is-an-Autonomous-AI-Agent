import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Paperclip, ArrowUp, Mic, Globe, Image as ImageIcon, X } from 'lucide-react';
import { cn } from '../utils/utils';
import { useExecutionContext } from '../context/ExecutionContext';

interface Props {
  onSubmit: (goal: string, attachments: { type: string; file: File }[], webSearchEnabled: boolean) => void;
  disabled: boolean;
  backendOnline: boolean;
}

export default function GoalInput({ onSubmit, disabled, backendOnline }: Props) {
  const [goal, setGoal] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [attachments, setAttachments] = useState<{ type: 'file' | 'image'; file: File }[]>([]);
  
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  
  const { state, devData } = useExecutionContext();

  const isExecuting = state.status !== 'idle' && state.status !== 'completed' && state.status !== 'failed';
  const hasFinished = state.status === 'completed' || state.status === 'failed';

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current && !isExecuting) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
    }
  }, [goal, isExecuting]);

  const handleSubmit = () => {
    if (!goal.trim() && attachments.length === 0) return;
    if (disabled || !backendOnline) return;
    
    onSubmit(goal.trim(), attachments, webSearchEnabled);
    setGoal('');
    setAttachments([]);
    setWebSearchEnabled(false);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, type: 'file' | 'image') => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files).map(file => ({ type, file }));
      setAttachments(prev => [...prev, ...newFiles]);
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <motion.div
      layout
      initial={false}
      animate={{
        y: isExecuting || hasFinished ? 0 : '30vh', // Start centered, move up
        scale: isExecuting || hasFinished ? 0.95 : 1,
      }}
      transition={{ type: 'spring', stiffness: 200, damping: 25 }}
      className={cn(
        "w-full max-w-3xl mx-auto z-10 relative",
        (isExecuting || hasFinished) ? "mb-8" : ""
      )}
    >
      <motion.div 
        layout
        className={cn(
          "relative bg-white dark:bg-do-bg-secondary rounded-[32px] transition-all duration-300 border",
          isFocused && !isExecuting 
            ? "border-do-bg-tertiary shadow-do-floating" 
            : "border-transparent shadow-do-soft",
          (isExecuting || hasFinished) ? "bg-transparent border-transparent shadow-none" : "p-3"
        )}
      >
        <AnimatePresence mode="wait">
          {!isExecuting && !hasFinished ? (
            <motion.div 
              key="input-mode"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="relative"
            >
              {/* Attachments Display */}
              {attachments.length > 0 && (
                <div className="flex flex-wrap gap-2 px-6 pt-4 pb-2">
                  {attachments.map((att, idx) => (
                    <div key={idx} className="flex items-center gap-2 bg-do-bg-tertiary px-3 py-1.5 rounded-full text-sm font-medium text-do-text-primary">
                      {att.type === 'image' ? <ImageIcon size={14} /> : <Paperclip size={14} />}
                      <span className="max-w-[150px] truncate">{att.file.name}</span>
                      <button onClick={() => removeAttachment(idx)} className="hover:bg-black/10 dark:hover:bg-white/10 p-0.5 rounded-full transition-colors">
                        <X size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <textarea
                ref={inputRef}
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setIsFocused(false)}
                onKeyDown={handleKeyDown}
                placeholder="Hello, what's on your mind?"
                disabled={disabled}
                rows={1}
                className="w-full bg-transparent text-do-text-primary text-xl placeholder:text-do-text-tertiary resize-none outline-none py-4 px-6 min-h-[70px] max-h-[200px]"
                aria-label="Mission Goal"
              />
              
              {/* Bottom Actions Bar */}
              <div className="flex items-center justify-between px-4 pt-2 pb-2">
                <div className="flex items-center gap-2">
                  <input type="file" ref={fileInputRef} className="hidden" multiple onChange={(e) => handleFileChange(e, 'file')} />
                  <input type="file" ref={imageInputRef} className="hidden" accept="image/*" multiple onChange={(e) => handleFileChange(e, 'image')} />
                  
                  <button onClick={() => fileInputRef.current?.click()} className="p-2 text-do-text-tertiary hover:text-do-text-primary hover:bg-do-bg-tertiary rounded-full transition-colors" title="Attach file">
                    <Paperclip size={20} strokeWidth={2} />
                  </button>
                  <button onClick={() => setWebSearchEnabled(!webSearchEnabled)} className={cn("p-2 rounded-full transition-colors", webSearchEnabled ? "text-do-active bg-do-active/10" : "text-do-text-tertiary hover:text-do-text-primary hover:bg-do-bg-tertiary")} title="Web search">
                    <Globe size={20} strokeWidth={2} />
                  </button>
                  <button onClick={() => imageInputRef.current?.click()} className="p-2 text-do-text-tertiary hover:text-do-text-primary hover:bg-do-bg-tertiary rounded-full transition-colors" title="Upload image">
                    <ImageIcon size={20} strokeWidth={2} />
                  </button>
                </div>
                
                <div className="flex items-center gap-4">
                  <button className="p-2 text-do-text-tertiary hover:text-do-text-primary hover:bg-do-bg-tertiary rounded-full transition-colors" title="Voice input">
                    <Mic size={20} strokeWidth={2} />
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={(!goal.trim() && attachments.length === 0) || disabled || !backendOnline}
                    className="flex items-center justify-center w-10 h-10 bg-do-accent text-white rounded-full hover:scale-105 disabled:opacity-50 disabled:hover:scale-100 transition-all shadow-md"
                  >
                    <ArrowUp size={20} strokeWidth={2.5} />
                  </button>
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div 
              key="header-mode"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center justify-between"
            >
              <div>
                <h1 className="text-3xl font-semibold tracking-tight text-do-text-primary">
                  {goal}
                </h1>
                <p className="text-sm text-do-text-secondary mt-1 font-mono">
                  MISSION ID: {devData.sessionId?.split('-')[0].toUpperCase() || 'UNKNOWN'}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  );
}
