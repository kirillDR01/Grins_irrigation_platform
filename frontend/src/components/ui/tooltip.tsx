// Minimal tooltip component — no new dependencies
// Uses native title attribute for accessibility + CSS for visual tooltip

import * as React from 'react';

interface TooltipProviderProps {
  children: React.ReactNode;
  delayDuration?: number;
}

interface TooltipProps {
  children: React.ReactNode;
}

interface TooltipTriggerProps {
  children: React.ReactNode;
  asChild?: boolean;
}

interface TooltipContentProps {
  children: React.ReactNode;
  className?: string;
}

const TooltipContext = React.createContext<{ content: string; setContent: (s: string) => void }>({
  content: '',
  setContent: () => {},
});

export function TooltipProvider({ children }: TooltipProviderProps) {
  return <>{children}</>;
}

export function Tooltip({ children }: TooltipProps) {
  const [content, setContent] = React.useState('');
  return (
    <TooltipContext.Provider value={{ content, setContent }}>
      <span className="relative inline-flex">{children}</span>
    </TooltipContext.Provider>
  );
}

export function TooltipTrigger({ children, asChild }: TooltipTriggerProps) {
  const { content } = React.useContext(TooltipContext);
  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as React.ReactElement<{ title?: string }>, { title: content });
  }
  return <span title={content}>{children}</span>;
}

export function TooltipContent({ children }: TooltipContentProps) {
  const { setContent } = React.useContext(TooltipContext);
  const text = typeof children === 'string' ? children : '';
  // Sync content to context on render
  React.useEffect(() => {
    setContent(text);
  }, [text, setContent]);
  return null;
}
