/**
 * StaffForm — admin dialog for creating or editing a staff member.
 *
 * Renders core fields (name, phone, email, role, skill_level, hourly_rate)
 * and, for admins only, an auth section (username, password, is_login_enabled).
 *
 * Validates: Cluster F — Admin Staff Auth UI.
 */

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, UserPlus } from 'lucide-react';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';

import { useAuth } from '@/features/auth/components/AuthProvider';
import { getErrorMessage } from '@/core/api';
import { useCreateStaff, useUpdateStaff } from '../hooks';
import type { Staff, StaffRole, SkillLevel } from '../types';

// Mirrors the backend admin password policy in src/grins_platform/schemas/staff.py.
const PASSWORD_BLOCKLIST = new Set([
  'admin123',
  'password',
  'qwerty',
  'letmein',
  '12345678',
]);

const PASSWORD_HINT = 'At least 8 characters, including a letter and a number.';

const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .max(128, 'Password must be at most 128 characters')
  .regex(/[A-Za-z]/, 'Password must include a letter')
  .regex(/\d/, 'Password must include a number')
  .refine(
    (v) => !PASSWORD_BLOCKLIST.has(v.toLowerCase()),
    'Password is too common; choose a stronger one',
  );

const usernameSchema = z
  .string()
  .min(3, 'Username must be at least 3 characters')
  .max(50, 'Username must be at most 50 characters')
  .regex(/^[a-zA-Z0-9_.]+$/, 'Letters, digits, underscore, or dot only');

const baseFormSchema = z
  .object({
    name: z.string().min(1, 'Name is required').max(100),
    phone: z
      .string()
      .min(10, 'Phone must be at least 10 digits')
      .max(20)
      .regex(/^\+?[\d\s\-().]+$/, 'Invalid phone format'),
    email: z.string().email('Invalid email').optional().or(z.literal('')),
    role: z.enum(['tech', 'sales', 'admin'] as const),
    skill_level: z.enum(['junior', 'senior', 'lead'] as const).optional(),
    hourly_rate: z.string().optional().or(z.literal('')),
    // Auth section — optional at the schema level; refinement enforces
    // password ≠ username and runs the password validator only when set.
    username: z.string().optional().or(z.literal('')),
    password: z.string().optional().or(z.literal('')),
    is_login_enabled: z.boolean().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.username && data.username.trim()) {
      const parsed = usernameSchema.safeParse(data.username);
      if (!parsed.success) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['username'],
          message: parsed.error.issues[0]?.message ?? 'Invalid username',
        });
      }
    }
    if (data.password && data.password.trim()) {
      const parsed = passwordSchema.safeParse(data.password);
      if (!parsed.success) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['password'],
          message: parsed.error.issues[0]?.message ?? 'Invalid password',
        });
      } else if (data.username && data.password === data.username) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['password'],
          message: 'Password must not match the username',
        });
      }
    }
  });

type StaffFormData = z.infer<typeof baseFormSchema>;

export type StaffFormMode = 'create' | 'edit';

interface StaffFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: StaffFormMode;
  staff?: Staff;
}

export function StaffForm({ open, onOpenChange, mode, staff }: StaffFormProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-lg bg-white rounded-2xl shadow-xl"
        data-testid="staff-form-dialog"
      >
        {open && (
          <StaffFormBody
            onOpenChange={onOpenChange}
            mode={mode}
            staff={staff}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function StaffFormBody({
  onOpenChange,
  mode,
  staff,
}: {
  onOpenChange: (open: boolean) => void;
  mode: StaffFormMode;
  staff?: Staff;
}) {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const isEditing = mode === 'edit';
  const createMutation = useCreateStaff();
  const updateMutation = useUpdateStaff();
  const pending = createMutation.isPending || updateMutation.isPending;

  const form = useForm<StaffFormData>({
    resolver: zodResolver(baseFormSchema),
    defaultValues: {
      name: staff?.name ?? '',
      phone: staff?.phone ?? '',
      email: staff?.email ?? '',
      role: staff?.role ?? 'tech',
      skill_level: staff?.skill_level ?? undefined,
      hourly_rate: staff?.hourly_rate != null ? String(staff.hourly_rate) : '',
      username: staff?.username ?? '',
      password: '',
      is_login_enabled: staff?.is_login_enabled ?? false,
    },
  });

  // Reset the form when the targeted staff changes (e.g. edit a different row).
  useEffect(() => {
    form.reset({
      name: staff?.name ?? '',
      phone: staff?.phone ?? '',
      email: staff?.email ?? '',
      role: staff?.role ?? 'tech',
      skill_level: staff?.skill_level ?? undefined,
      hourly_rate: staff?.hourly_rate != null ? String(staff.hourly_rate) : '',
      username: staff?.username ?? '',
      password: '',
      is_login_enabled: staff?.is_login_enabled ?? false,
    });
  }, [staff, form]);

  const onSubmit = async (data: StaffFormData) => {
    const trimmedPassword = data.password?.trim() || undefined;
    const trimmedUsername = data.username?.trim() || undefined;
    const hourlyRateNumber =
      data.hourly_rate && data.hourly_rate.trim()
        ? Number(data.hourly_rate)
        : undefined;

    const basePayload = {
      name: data.name.trim(),
      phone: data.phone,
      email: data.email?.trim() || null,
      role: data.role as StaffRole,
      skill_level: (data.skill_level ?? null) as SkillLevel | null,
      hourly_rate: hourlyRateNumber ?? null,
    };

    // Auth fields only when admin actually filled them — backend silently
    // accepts but the self-update endpoint would 403 them, so guard at UI.
    const authPayload = isAdmin
      ? {
          ...(trimmedUsername !== undefined ? { username: trimmedUsername } : {}),
          ...(trimmedPassword !== undefined ? { password: trimmedPassword } : {}),
          ...(data.is_login_enabled !== undefined
            ? { is_login_enabled: data.is_login_enabled }
            : {}),
        }
      : {};

    try {
      if (isEditing && staff) {
        await updateMutation.mutateAsync({
          id: staff.id,
          data: { ...basePayload, ...authPayload },
        });
        toast.success(`${basePayload.name} updated`);
      } else {
        await createMutation.mutateAsync({ ...basePayload, ...authPayload });
        toast.success(`${basePayload.name} added`);
      }
      onOpenChange(false);
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  };

  return (
    <>
      <DialogHeader className="pb-2">
        <DialogTitle className="flex items-center gap-2 text-lg font-bold text-slate-800">
          <UserPlus className="h-5 w-5 text-teal-600" />
          {isEditing ? 'Edit Staff Member' : 'Add Staff Member'}
        </DialogTitle>
        <DialogDescription className="text-slate-500 text-sm">
          {isEditing
            ? 'Update profile, role, or login details for this staff member.'
            : 'Create a new staff member. Optional login credentials can be set now or later.'}
        </DialogDescription>
      </DialogHeader>

      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="space-y-4 py-2"
          data-testid="staff-form"
        >
          <div className="grid grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Name <span className="text-red-500">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      data-testid="staff-form-name"
                      placeholder="Full name"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="phone"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Phone <span className="text-red-500">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      data-testid="staff-form-phone"
                      placeholder="(555) 123-4567"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    type="email"
                    data-testid="staff-form-email"
                    placeholder="email@example.com"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <div className="grid grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="role"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Role <span className="text-red-500">*</span>
                  </FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger data-testid="staff-form-role">
                        <SelectValue placeholder="Select role" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="tech">Technician</SelectItem>
                      <SelectItem value="sales">Sales</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="skill_level"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Skill Level</FormLabel>
                  <Select
                    value={field.value ?? ''}
                    onValueChange={(v) =>
                      field.onChange(v === '' ? undefined : v)
                    }
                  >
                    <FormControl>
                      <SelectTrigger data-testid="staff-form-skill">
                        <SelectValue placeholder="Optional" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="junior">Junior</SelectItem>
                      <SelectItem value="senior">Senior</SelectItem>
                      <SelectItem value="lead">Lead</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="hourly_rate"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Hourly Rate (USD)</FormLabel>
                <FormControl>
                  <Input
                    {...field}
                    inputMode="decimal"
                    placeholder="25.00"
                    data-testid="staff-form-hourly-rate"
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {isAdmin && (
            <div
              className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-4"
              data-testid="staff-form-auth-section"
            >
              <div>
                <h3 className="text-sm font-semibold text-slate-700">Login</h3>
                <p className="text-xs text-slate-500">
                  Optional username + password so this staff member can sign in.
                </p>
              </div>

              <FormField
                control={form.control}
                name="username"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Username</FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        autoComplete="off"
                        data-testid="staff-form-username"
                        placeholder="e.g. alice.tech"
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      {isEditing ? 'New password (leave blank to keep current)' : 'Password'}
                    </FormLabel>
                    <FormControl>
                      <Input
                        {...field}
                        type="password"
                        autoComplete="new-password"
                        data-testid="staff-form-password"
                        placeholder="At least 8 characters"
                      />
                    </FormControl>
                    <FormDescription className="text-xs">
                      {PASSWORD_HINT}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="is_login_enabled"
                render={({ field }) => (
                  <FormItem className="flex items-center justify-between rounded-lg bg-white border border-slate-200 px-4 py-3">
                    <div>
                      <FormLabel className="text-sm font-medium text-slate-700">
                        Login enabled
                      </FormLabel>
                      <FormDescription className="text-xs">
                        Disable to block sign-in without deleting credentials.
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch
                        checked={Boolean(field.value)}
                        onCheckedChange={field.onChange}
                        data-testid="staff-form-login-enabled"
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
            </div>
          )}

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={pending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={pending}
              data-testid="staff-form-submit"
              className="bg-teal-500 hover:bg-teal-600 text-white"
            >
              {pending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : isEditing ? (
                'Save Changes'
              ) : (
                'Add Staff'
              )}
            </Button>
          </DialogFooter>
        </form>
      </Form>
    </>
  );
}

export default StaffForm;
