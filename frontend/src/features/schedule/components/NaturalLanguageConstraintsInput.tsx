/**
 * Natural Language Constraints Input Component.
 * Allows users to enter scheduling constraints in plain English.
 */

import { useState } from 'react';
import { X, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useConstraintParser } from '../hooks/useConstraintParser';
import type { ParsedConstraint } from '../types';

interface NaturalLanguageConstraintsInputProps {
  scheduleDate: string;
  onConstraintsChange: (constraints: ParsedConstraint[]) => void;
}

const EXAMPLE_CONSTRAINTS = [
  "Don't schedule Viktor before 10am",
  "Keep all winterizations together",
  "Only assign repairs to Vas",
  "Focus on Eden Prairie first",
];

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

  const getConstraintColor = (type: ParsedConstraint['type']) => {
    switch (type) {
      case 'staff_time':
        return 'bg-blue-100 text-blue-800';
      case 'job_grouping':
        return 'bg-green-100 text-green-800';
      case 'staff_restriction':
        return 'bg-purple-100 text-purple-800';
      case 'geographic':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-4" data-testid="constraints-input-container">
      <div>
        <label htmlFor="constraints-input" className="block text-sm font-medium mb-2">
          Scheduling Constraints (Optional)
        </label>
        <Textarea
          id="constraints-input"
          data-testid="constraints-input"
          placeholder={`Enter constraints in plain English, one per line:\n${EXAMPLE_CONSTRAINTS.join('\n')}`}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          rows={4}
          className="resize-none"
        />
        <Button
          data-testid="parse-constraints-btn"
          onClick={handleParse}
          disabled={!inputText.trim() || parseConstraints.isPending}
          className="mt-2"
          variant="outline"
        >
          {parseConstraints.isPending ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Parsing...
            </>
          ) : (
            'Parse Constraints'
          )}
        </Button>
      </div>

      {/* Parsed Constraints */}
      {constraints.length > 0 && (
        <div data-testid="parsed-constraints-section">
          <p className="text-sm font-medium mb-2">Active Constraints:</p>
          <div className="flex flex-wrap gap-2">
            {constraints.map((constraint, index) => (
              <Badge
                key={index}
                data-testid={`parsed-constraint-${index}`}
                className={`${getConstraintColor(constraint.type)} flex items-center gap-2`}
              >
                <span>{constraint.description}</span>
                <button
                  data-testid={`remove-constraint-${index}`}
                  onClick={() => handleRemoveConstraint(index)}
                  className="hover:bg-black/10 rounded-full p-0.5"
                  aria-label="Remove constraint"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Validation Errors */}
      {unparseable.length > 0 && (
        <Alert variant="destructive" data-testid="unparseable-text-alert">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <p className="font-medium mb-1">Could not parse:</p>
            <ul className="list-disc list-inside text-sm">
              {unparseable.map((text, index) => (
                <li key={index}>{text}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Invalid Constraints */}
      {constraints.some((c) => !c.is_valid) && (
        <Alert variant="destructive" data-testid="invalid-constraints-alert">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <p className="font-medium mb-1">Invalid constraints:</p>
            <ul className="list-disc list-inside text-sm">
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
        <Alert variant="destructive" data-testid="parse-error-alert">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to parse constraints. Please try again or contact support if the issue persists.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
