import { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useGetEmbeddedSigningUrl } from '../hooks/useSalesPipeline';

interface SignWellEmbeddedSignerProps {
  entryId: string;
  onComplete?: () => void;
  disabled?: boolean;
  disabledReason?: string;
}

export function SignWellEmbeddedSigner({
  entryId,
  onComplete,
  disabled,
  disabledReason,
}: SignWellEmbeddedSignerProps) {
  const [open, setOpen] = useState(false);
  const [signingUrl, setSigningUrl] = useState<string | null>(null);
  const getUrl = useGetEmbeddedSigningUrl();

  const handleOpen = useCallback(async () => {
    try {
      const result = await getUrl.mutateAsync(entryId);
      setSigningUrl(result.signing_url);
      setOpen(true);
    } catch {
      toast.error('Failed to load signing form');
    }
  }, [entryId, getUrl]);

  useEffect(() => {
    const handler = (e: MessageEvent) => {
      if (
        typeof e.data === 'object' &&
        e.data?.type === 'signwell_event' &&
        e.data?.event_type === 'document_completed'
      ) {
        toast.success('Document signed');
        setOpen(false);
        setSigningUrl(null);
        onComplete?.();
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [onComplete]);

  return (
    <>
      <span title={disabled ? disabledReason : undefined}>
        <Button
          size="sm"
          variant="outline"
          onClick={handleOpen}
          disabled={getUrl.isPending || disabled}
          data-testid="embedded-sign-btn"
        >
          {getUrl.isPending ? 'Loading…' : 'Sign On-Site'}
        </Button>
      </span>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-3xl h-[80vh] p-0">
          <DialogHeader className="p-4 pb-0">
            <DialogTitle>Sign Document</DialogTitle>
          </DialogHeader>
          {signingUrl && (
            <iframe
              src={signingUrl}
              className="w-full flex-1 border-0"
              style={{ height: 'calc(80vh - 60px)' }}
              title="SignWell Signing"
              data-testid="signwell-iframe"
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
