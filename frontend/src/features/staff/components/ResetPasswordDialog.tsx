/**
 * ResetPasswordDialog — admin reset of a staff member's password.
 *
 * Calls useResetStaffPassword. Validates against the same admin password
 * policy enforced server-side in src/grins_platform/schemas/staff.py.
 *
 * Validates: Cluster F — Admin Staff Auth UI.
 */

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { KeyRound, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

import { getErrorMessage } from '@/core/api';
import { useResetStaffPassword } from '../hooks';

const PASSWORD_BLOCKLIST = new Set([
  'admin123',
  'password',
  'qwerty',
  'letmein',
  '12345678',
]);

const resetSchema = z.object({
  new_password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .max(128, 'Password must be at most 128 characters')
    .regex(/[A-Za-z]/, 'Password must include a letter')
    .regex(/\d/, 'Password must include a number')
    .refine(
      (v) => !PASSWORD_BLOCKLIST.has(v.toLowerCase()),
      'Password is too common; choose a stronger one',
    ),
});

type ResetForm = z.infer<typeof resetSchema>;

interface ResetPasswordDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  staffId: string;
  staffName: string;
}

export function ResetPasswordDialog({
  open,
  onOpenChange,
  staffId,
  staffName,
}: ResetPasswordDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-md bg-white rounded-2xl shadow-xl"
        data-testid="reset-password-dialog"
      >
        {open && (
          <ResetPasswordBody
            onOpenChange={onOpenChange}
            staffId={staffId}
            staffName={staffName}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function ResetPasswordBody({
  onOpenChange,
  staffId,
  staffName,
}: {
  onOpenChange: (open: boolean) => void;
  staffId: string;
  staffName: string;
}) {
  const mutation = useResetStaffPassword();
  const form = useForm<ResetForm>({
    resolver: zodResolver(resetSchema),
    defaultValues: { new_password: '' },
  });

  const onSubmit = async (data: ResetForm) => {
    try {
      await mutation.mutateAsync({
        id: staffId,
        payload: { new_password: data.new_password },
      });
      toast.success(`Password reset for ${staffName}`);
      form.reset({ new_password: '' });
      onOpenChange(false);
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  return (
    <>
      <DialogHeader className="pb-2">
        <DialogTitle className="flex items-center gap-2 text-lg font-bold text-slate-800">
          <KeyRound className="h-5 w-5 text-teal-600" />
          Reset Password
        </DialogTitle>
        <DialogDescription className="text-slate-500 text-sm">
          Set a new password for {staffName}. The current password will be
          replaced and any lockout cleared.
        </DialogDescription>
      </DialogHeader>

      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="space-y-4 py-2"
          data-testid="reset-password-form"
        >
          <FormField
            control={form.control}
            name="new_password"
            render={({ field }) => (
              <FormItem>
                <FormLabel>New password</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    type="password"
                    autoComplete="new-password"
                    data-testid="reset-password-input"
                    placeholder="At least 8 characters"
                  />
                </FormControl>
                <FormDescription className="text-xs">
                  At least 8 characters, including a letter and a number.
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={mutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={mutation.isPending}
              data-testid="reset-password-submit"
              className="bg-teal-500 hover:bg-teal-600 text-white"
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Resetting...
                </>
              ) : (
                'Reset Password'
              )}
            </Button>
          </DialogFooter>
        </form>
      </Form>
    </>
  );
}

export default ResetPasswordDialog;
