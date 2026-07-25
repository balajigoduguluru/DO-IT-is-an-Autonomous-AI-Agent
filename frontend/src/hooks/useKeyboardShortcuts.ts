import { useEffect } from 'react';
import { useExecutionContext } from '../context/ExecutionContext';

export function useKeyboardShortcuts() {
  const { dispatch } = useExecutionContext();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Toggle Developer Mode with Cmd/Ctrl + K
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        dispatch({ type: 'TOGGLE_DEV_MODE' });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [dispatch]);
}
