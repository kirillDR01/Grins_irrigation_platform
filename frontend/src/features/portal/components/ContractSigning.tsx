import { useState, useRef, useCallback, useEffect } from 'react';
import type { AxiosError } from 'axios';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, AlertTriangle, PenLine, Eraser } from 'lucide-react';
import { usePortalContract, useSignContract } from '../hooks';

function extractErrorMessage(err: unknown): string | undefined {
  const axErr = err as AxiosError<{ detail?: string }> | undefined;
  return axErr?.response?.data?.detail ?? (err as Error | undefined)?.message;
}

export function ContractSigning() {
  const { token = '' } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const { data: contract, isLoading, error } = usePortalContract(token);
  const sign = useSignContract(token);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasSignature, setHasSignature] = useState(false);

  const isExpired = error && (error as { response?: { status?: number } })?.response?.status === 410;

  // Initialize canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
      ctx.strokeStyle = '#1e293b';
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    return () => window.removeEventListener('resize', resizeCanvas);
  }, [contract]);

  const getCanvasPoint = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY;
    return { x: clientX - rect.left, y: clientY - rect.top };
  }, []);

  const startDrawing = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    const point = getCanvasPoint(e);
    if (!point) return;
    const ctx = canvasRef.current?.getContext('2d');
    if (!ctx) return;
    ctx.beginPath();
    ctx.moveTo(point.x, point.y);
    setIsDrawing(true);
  }, [getCanvasPoint]);

  const draw = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    if (!isDrawing) return;
    const point = getCanvasPoint(e);
    if (!point) return;
    const ctx = canvasRef.current?.getContext('2d');
    if (!ctx) return;
    ctx.lineTo(point.x, point.y);
    ctx.stroke();
    setHasSignature(true);
  }, [isDrawing, getCanvasPoint]);

  const stopDrawing = useCallback(() => {
    setIsDrawing(false);
  }, []);

  const clearSignature = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasSignature(false);
  }, []);

  const handleSign = async () => {
    const canvas = canvasRef.current;
    if (!canvas || !hasSignature) return;
    const signatureData = canvas.toDataURL('image/png');
    try {
      await sign.mutateAsync({ signature_data: signatureData });
      navigate(`/portal/contracts/${token}/confirmed`, { state: { action: 'signed' } });
    } catch {
      // surfaced via sign.error below
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50" data-testid="contract-loading">
        <Loader2 className="h-8 w-8 animate-spin text-teal-500" />
      </div>
    );
  }

  if (isExpired) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4" data-testid="contract-expired">
        <div className="max-w-md text-center space-y-4">
          <AlertTriangle className="h-12 w-12 text-amber-500 mx-auto" />
          <h1 className="text-xl font-bold text-slate-800">Link Expired</h1>
          <p className="text-slate-600">
            This contract link has expired. Please contact the business for an updated link.
          </p>
        </div>
      </div>
    );
  }

  if (error || !contract) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4" data-testid="contract-error">
        <div className="max-w-md text-center space-y-4">
          <AlertTriangle className="h-12 w-12 text-red-500 mx-auto" />
          <h1 className="text-xl font-bold text-slate-800">Unable to Load Contract</h1>
          <p className="text-slate-600">
            We couldn&apos;t load this contract. The link may be invalid or expired.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50" data-testid="contract-signing-page">
      {/* Header with company branding */}
      <header className="bg-white border-b border-slate-200 px-4 py-6 md:px-8">
        <div className="max-w-3xl mx-auto flex items-center gap-4">
          {contract.company_logo_url && (
            <img
              src={contract.company_logo_url}
              alt={contract.company_name ?? "Grin's Irrigation"}
              className="h-12 w-auto object-contain"
              data-testid="company-logo"
            />
          )}
          <div>
            <h1 className="text-lg font-bold text-slate-800">
              {contract.company_name ?? "Grin's Irrigation"}
            </h1>
            {contract.company_phone && (
              <p className="text-sm text-slate-500">{contract.company_phone}</p>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8 md:px-8 space-y-6">
        {/* Contract info */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <p className="text-sm text-slate-500 mb-1">Prepared for</p>
          <p className="font-semibold text-slate-800">{contract.customer_name}</p>
        </div>

        {/* Contract body */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 md:p-8">
          <div
            className="prose prose-slate prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: contract.contract_body }}
            data-testid="contract-body"
          />
        </div>

        {/* Terms and conditions */}
        {contract.terms_and_conditions && (
          <div className="bg-slate-100 rounded-xl border border-slate-200 p-6">
            <h3 className="font-semibold text-slate-700 mb-2 text-sm uppercase tracking-wide">
              Terms &amp; Conditions
            </h3>
            <div
              className="prose prose-slate prose-xs max-w-none text-slate-600"
              dangerouslySetInnerHTML={{ __html: contract.terms_and_conditions }}
              data-testid="contract-terms"
            />
          </div>
        )}

        {/* Signature pad */}
        {!contract.is_signed ? (
          <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4" data-testid="signature-section">
            {sign.isError && (
              <Alert variant="destructive" data-testid="contract-sign-error">
                <AlertDescription>
                  {extractErrorMessage(sign.error) ??
                    "We couldn't save your signature. Please try again or call us at the number above."}
                </AlertDescription>
              </Alert>
            )}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <PenLine className="h-5 w-5 text-teal-500" />
                <h3 className="font-semibold text-slate-800">Your Signature</h3>
              </div>
              {hasSignature && (
                <Button variant="ghost" size="sm" onClick={clearSignature} data-testid="clear-signature-btn">
                  <Eraser className="h-4 w-4" />
                  Clear
                </Button>
              )}
            </div>

            <div className="border-2 border-dashed border-slate-300 rounded-lg bg-white relative">
              <canvas
                ref={canvasRef}
                className="w-full h-40 md:h-48 cursor-crosshair touch-none"
                onMouseDown={startDrawing}
                onMouseMove={draw}
                onMouseUp={stopDrawing}
                onMouseLeave={stopDrawing}
                onTouchStart={startDrawing}
                onTouchMove={draw}
                onTouchEnd={stopDrawing}
                data-testid="signature-canvas"
              />
              {!hasSignature && (
                <p className="absolute inset-0 flex items-center justify-center text-slate-400 text-sm pointer-events-none">
                  Draw your signature here
                </p>
              )}
            </div>

            <Button
              onClick={handleSign}
              disabled={!hasSignature || sign.isPending}
              className="w-full h-12"
              data-testid="sign-contract-btn"
            >
              {sign.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <PenLine className="h-4 w-4" />
              )}
              Sign Contract
            </Button>
          </div>
        ) : (
          <div className="text-center text-sm text-slate-500 py-4" data-testid="contract-signed-notice">
            This contract was signed on {contract.signed_at ? new Date(contract.signed_at).toLocaleDateString() : 'a previous date'}.
          </div>
        )}
      </main>
    </div>
  );
}
