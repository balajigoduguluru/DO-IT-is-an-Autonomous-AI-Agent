import { useState, useEffect } from 'react';

export interface HistoryItem {
  id: string;
  title: string;
  desc: string;
  timestamp: number;
}

export function useHistory() {
  const [history, setHistory] = useState<HistoryItem[]>([]);

  useEffect(() => {
    const saved = localStorage.getItem('do_it_history');
    if (saved) {
      try {
        setHistory(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to parse history', e);
      }
    }
  }, []);

  const addHistoryItem = (title: string, desc: string) => {
    const newItem: HistoryItem = {
      id: Date.now().toString(),
      title,
      desc,
      timestamp: Date.now(),
    };
    
    setHistory(prev => {
      const updated = [newItem, ...prev].slice(0, 50); // Keep last 50
      localStorage.setItem('do_it_history', JSON.stringify(updated));
      return updated;
    });
  };

  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem('do_it_history');
  };

  return { history, addHistoryItem, clearHistory };
}
