/**
 * Morning Briefing component.
 * Displays personalized daily summary with overnight requests, schedule, and pending actions.
 * Redesigned with amber alert styling per UI redesign spec.
 */

import { Link } from 'react-router-dom';
import { Sun, Moon, Sunrise, Sunset, ArrowRight, AlertCircle } from 'lucide-react';
import { useJobsByStatus } from '@/features/dashboard/hooks';

function getGreeting(): { text: string; icon: typeof Sun } {
  const hour = new Date().getHours();
  if (hour < 6) return { text: 'Good night', icon: Moon };
  if (hour < 12) return { text: 'Good morning', icon: Sunrise };
  if (hour < 18) return { text: 'Good afternoon', icon: Sun };
  if (hour < 22) return { text: 'Good evening', icon: Sunset };
  return { text: 'Good night', icon: Moon };
}

export function MorningBriefing() {
  const { data: jobsByStatus } = useJobsByStatus();

  const greeting = getGreeting();
  const overnightRequests = jobsByStatus?.requested ?? 0;

  // Only show if there are overnight requests
  if (overnightRequests === 0) {
    return null;
  }

  return (
    <div
      data-testid="morning-briefing"
      className="bg-white p-4 rounded-xl shadow-sm border-l-4 border-amber-400"
    >
      <div className="flex items-start gap-4">
        {/* Icon container - amber styling */}
        <div className="bg-amber-100 p-2 rounded-full text-amber-600 flex-shrink-0">
          <AlertCircle className="h-5 w-5" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <h4 className="text-slate-800 font-medium" data-testid="greeting">
            {greeting.text}, Viktor! You have {overnightRequests} overnight request{overnightRequests !== 1 ? 's' : ''}
          </h4>

          {/* Description */}
          <p className="text-slate-500 text-sm mt-1">
            {overnightRequests} job{overnightRequests !== 1 ? 's' : ''} need{overnightRequests === 1 ? 's' : ''} categorization before scheduling
          </p>
        </div>

        {/* Action button - amber styling */}
        <Link
          to="/jobs?status=requested"
          data-testid="review-requests-btn"
          className="text-amber-600 bg-amber-50 hover:bg-amber-100 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1 flex-shrink-0"
        >
          Review
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
  );
}
