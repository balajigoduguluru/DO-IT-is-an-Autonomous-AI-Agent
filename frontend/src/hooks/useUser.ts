import { useState, useEffect } from 'react';

export function useUser() {
  const [userName, setUserName] = useState<string>('');

  useEffect(() => {
    const storedName = localStorage.getItem('userName');
    if (storedName) {
      setUserName(storedName);
    } else {
      // Small timeout to allow initial render before blocking with prompt
      setTimeout(() => {
        const name = window.prompt("Welcome to DO IT. Please enter your name:");
        if (name && name.trim()) {
          const finalName = name.trim();
          localStorage.setItem('userName', finalName);
          setUserName(finalName);
        } else {
          localStorage.setItem('userName', 'Commander');
          setUserName('Commander');
        }
      }, 500);
    }
  }, []);

  return {
    userName: userName || 'Loading...',
    email: userName ? `${userName.toLowerCase().replace(/\s+/g, '.')}@doit.ai` : 'loading...'
  };
}
