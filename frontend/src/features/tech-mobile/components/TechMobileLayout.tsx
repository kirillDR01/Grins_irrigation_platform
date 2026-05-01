import { Outlet } from 'react-router-dom';
import { PhoneOnlyGate } from './PhoneOnlyGate';

export function TechMobileLayout() {
  return (
    <div className="min-h-screen bg-slate-50">
      <PhoneOnlyGate>
        <Outlet />
      </PhoneOnlyGate>
    </div>
  );
}
