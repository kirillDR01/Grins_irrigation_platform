import { useEffect, useState } from 'react';

interface AIStreamingTextProps {
  text: string;
  isStreaming: boolean;
  speed?: number;
}

export function AIStreamingText({ text, isStreaming, speed = 20 }: AIStreamingTextProps) {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    if (!isStreaming) {
      setDisplayedText(text);
      return;
    }

    let currentIndex = 0;
    const interval = setInterval(() => {
      if (currentIndex < text.length) {
        setDisplayedText(text.slice(0, currentIndex + 1));
        currentIndex++;
      } else {
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, isStreaming, speed]);

  return (
    <div data-testid="ai-streaming-text" className="text-slate-700 leading-relaxed whitespace-pre-wrap">
      {displayedText}
      {isStreaming && displayedText.length < text.length && (
        <span className="inline-block w-2 h-5 bg-teal-500 animate-pulse ml-1">▊</span>
      )}
    </div>
  );
}
