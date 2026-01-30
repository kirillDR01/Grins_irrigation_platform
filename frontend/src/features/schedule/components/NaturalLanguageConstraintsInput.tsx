/**
 * Natural Language Constraints Input Component.
 * Allows users to enter scheduling constraints in plain English.
 */

import { useState } from 'react';
import { X, Loader2, AlertCircle, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useConstraintParser } from '../hooks/useConstraintParser';
import type { ParsedConstraint } from '../types';

interface NaturalLanguageConstraintsInputProps {
  scheduleDate: string;
  onConstraintsChange: (constraints: ParsedConstraint[]) => void;
}

const EXAMPLE_CONSTRAINT = "e.g., 'No jobs before 9am' or 'Prioritize Eden Prairie'";

export function NaturalLanguageConstraintsInput({
  scheduleDate,
  onConstraintsChange,
}: NaturalLanguageConstraintsInputProps) {
  const [inputText, setInputText] = useState('');
  const [constraints, setConstraints] = useState<ParsedConstraint[]>([]);
  const [unparseable, setUnparseable] = useState<string[]>([]);

  const parseConstraints = useConstraintParser();

  const handleParse = async () => {
    if (!inputText.trim()) return;

    try {
      const result = await parseConstraints.mutateAsync({
        constraint_text: inputText,
      });

      const validConstraints = result.constraints.filter(
        (c) => c.validation_errors.length === 0
      );
      setConstraints(validConstraints);
      const unparseableList = result.unparseable_text ? [result.unparseable_text] : [];
      setUnparseable(unparseableList);
      onConstraintsChange(validConstraints);
      setInputText('');
    } catch (error) {
      console.error('Failed to parse constraints:', error);
    }
  };

  const handleRemoveConstraint = (index: number) => {
    const updated = constraints.filter((_, i) => i !== index);
    setConstraints(updated);
    onConstraintsChange(updated);
  };

  return (
    <div className="space-y-4" data-testid="constraints-input-container">
      {/* Input Container - bg-slate-50 rounded-xl p-4 */}
      <div className="bg-slate-50 rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="h-4 w-4 text-teal-500" />
          <label htmlFor="constraints-input" className="text-sm font-medium text-slate-700">
            Scheduling Constraints (Optional)
          </label>
        </div>
        <Textarea
          id="constraints-input"
          data-testid="constraints-input"
          placeholder={EXAMPLE_CONSTRAINT}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          rows={2}
          className="resize-none bg-white border-slate-200 rounded-lg text-slate-700 text-sm placeholder-slate-400 focus:border-teal-500 focus:ring-2 focus:ring-teal-100"
        />
        <Button
          data-testid="parse-constraints-btn"
          onClick={handleParse}
          disabled={!inputText.trim() || parseConstraints.isPending}
          className="mt-3 text-teal-600 hover:text-teal-700 text-sm font-medium bg-transparent hover:bg-teal-50 border-0 shadow-none p-0 h-auto"
          variant="ghost"
        >
          {parseConstraints.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin text-teal-500" />
              Parsing...
            </>
          ) : (
            <>
              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              Add Constraint
            </>
          )}
        </Button>
      </div>

      {/* Parsed Constraints - Chips */}
      {constraints.length > 0 && (
        <div data-testid="parsed-constraints-section">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Active Constraints:
          </p>
          <div className="flex flex-wrap gap-2">
            {constraints.map((constraint, index) => (
              <div
                key={index}
                data-testid={`parsed-constraint-${index}`}
                className="bg-white px-3 py-1.5 rounded-full text-sm border border-slate-200 flex items-center gap-2 text-slate-700"
              >
                <span>{constraint.description}</span>
                <button
                  data-testid={`remove-constraint-btn`}
                  onClick={() => handleRemoveConstraint(index)}
                  className="text-slate-400 hover:text-slate-600 transition-colors"
                  aria-label="Remove constraint"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Validation Errors */}
      {unparseable.length > 0 && (
        <Alert variant="destructive" data-testid="unparseable-text-alert" className="bg-white rounded-xl shadow-sm border-l-4 border-l-red-400 border-t-slate-100 border-r-slate-100 border-b-slate-100">
          <AlertCircle className="h-4 w-4 text-red-500" />
          <AlertDescription>
            <p className="font-medium text-slate-800 mb-1">Could not parse:</p>
            <ul className="list-disc list-inside text-sm text-slate-500">
              {unparseable.map((text, index) => (
                <li key={index}>{text}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Invalid Constraints */}
      {constraints.some((c) => !c.is_valid) && (
        <Alert variant="destructive" data-testid="invalid-constraints-alert" className="bg-white rounded-xl shadow-sm border-l-4 border-l-amber-400 border-t-slate-100 border-r-slate-100 border-b-slate-100">
          <AlertCircle className="h-4 w-4 text-amber-500" />
          <AlertDescription>
            <p className="font-medium text-slate-800 mb-1">Invalid constraints:</p>
            <ul className="list-disc list-inside text-sm text-slate-500">
              {constraints
                .filter((c) => !c.is_valid)
                .map((c, index) => (
                  <li key={index}>
                    {c.description}: {c.validation_error}
                  </li>
                ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {parseConstraints.isError && (
        <Alert variant="destructive" data-testid="parse-error-alert" className="bg-white rounded-xl shadow-sm border-l-4 border-l-red-400 border-t-slate-100 border-r-slate-100 border-b-slate-100">
          <AlertCircle className="h-4 w-4 text-red-500" />
          <AlertDescription className="text-slate-500 text-sm">
            Failed to parse constraints. Please try again or contact support if the issue persists.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
