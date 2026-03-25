import { useState } from 'react';
import { Loader2, FileText } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useContractTemplates, useCreateContract } from '../hooks';

interface ContractCreatorProps {
  leadId: string;
  leadName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ContractCreator({ leadId, leadName, open, onOpenChange }: ContractCreatorProps) {
  const { data: templates } = useContractTemplates();
  const createContract = useCreateContract();
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [body, setBody] = useState('');
  const [terms, setTerms] = useState('');

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplateId(templateId);
    if (templateId === 'none') {
      setBody('');
      setTerms('');
      return;
    }
    const template = templates?.find((t) => t.id === templateId);
    if (template) {
      // Replace template variables
      const populatedBody = template.body
        .replace(/\{customer_name\}/g, leadName)
        .replace(/\{date\}/g, new Date().toLocaleDateString());
      setBody(populatedBody);
      setTerms(template.terms_and_conditions ?? '');
    }
  };

  const handleSubmit = async () => {
    if (!body.trim()) {
      toast.error('Contract body is required');
      return;
    }
    try {
      await createContract.mutateAsync({
        lead_id: leadId,
        template_id: selectedTemplateId !== 'none' ? selectedTemplateId : undefined,
        body,
        terms_and_conditions: terms || undefined,
      });
      toast.success('Contract Created', { description: 'Contract has been generated.' });
      onOpenChange(false);
      resetForm();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create contract';
      toast.error('Error', { description: msg });
    }
  };

  const resetForm = () => {
    setSelectedTemplateId('');
    setBody('');
    setTerms('');
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="contract-creator-dialog">
        <DialogHeader>
          <DialogTitle>Create Contract</DialogTitle>
          <DialogDescription>
            Select a template or write a custom contract for {leadName}.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Template Selector */}
          <div>
            <label className="text-sm font-medium text-slate-700 mb-1.5 block">Template</label>
            <Select value={selectedTemplateId} onValueChange={handleTemplateSelect}>
              <SelectTrigger data-testid="contract-template-select">
                <SelectValue placeholder="Select a template..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No Template (Custom)</SelectItem>
                {templates?.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    {t.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Contract Body */}
          <div>
            <label className="text-sm font-medium text-slate-700 mb-1.5 block">Contract Body</label>
            <Textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Enter contract content..."
              rows={10}
              data-testid="contract-body"
            />
          </div>

          {/* Terms and Conditions */}
          <div>
            <label className="text-sm font-medium text-slate-700 mb-1.5 block">
              Terms & Conditions
            </label>
            <Textarea
              value={terms}
              onChange={(e) => setTerms(e.target.value)}
              placeholder="Terms and conditions..."
              rows={4}
              data-testid="contract-terms"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={createContract.isPending || !body.trim()}
            data-testid="create-contract-btn"
          >
            {createContract.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <FileText className="mr-2 h-4 w-4" />
            )}
            Create Contract
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
