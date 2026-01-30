import { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
}

export function PageHeader({ title, description, action }: PageHeaderProps) {
  return (
    <div
      className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-6"
      data-testid="page-header"
    >
      <div>
        <h1 className="text-2xl font-bold text-slate-800" data-testid="page-title">
          {title}
        </h1>
        {description && (
          <div className="text-slate-500 mt-1" data-testid="page-description">
            {description}
          </div>
        )}
      </div>
      {action && <div data-testid="page-header-action">{action}</div>}
    </div>
  );
}
