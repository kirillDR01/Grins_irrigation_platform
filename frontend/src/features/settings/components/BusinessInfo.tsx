import { useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Building2, Upload, X } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { useSettings, useUpdateSettings, useUploadLogo } from '../hooks';

const schema = z.object({
  company_name: z.string().min(1, 'Company name is required'),
  company_address: z.string().min(1, 'Address is required'),
  company_phone: z.string().min(1, 'Phone is required'),
  company_email: z.string().email('Invalid email'),
  company_website: z.string().optional().or(z.literal('')),
});

type FormData = z.infer<typeof schema>;

export function BusinessInfo() {
  const { data: settings } = useSettings();
  const updateSettings = useUpdateSettings();
  const uploadLogo = useUploadLogo();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);

  const form = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      company_name: '',
      company_address: '',
      company_phone: '',
      company_email: '',
      company_website: '',
    },
  });

  useEffect(() => {
    if (settings) {
      form.reset({
        company_name: settings.company_name ?? '',
        company_address: settings.company_address ?? '',
        company_phone: settings.company_phone ?? '',
        company_email: settings.company_email ?? '',
        company_website: settings.company_website ?? '',
      });
      setLogoPreview(settings.company_logo_url);
    }
  }, [settings, form]);

  const onSubmit = async (data: FormData) => {
    try {
      await updateSettings.mutateAsync(data);
      toast.success('Business information saved');
    } catch {
      toast.error('Failed to save business information');
    }
  };

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const { url } = await uploadLogo.mutateAsync(file);
      setLogoPreview(url);
      await updateSettings.mutateAsync({ company_logo_url: url });
      toast.success('Logo uploaded');
    } catch {
      toast.error('Failed to upload logo');
    }
  };

  const handleRemoveLogo = async () => {
    try {
      await updateSettings.mutateAsync({ company_logo_url: null });
      setLogoPreview(null);
      toast.success('Logo removed');
    } catch {
      toast.error('Failed to remove logo');
    }
  };

  return (
    <Card data-testid="business-info-section" className="bg-white rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow dark:bg-slate-800 dark:border-slate-700">
      <CardHeader className="p-6 border-b border-slate-100 dark:border-slate-700">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-50 rounded-lg dark:bg-blue-900/30">
            <Building2 className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <CardTitle className="font-bold text-slate-800 text-lg dark:text-slate-100">Business Information</CardTitle>
            <CardDescription className="text-slate-500 text-sm dark:text-slate-400">Company details used on invoices and estimates</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-6">
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6" data-testid="business-info-form">
          {/* Logo */}
          <div className="space-y-2">
            <Label className="text-sm font-medium text-slate-700 dark:text-slate-300">Company Logo</Label>
            <div className="flex items-center gap-4">
              {logoPreview ? (
                <div className="relative">
                  <img
                    src={logoPreview}
                    alt="Company logo"
                    className="w-16 h-16 rounded-lg object-cover border border-slate-200 dark:border-slate-600"
                    data-testid="company-logo-preview"
                  />
                  <button
                    type="button"
                    onClick={handleRemoveLogo}
                    className="absolute -top-2 -right-2 p-0.5 bg-red-500 text-white rounded-full hover:bg-red-600"
                    data-testid="remove-logo-btn"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : (
                <div className="w-16 h-16 rounded-lg border-2 border-dashed border-slate-300 flex items-center justify-center dark:border-slate-600">
                  <Building2 className="w-6 h-6 text-slate-400" />
                </div>
              )}
              <div>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadLogo.isPending}
                  data-testid="upload-logo-btn"
                >
                  <Upload className="w-4 h-4 mr-1" />
                  {uploadLogo.isPending ? 'Uploading...' : 'Upload Logo'}
                </Button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/gif"
                  className="hidden"
                  onChange={handleLogoUpload}
                  data-testid="logo-file-input"
                />
                <p className="text-xs text-slate-400 mt-1">JPG, PNG or GIF. Max 2MB.</p>
              </div>
            </div>
          </div>

          {/* Name & Phone */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="bi-company-name" className="text-sm font-medium text-slate-700 dark:text-slate-300">Company Name</Label>
              <Input
                id="bi-company-name"
                data-testid="bi-company-name-input"
                {...form.register('company_name')}
                placeholder="Company name"
              />
              {form.formState.errors.company_name && (
                <p className="text-xs text-red-500">{form.formState.errors.company_name.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="bi-company-phone" className="text-sm font-medium text-slate-700 dark:text-slate-300">Business Phone</Label>
              <Input
                id="bi-company-phone"
                type="tel"
                data-testid="bi-company-phone-input"
                {...form.register('company_phone')}
                placeholder="Business phone"
              />
              {form.formState.errors.company_phone && (
                <p className="text-xs text-red-500">{form.formState.errors.company_phone.message}</p>
              )}
            </div>
          </div>

          {/* Address */}
          <div className="space-y-2">
            <Label htmlFor="bi-company-address" className="text-sm font-medium text-slate-700 dark:text-slate-300">Business Address</Label>
            <Input
              id="bi-company-address"
              data-testid="bi-company-address-input"
              {...form.register('company_address')}
              placeholder="Business address"
            />
            {form.formState.errors.company_address && (
              <p className="text-xs text-red-500">{form.formState.errors.company_address.message}</p>
            )}
          </div>

          {/* Email & Website */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="bi-company-email" className="text-sm font-medium text-slate-700 dark:text-slate-300">Business Email</Label>
              <Input
                id="bi-company-email"
                type="email"
                data-testid="bi-company-email-input"
                {...form.register('company_email')}
                placeholder="Business email"
              />
              {form.formState.errors.company_email && (
                <p className="text-xs text-red-500">{form.formState.errors.company_email.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="bi-company-website" className="text-sm font-medium text-slate-700 dark:text-slate-300">Website</Label>
              <Input
                id="bi-company-website"
                data-testid="bi-company-website-input"
                {...form.register('company_website')}
                placeholder="https://example.com"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <Button type="submit" disabled={updateSettings.isPending} data-testid="save-business-info-btn">
              {updateSettings.isPending ? 'Saving...' : 'Save Business Info'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
