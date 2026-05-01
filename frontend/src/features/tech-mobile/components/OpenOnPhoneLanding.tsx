import { Smartphone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/features/auth/components/AuthProvider';

/**
 * Landing surface shown to a tech who lands on `/tech` from a viewport
 * wider than the phone-only breakpoint. Keeps the tech off admin UI
 * (which is desktop-shaped) and offers a clear path back to login.
 */
export function OpenOnPhoneLanding() {
  const { logout } = useAuth();

  return (
    <div className="min-h-screen flex items-center justify-center px-6 bg-slate-50">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg border border-slate-200 p-8 text-center">
        <div className="w-14 h-14 mx-auto mb-5 rounded-2xl bg-teal-500/10 flex items-center justify-center">
          <Smartphone className="w-7 h-7 text-teal-600" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mb-2">
          Open this on your phone.
        </h1>
        <p className="text-slate-600 leading-relaxed mb-6">
          The technician view is designed for phone-sized screens. Sign in
          from your phone to continue.
        </p>
        <Button
          variant="outline"
          className="w-full"
          onClick={() => {
            void logout();
          }}
          data-testid="logout-btn"
        >
          Sign out
        </Button>
      </div>
    </div>
  );
}
