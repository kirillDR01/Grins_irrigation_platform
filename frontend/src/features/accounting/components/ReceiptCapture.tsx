// @ts-nocheck — pre-existing TS errors documented in bughunt/2026-04-29-pre-existing-tsc-errors.md
import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/shared/components';
import { Camera, Upload, Check, X } from 'lucide-react';
import { cn } from '@/shared/utils/cn';
import { useExtractReceipt } from '../hooks';
import type { ReceiptExtraction } from '../types';

interface ReceiptCaptureProps {
  onExtracted?: (data: ReceiptExtraction) => void;
}

export function ReceiptCapture({ onExtracted }: ReceiptCaptureProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [extraction, setExtraction] = useState<ReceiptExtraction | null>(null);
  const extractReceipt = useExtractReceipt();

  const handleFileSelect = useCallback(async (file: File) => {
    // Show preview
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target?.result as string);
    reader.readAsDataURL(file);

    // Extract via OCR
    try {
      const result = await extractReceipt.mutateAsync(file);
      setExtraction(result);
      onExtracted?.(result);
    } catch {
      setExtraction(null);
    }
  }, [extractReceipt, onExtracted]);

  const handleReset = () => {
    setPreview(null);
    setExtraction(null);
  };

  return (
    <Card data-testid="receipt-capture">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Camera className="h-5 w-5 text-teal-500" />
          Receipt Capture
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!preview ? (
          <label className="cursor-pointer">
            <div
              className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center hover:border-teal-400 transition-colors"
              data-testid="receipt-dropzone"
            >
              <Upload className="h-10 w-10 text-slate-400 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-600">Upload a receipt photo</p>
              <p className="text-xs text-slate-400 mt-1">JPEG, PNG, or PDF up to 10MB</p>
              <Button variant="outline" size="sm" className="mt-3" type="button" data-testid="receipt-choose-btn">
                Choose File
              </Button>
            </div>
            <input
              type="file"
              accept="image/jpeg,image/png,application/pdf"
              className="hidden"
              data-testid="receipt-file-input"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileSelect(file);
              }}
            />
          </label>
        ) : (
          <div className="space-y-4">
            {/* Preview */}
            <div className="relative rounded-lg overflow-hidden bg-slate-100 max-h-64 flex items-center justify-center">
              <img src={preview} alt="Receipt preview" className="max-h-64 object-contain" data-testid="receipt-preview" />
              <Button
                variant="ghost"
                size="icon"
                className="absolute top-2 right-2 bg-white/80 hover:bg-white"
                onClick={handleReset}
                data-testid="receipt-clear-btn"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Extraction Results */}
            {extractReceipt.isPending ? (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <LoadingSpinner /> Extracting receipt data...
              </div>
            ) : extraction ? (
              <div className="bg-emerald-50 rounded-lg p-4 space-y-2" data-testid="receipt-extraction-results">
                <div className="flex items-center gap-2 text-sm font-medium text-emerald-700">
                  <Check className="h-4 w-4" /> Extracted Data
                  <span className="text-xs text-emerald-500 ml-auto">
                    {(extraction.confidence * 100).toFixed(0)}% confidence
                  </span>
                </div>
                {extraction.amount !== null && (
                  <p className="text-sm" data-testid="extracted-amount">
                    <span className="text-slate-500">Amount:</span>{' '}
                    <span className="font-medium">${extraction.amount.toFixed(2)}</span>
                  </p>
                )}
                {extraction.vendor && (
                  <p className="text-sm" data-testid="extracted-vendor">
                    <span className="text-slate-500">Vendor:</span>{' '}
                    <span className="font-medium">{extraction.vendor}</span>
                  </p>
                )}
                {extraction.category && (
                  <p className="text-sm" data-testid="extracted-category">
                    <span className="text-slate-500">Category:</span>{' '}
                    <span className="font-medium">{extraction.category}</span>
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-slate-500">Could not extract data from receipt</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
