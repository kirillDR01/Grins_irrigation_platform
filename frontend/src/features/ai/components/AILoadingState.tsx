import { useState, useEffect } from 'react';

const loadingTexts = ['Analyzing...', 'Optimizing...', 'Generating...'];

export function AILoadingState() {
  const [textIndex, setTextIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setTextIndex((prev) => (prev + 1) % loadingTexts.length);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div 
      className="flex flex-col items-center justify-center py-12"
      data-testid="ai-loading-state"
    >
      <div className="w-12 h-12 border-4 border-teal-200 border-t-teal-500 rounded-full animate-spin" />
      <span className="text-slate-600 mt-4 animate-pulse">
        {loadingTexts[textIndex]}
      </span>
    </div>
  );
}
