import { useEffect } from 'react';
import { Code2 } from 'lucide-react';
import { useExecutionContext } from '../context/ExecutionContext';
import { cn } from '../utils/utils';

export function TopNav() {
  const { state, dispatch } = useExecutionContext();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        dispatch({ type: 'TOGGLE_DEV_MODE' });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [dispatch]);

  return (
    <header className="h-16 flex items-center justify-end px-6 relative z-10 w-full">
      <button 
        onClick={() => dispatch({ type: 'TOGGLE_DEV_MODE' })}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono border transition-all",
          state.devMode 
            ? "bg-do-text-primary text-white border-transparent shadow-md" 
            : "bg-white dark:bg-do-bg-secondary text-do-text-tertiary border-do-bg-tertiary hover:border-do-text-tertiary hover:text-do-text-secondary"
        )}
        title="Toggle Developer Mode (Cmd+K)"
      >
        <Code2 size={14} />
        DEV MODE
      </button>
    </header>
  );
}
