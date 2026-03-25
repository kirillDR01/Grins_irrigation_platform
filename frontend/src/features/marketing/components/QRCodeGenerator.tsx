import { useState, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { QRCodeSVG } from 'qrcode.react';
import { Download, QrCode } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const qrSchema = z.object({
  target_url: z.string().url('Must be a valid URL'),
  campaign_name: z.string().min(1, 'Campaign name is required'),
});

type QRFormData = z.infer<typeof qrSchema>;

function buildUtmUrl(targetUrl: string, campaignName: string): string {
  const url = new URL(targetUrl);
  url.searchParams.set('utm_source', 'qr_code');
  url.searchParams.set('utm_campaign', campaignName);
  url.searchParams.set('utm_medium', 'print');
  return url.toString();
}

export function QRCodeGenerator() {
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null);
  const [campaignLabel, setCampaignLabel] = useState('');
  const qrRef = useRef<HTMLDivElement>(null);

  const form = useForm<QRFormData>({
    resolver: zodResolver(qrSchema),
    defaultValues: { target_url: '', campaign_name: '' },
  });

  const onSubmit = (data: QRFormData) => {
    const utmUrl = buildUtmUrl(data.target_url, data.campaign_name);
    setGeneratedUrl(utmUrl);
    setCampaignLabel(data.campaign_name);
  };

  const handleDownload = useCallback(() => {
    if (!qrRef.current) return;
    const svg = qrRef.current.querySelector('svg');
    if (!svg) return;

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const svgData = new XMLSerializer().serializeToString(svg);
    const img = new Image();
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    img.onload = () => {
      canvas.width = 300;
      canvas.height = 300;
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, 300, 300);
      ctx.drawImage(img, 0, 0, 300, 300);
      URL.revokeObjectURL(url);

      const link = document.createElement('a');
      link.download = `qr-${campaignLabel || 'code'}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    };
    img.src = url;
  }, [campaignLabel]);

  return (
    <div className="space-y-6" data-testid="qr-code-generator">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <QrCode className="h-5 w-5 text-teal-500" />
            Generate QR Code
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="space-y-4"
            data-testid="qr-form"
          >
            <div className="space-y-1">
              <Label>Target URL</Label>
              <Input
                {...form.register('target_url')}
                placeholder="https://example.com/landing-page"
                data-testid="qr-url-input"
              />
              {form.formState.errors.target_url && (
                <p className="text-sm text-red-500">
                  {form.formState.errors.target_url.message}
                </p>
              )}
            </div>
            <div className="space-y-1">
              <Label>Campaign Name</Label>
              <Input
                {...form.register('campaign_name')}
                placeholder="e.g., spring-flyer-2025"
                data-testid="qr-campaign-input"
              />
              {form.formState.errors.campaign_name && (
                <p className="text-sm text-red-500">
                  {form.formState.errors.campaign_name.message}
                </p>
              )}
            </div>
            <Button type="submit" data-testid="generate-qr-btn">
              Generate QR Code
            </Button>
          </form>
        </CardContent>
      </Card>

      {generatedUrl && (
        <Card data-testid="qr-preview">
          <CardHeader>
            <CardTitle className="text-lg">QR Code Preview</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-4">
            <div ref={qrRef} className="p-4 bg-white rounded-lg border">
              <QRCodeSVG value={generatedUrl} size={200} level="M" />
            </div>
            <p className="text-xs text-slate-500 max-w-md text-center break-all">
              {generatedUrl}
            </p>
            <Button
              variant="outline"
              onClick={handleDownload}
              data-testid="download-qr-btn"
            >
              <Download className="h-4 w-4 mr-1" /> Download PNG
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
