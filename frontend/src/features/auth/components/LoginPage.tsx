/**
 * LoginPage component for user authentication.
 *
 * Features:
 * - Username input with User icon
 * - Password input with visibility toggle
 * - Remember me checkbox
 * - Sign In button with loading state
 * - Error alert for invalid credentials
 * - Redirect to dashboard on success
 *
 * Requirements: 19.1-19.7
 * UI Redesign: Task 27.1-27.7
 */

import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { User, Eye, EyeOff, AlertCircle, Loader2, Droplets } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { useAuth } from './AuthProvider';

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get redirect path from location state or default to dashboard
  const from = (location.state as { from?: string })?.from || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login({ username, password, remember_me: rememberMe });
      navigate(from, { replace: true });
    } catch (err) {
      // Always show a user-friendly message for login failures
      // Don't expose technical details like "401" or "Request failed"
      setError('Username or password is incorrect. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="flex min-h-screen items-center justify-center bg-slate-50 px-4"
      data-testid="login-page"
    >
      <div className="w-full max-w-md mx-auto space-y-8">
        {/* Logo Section - Task 27.3 */}
        <div className="flex flex-col items-center justify-center">
          <div className="w-12 h-12 bg-teal-500 rounded-xl shadow-lg shadow-teal-500/30 flex items-center justify-center mb-4">
            <Droplets className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-800 text-center">
            Grin's Irrigation
          </h1>
        </div>

        {/* Login Card - Task 27.2 */}
        <div className="bg-white rounded-2xl shadow-lg p-8">
          {/* Form Title - Task 27.4 */}
          <h2 className="text-2xl font-bold text-slate-800 text-center mb-6">
            Sign in to your account
          </h2>

          {/* Login Form */}
          <form
            onSubmit={handleSubmit}
            className="space-y-6"
            data-testid="login-form"
          >
            {/* Error Alert - User-friendly error message with highlighted box */}
            {error && (
              <div 
                className="bg-red-50 p-4 rounded-xl border border-red-200 flex items-start gap-3"
                data-testid="login-error"
              >
                <div className="bg-red-100 p-2 rounded-full flex-shrink-0">
                  <AlertCircle className="h-4 w-4 text-red-600" />
                </div>
                <div>
                  <p className="text-red-800 font-medium">Login Failed</p>
                  <p className="text-red-600 text-sm mt-0.5">{error}</p>
                </div>
              </div>
            )}

            {/* Email/Username Field - Task 27.5 */}
            <div className="space-y-2">
              <Label htmlFor="username" className="text-sm font-medium text-slate-700">
                Username
              </Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your username"
                  className="pl-10"
                  required
                  disabled={isLoading}
                  data-testid="username-input"
                />
              </div>
            </div>

            {/* Password Field - Task 27.5 */}
            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm font-medium text-slate-700">
                Password
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="pr-10"
                  required
                  disabled={isLoading}
                  data-testid="password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  tabIndex={-1}
                  data-testid="password-toggle"
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Remember Me */}
            <div className="flex items-center space-x-2">
              <Checkbox
                id="remember-me"
                checked={rememberMe}
                onCheckedChange={(checked) => setRememberMe(checked === true)}
                disabled={isLoading}
                data-testid="remember-me-checkbox"
              />
              <Label htmlFor="remember-me" className="text-sm font-normal text-slate-600">
                Remember me
              </Label>
            </div>

            {/* Submit Button - Task 27.6: Primary button styling (teal-500) */}
            <Button
              type="submit"
              className="w-full"
              disabled={isLoading}
              data-testid="login-btn"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
