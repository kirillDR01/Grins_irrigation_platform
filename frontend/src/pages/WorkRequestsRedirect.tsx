import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

export function WorkRequestsRedirect() {
  const navigate = useNavigate();

  useEffect(() => {
    toast.info('Work Requests Consolidated', {
      description: 'Work requests have been merged into the Leads pipeline. Redirecting to Leads.',
      duration: 5000,
    });
    navigate('/leads', { replace: true });
  }, [navigate]);

  return null;
}
