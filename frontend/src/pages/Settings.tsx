import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { User, Bell, Key, Shield, LogOut, Lock, Mail, Phone } from "lucide-react";
import { useAuth, PasskeyManager } from "@/features/auth";
import { authApi } from "@/features/auth/api";
import { toast } from "sonner";
import { BusinessInfo, InvoiceDefaults, NotificationPrefs, EstimateDefaults, BusinessSettingsPanel } from "@/features/settings";

export function SettingsPage() {
  const { user, logout, updateUser } = useAuth();
  
  // Profile form state - parse name into first/last
  const nameParts = user?.name?.split(' ') ?? ['', ''];
  const [firstName, setFirstName] = useState(nameParts[0] ?? '');
  const [lastName, setLastName] = useState(nameParts.slice(1).join(' ') ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [phone, setPhone] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  
  const [smsEnabled, setSmsEnabled] = useState(true);
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);

  const handleSaveProfile = async () => {
    setIsSaving(true);
    try {
      const fullName = `${firstName} ${lastName}`.trim();
      const updatedUser = await authApi.updateProfile({
        name: fullName || undefined,
        email: email || undefined,
        phone: phone || undefined,
      });
      updateUser(updatedUser);
      toast.success("Profile updated successfully");
    } catch {
      toast.error("Failed to update profile");
    } finally {
      setIsSaving(false);
    }
  };

  const handleSignOut = async () => {
    await logout();
  };

  return (
    <div data-testid="settings-page" className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Page Header */}
      <div data-testid="page-header">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Settings</h1>
        <p className="text-slate-500 mt-1 dark:text-slate-400">Manage your account and preferences</p>
      </div>

      {/* Profile Settings Section */}
      <Card data-testid="profile-settings" className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow dark:bg-slate-800 dark:border-slate-700">
        <CardHeader className="p-6 border-b border-slate-100 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-teal-50 rounded-lg dark:bg-teal-900/30">
              <User className="w-5 h-5 text-teal-600 dark:text-teal-400" />
            </div>
            <div>
              <CardTitle className="font-bold text-slate-800 text-lg dark:text-slate-100">Profile Settings</CardTitle>
              <CardDescription className="text-slate-500 text-sm dark:text-slate-400">Update your personal information</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6 space-y-6">
          {/* Avatar Section */}
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-teal-100 text-teal-700 font-bold text-xl flex items-center justify-center dark:bg-teal-900/50 dark:text-teal-300">
              {firstName[0]?.toUpperCase() ?? ''}{lastName[0]?.toUpperCase() ?? ''}
            </div>
            <div>
              <Button variant="secondary" size="sm">Change Photo</Button>
              <p className="text-xs text-slate-400 mt-1">JPG, PNG or GIF. Max 2MB.</p>
            </div>
          </div>

          {/* Name Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="first-name" className="text-sm font-medium text-slate-700 dark:text-slate-300">First Name</Label>
              <Input 
                id="first-name" 
                data-testid="profile-first-name-input"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="First name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="last-name" className="text-sm font-medium text-slate-700 dark:text-slate-300">Last Name</Label>
              <Input 
                id="last-name"
                data-testid="profile-last-name-input"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                placeholder="Last name"
              />
            </div>
          </div>

          {/* Contact Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-medium text-slate-700 dark:text-slate-300">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input 
                  id="email" 
                  type="email"
                  data-testid="profile-email-input"
                  className="pl-10"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email address"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone" className="text-sm font-medium text-slate-700 dark:text-slate-300">Phone</Label>
              <div className="relative">
                <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input 
                  id="phone" 
                  type="tel"
                  data-testid="profile-phone-input"
                  className="pl-10"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="Phone number"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <Button onClick={handleSaveProfile} disabled={isSaving} data-testid="save-profile-btn">
              {isSaving ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Notification Preferences Section */}
      <Card data-testid="notification-settings" className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow dark:bg-slate-800 dark:border-slate-700">
        <CardHeader className="p-6 border-b border-slate-100 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-violet-50 rounded-lg dark:bg-violet-900/30">
              <Bell className="w-5 h-5 text-violet-600 dark:text-violet-400" />
            </div>
            <div>
              <CardTitle className="font-bold text-slate-800 text-lg dark:text-slate-100">Notification Preferences</CardTitle>
              <CardDescription className="text-slate-500 text-sm dark:text-slate-400">Choose how you want to be notified</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6 space-y-6">
          <div className="flex items-center justify-between py-3 border-b border-slate-50 dark:border-slate-700">
            <div className="space-y-0.5">
              <Label htmlFor="sms-toggle" className="text-sm font-medium text-slate-700 dark:text-slate-300">SMS Notifications</Label>
              <p className="text-xs text-slate-400">Receive text messages for job updates</p>
            </div>
            <Switch 
              id="sms-toggle"
              data-testid="sms-toggle"
              checked={smsEnabled}
              onCheckedChange={setSmsEnabled}
            />
          </div>

          <div className="flex items-center justify-between py-3 border-b border-slate-50 dark:border-slate-700">
            <div className="space-y-0.5">
              <Label htmlFor="email-toggle" className="text-sm font-medium text-slate-700 dark:text-slate-300">Email Notifications</Label>
              <p className="text-xs text-slate-400">Receive email updates for invoices and reports</p>
            </div>
            <Switch 
              id="email-toggle"
              data-testid="email-toggle"
              checked={emailEnabled}
              onCheckedChange={setEmailEnabled}
            />
          </div>

          <div className="flex items-center justify-between py-3">
            <div className="space-y-0.5">
              <Label htmlFor="push-toggle" className="text-sm font-medium text-slate-700 dark:text-slate-300">Push Notifications</Label>
              <p className="text-xs text-slate-400">Receive browser push notifications</p>
            </div>
            <Switch 
              id="push-toggle"
              data-testid="push-toggle"
              checked={pushEnabled}
              onCheckedChange={setPushEnabled}
            />
          </div>
        </CardContent>
      </Card>

      {/* Business Information Section (Req 87.3) */}
      <BusinessInfo />

      {/* Invoice Defaults Section (Req 87.4) */}
      <InvoiceDefaults />

      {/* Notification Preferences Section (Req 87.5) */}
      <NotificationPrefs />

      {/* Estimate Defaults Section (Req 87.6) */}
      <EstimateDefaults />

      {/* Business Thresholds Section (H-12 bughunt 2026-04-16) */}
      <BusinessSettingsPanel />

      {/* Integration Settings Section */}
      <Card data-testid="integration-settings" className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow dark:bg-slate-800 dark:border-slate-700">
        <CardHeader className="p-6 border-b border-slate-100 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-50 rounded-lg dark:bg-emerald-900/30">
              <Key className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <CardTitle className="font-bold text-slate-800 text-lg dark:text-slate-100">Integration Settings</CardTitle>
              <CardDescription className="text-slate-500 text-sm dark:text-slate-400">Manage API keys and integrations</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          <div className="p-4 bg-slate-50 rounded-xl dark:bg-slate-700/50">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">API Key</p>
                <p className="text-xs text-slate-400 font-mono mt-1 break-all">grins_sk_****************************1234</p>
              </div>
              <Button variant="secondary" size="sm">Regenerate</Button>
            </div>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl dark:bg-slate-700/50">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Google Maps API</p>
                <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">● Connected</p>
              </div>
              <Button variant="secondary" size="sm">Configure</Button>
            </div>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl dark:bg-slate-700/50">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Twilio SMS</p>
                <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">● Connected</p>
              </div>
              <Button variant="secondary" size="sm">Configure</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sign-in & Security (passkeys) */}
      <PasskeyManager />

      {/* Account Actions Section */}
      <Card data-testid="account-actions" className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow dark:bg-slate-800 dark:border-slate-700">
        <CardHeader className="p-6 border-b border-slate-100 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-rose-50 rounded-lg dark:bg-rose-900/30">
              <Shield className="w-5 h-5 text-rose-600 dark:text-rose-400" />
            </div>
            <div>
              <CardTitle className="font-bold text-slate-800 text-lg dark:text-slate-100">Account Actions</CardTitle>
              <CardDescription className="text-slate-500 text-sm dark:text-slate-400">Manage your account security</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 p-4 bg-slate-50 rounded-xl dark:bg-slate-700/50">
            <div className="flex items-center gap-3 min-w-0">
              <Lock className="w-5 h-5 text-slate-500 dark:text-slate-400 shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Change Password</p>
                <p className="text-xs text-slate-400">Update your account password</p>
              </div>
            </div>
            <Button
              variant="secondary"
              size="sm"
              data-testid="change-password-btn"
              onClick={() => setChangePasswordOpen(true)}
            >
              Change
            </Button>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 p-4 bg-red-50 rounded-xl dark:bg-red-900/20">
            <div className="flex items-center gap-3 min-w-0">
              <LogOut className="w-5 h-5 text-red-500 shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-red-700 dark:text-red-400">Sign Out</p>
                <p className="text-xs text-red-500/70">Sign out of your account</p>
              </div>
            </div>
            <Button
              variant="destructive"
              size="sm"
              data-testid="logout-btn"
              onClick={handleSignOut}
            >
              Sign Out
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Change Password Dialog */}
      <Dialog open={changePasswordOpen} onOpenChange={setChangePasswordOpen}>
        <DialogContent data-testid="change-password-dialog">
          <DialogHeader>
            <DialogTitle>Change Password</DialogTitle>
            <DialogDescription>
              Enter your current password and a new password to update your account security.
            </DialogDescription>
          </DialogHeader>
          <div className="p-6 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="current-password" className="text-sm font-medium text-slate-700 dark:text-slate-300">Current Password</Label>
              <Input 
                id="current-password" 
                type="password"
                placeholder="Enter current password"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="new-password" className="text-sm font-medium text-slate-700 dark:text-slate-300">New Password</Label>
              <Input 
                id="new-password" 
                type="password"
                placeholder="Enter new password"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm-password" className="text-sm font-medium text-slate-700 dark:text-slate-300">Confirm New Password</Label>
              <Input 
                id="confirm-password" 
                type="password"
                placeholder="Confirm new password"
              />
            </div>
          </div>
          <DialogFooter>
            <Button 
              variant="secondary" 
              onClick={() => setChangePasswordOpen(false)}
              data-testid="close-dialog-btn"
            >
              Cancel
            </Button>
            <Button onClick={() => setChangePasswordOpen(false)}>
              Update Password
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
