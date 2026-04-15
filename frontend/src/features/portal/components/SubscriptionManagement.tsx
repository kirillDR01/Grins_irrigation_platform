/**
 * Subscription management portal — public page where subscribers
 * enter their email to receive a Stripe billing portal link.
 *
 * Validates: Requirements 2.1, 2.2, 2.3, 2.4
 */

import { useState } from 'react';
import { Mail, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useManageSubscription } from '../hooks';

type ViewState = 'form' | 'success' | 'error';

export function SubscriptionManagement() {
  const [email, setEmail] = useState('');
  const [view, setView] = useState<ViewState>('form');
  const [errorMessage, setErrorMessage] = useState('');
  const mutation = useManageSubscription();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    try {
      await mutation.mutateAsync(email.trim());
      setView('success');
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? 'Something went wrong. Please try again.';
      setErrorMessage(detail);
      setView('error');
    }
  };

  const handleResend = () => {
    setView('form');
    setErrorMessage('');
    mutation.reset();
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-md" data-testid="subscription-manage-card">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Manage Your Subscription</CardTitle>
        </CardHeader>
        <CardContent>
          {view === 'form' && (
            <form onSubmit={handleSubmit} data-testid="subscription-manage-form">
              <p className="text-sm text-muted-foreground mb-4">
                Enter the email address associated with your subscription and
                we'll send you a link to manage your billing.
              </p>
              <div className="space-y-4">
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="email"
                    placeholder="your@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-10"
                    required
                    data-testid="subscription-email-input"
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={mutation.isPending || !email.trim()}
                  data-testid="subscription-submit-btn"
                >
                  {mutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    'Send Login Email'
                  )}
                </Button>
              </div>
            </form>
          )}

          {view === 'success' && (
            <div className="text-center space-y-4" data-testid="subscription-success">
              <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
              <h3 className="font-semibold text-lg">Email Sent!</h3>
              <p className="text-sm text-muted-foreground">
                We've sent a login link to <strong>{email}</strong>. Please
                check your inbox and spam folder.
              </p>
              <Button
                variant="outline"
                onClick={handleResend}
                data-testid="subscription-resend-btn"
              >
                Resend Email
              </Button>
            </div>
          )}

          {view === 'error' && (
            <div className="space-y-4" data-testid="subscription-error">
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{errorMessage}</AlertDescription>
              </Alert>
              <Button
                variant="outline"
                onClick={handleResend}
                className="w-full"
                data-testid="subscription-try-again-btn"
              >
                Try Again
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
