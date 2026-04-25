/**
 * PasskeyManager — register, list, and revoke passkeys.
 *
 * Drops into the Settings page as a self-contained Card. Uses the standard
 * project patterns: TanStack Query (with the passkeyKeys factory), React
 * Hook Form + Zod for the device-name input, sonner toasts for feedback,
 * and the shadcn Dialog for the revoke confirmation.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Fingerprint, Loader2, Shield, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

import { webauthnApi } from '../api/webauthn';
import { passkeyKeys } from '../api/keys';
import {
  useRegisterPasskey,
  useRevokePasskey,
} from '../hooks/usePasskeyAuth';
import type { Passkey } from '../types/webauthn';

const deviceNameSchema = z.object({
  device_name: z
    .string()
    .min(1, 'Required')
    .max(100, 'Max 100 chars'),
});

type DeviceNameForm = z.infer<typeof deviceNameSchema>;

function formatDate(value: string | null): string {
  if (!value) return '—';
  return new Date(value).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function deviceTypeLabel(type: Passkey['credential_device_type']): string {
  return type === 'multi_device' ? 'Syncs across devices' : 'This device only';
}

export function PasskeyManager() {
  const [addOpen, setAddOpen] = useState(false);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  const list = useQuery({
    queryKey: passkeyKeys.list(),
    queryFn: webauthnApi.listPasskeys,
  });

  const register = useRegisterPasskey();
  const revoke = useRevokePasskey();

  const form = useForm<DeviceNameForm>({
    resolver: zodResolver(deviceNameSchema),
    defaultValues: { device_name: '' },
  });

  const onSubmitAdd = async ({ device_name }: DeviceNameForm) => {
    try {
      await register.mutateAsync(device_name);
      toast.success('Passkey added');
      setAddOpen(false);
      form.reset();
    } catch (e: unknown) {
      // Silent abort if the user cancelled the OS biometric prompt.
      if (e instanceof Error && e.name === 'NotAllowedError') return;
      const msg = e instanceof Error ? e.message : 'unknown error';
      toast.error(`Failed to add passkey: ${msg}`);
    }
  };

  const handleRevoke = async (id: string) => {
    try {
      await revoke.mutateAsync(id);
      toast.success('Passkey removed');
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'unknown error';
      toast.error(`Failed to remove passkey: ${msg}`);
    } finally {
      setConfirmingId(null);
    }
  };

  return (
    <Card
      data-testid="security-page"
      className="bg-white rounded-2xl shadow-sm border border-slate-100 dark:bg-slate-800 dark:border-slate-700"
    >
      <CardHeader className="p-6 border-b border-slate-100 dark:border-slate-700">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-teal-50 rounded-lg dark:bg-teal-900/30">
            <Shield className="w-5 h-5 text-teal-600 dark:text-teal-400" />
          </div>
          <div className="flex-1">
            <CardTitle className="font-bold text-slate-800 text-lg dark:text-slate-100">
              Sign-in & Security
            </CardTitle>
            <CardDescription className="text-slate-500 text-sm dark:text-slate-400">
              Manage biometric passkeys for Face ID, Touch ID, and Windows Hello.
            </CardDescription>
          </div>
          <Button
            type="button"
            size="sm"
            onClick={() => setAddOpen(true)}
            data-testid="add-passkey-btn"
          >
            <Fingerprint className="h-4 w-4 mr-2" /> Add passkey
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-6">
        {list.isLoading && (
          <div
            className="flex justify-center py-6"
            data-testid="passkey-loading-spinner"
          >
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        )}

        {list.isError && (
          <div className="bg-red-50 p-3 rounded-xl border border-red-200 text-sm text-red-700">
            Failed to load passkeys. Reload the page to try again.
          </div>
        )}

        {list.data && list.data.passkeys.length === 0 && (
          <div
            className="py-8 text-center text-slate-500 text-sm"
            data-testid="passkey-empty-state"
          >
            No passkeys yet. Add one to skip the password next time.
          </div>
        )}

        {list.data && list.data.passkeys.length > 0 && (
          <table
            className="w-full text-sm"
            data-testid="passkey-table"
          >
            <thead className="text-left text-slate-500">
              <tr>
                <th className="py-2 pr-4 font-medium">Device</th>
                <th className="py-2 pr-4 font-medium">Type</th>
                <th className="py-2 pr-4 font-medium">Added</th>
                <th className="py-2 pr-4 font-medium">Last used</th>
                <th className="py-2 pr-4 font-medium" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {list.data.passkeys.map((p) => (
                <tr key={p.id} data-testid="passkey-row">
                  <td className="py-3 pr-4 font-medium text-slate-700 dark:text-slate-200">
                    {p.device_name}
                  </td>
                  <td className="py-3 pr-4 text-slate-500">
                    {deviceTypeLabel(p.credential_device_type)}
                  </td>
                  <td className="py-3 pr-4 text-slate-500">
                    {formatDate(p.created_at)}
                  </td>
                  <td className="py-3 pr-4 text-slate-500">
                    {formatDate(p.last_used_at)}
                  </td>
                  <td className="py-3 pr-4 text-right">
                    <Button
                      variant="destructive"
                      size="sm"
                      data-testid="revoke-passkey-btn"
                      onClick={() => setConfirmingId(p.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>

      {/* Add Passkey Dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent data-testid="passkey-form">
          <DialogHeader>
            <DialogTitle>Add a passkey</DialogTitle>
            <DialogDescription>
              Give this device a memorable name. Your platform's biometric
              prompt will appear next.
            </DialogDescription>
          </DialogHeader>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmitAdd)}
              className="space-y-4"
            >
              <FormField
                control={form.control}
                name="device_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Device name</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="e.g. Kirill's MacBook Pro"
                        data-testid="device-name-input"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setAddOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={register.isPending}
                  data-testid="submit-passkey-btn"
                >
                  {register.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    'Continue'
                  )}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      {/* Revoke confirmation dialog */}
      <Dialog
        open={confirmingId !== null}
        onOpenChange={(open) => !open && setConfirmingId(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove this passkey?</DialogTitle>
            <DialogDescription>
              You'll need to re-enroll on this device to use biometric sign-in
              again.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setConfirmingId(null)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={revoke.isPending}
              onClick={() => confirmingId && handleRevoke(confirmingId)}
            >
              {revoke.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Remove'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
