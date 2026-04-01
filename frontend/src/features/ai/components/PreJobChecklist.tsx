/**
 * PreJobChecklist Component
 *
 * Displays pre-job requirements for the Resource mobile view.
 * Shows job type, customer info, equipment, known issues,
 * gate code, special instructions, and estimated duration.
 * Includes confirmation checkboxes for equipment verification.
 */

import { useState } from 'react';
import {
  MapPin,
  Wrench,
  AlertTriangle,
  Key,
  FileText,
  Clock,
} from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────

export interface PreJobChecklistData {
  job_type: string;
  customer_name: string;
  customer_address: string;
  required_equipment: string[];
  known_issues: string[];
  gate_code: string | null;
  special_instructions: string | null;
  estimated_duration: number;
}

interface PreJobChecklistProps {
  checklist: PreJobChecklistData;
}

export function PreJobChecklist({ checklist }: PreJobChecklistProps) {
  const [checkedItems, setCheckedItems] = useState<Record<string, boolean>>({});

  const toggleItem = (item: string) => {
    setCheckedItems((prev) => ({ ...prev, [item]: !prev[item] }));
  };

  return (
    <div
      className="rounded-xl border border-slate-200 bg-white overflow-hidden"
      data-testid="prejob-checklist"
    >
      {/* Header */}
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
        <h4 className="font-semibold text-slate-800 text-sm">
          Pre-Job Checklist
        </h4>
        <p className="text-xs text-slate-500 mt-0.5">{checklist.job_type}</p>
      </div>

      <div className="p-4 space-y-3 text-sm">
        {/* Customer info */}
        <div className="flex items-start gap-2">
          <MapPin className="h-4 w-4 text-slate-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-medium text-slate-700">
              {checklist.customer_name}
            </p>
            <p className="text-slate-500 text-xs">
              {checklist.customer_address}
            </p>
          </div>
        </div>

        {/* Duration */}
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-slate-400 flex-shrink-0" />
          <span className="text-slate-600">
            Est. {checklist.estimated_duration} min
          </span>
        </div>

        {/* Gate code */}
        {checklist.gate_code && (
          <div className="flex items-center gap-2">
            <Key className="h-4 w-4 text-amber-500 flex-shrink-0" />
            <span className="text-slate-600">
              Gate code:{' '}
              <span className="font-mono font-medium">
                {checklist.gate_code}
              </span>
            </span>
          </div>
        )}

        {/* Special instructions */}
        {checklist.special_instructions && (
          <div className="flex items-start gap-2">
            <FileText className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
            <p className="text-slate-600">{checklist.special_instructions}</p>
          </div>
        )}

        {/* Known issues */}
        {checklist.known_issues.length > 0 && (
          <div>
            <div className="flex items-center gap-1 mb-1">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              <span className="font-medium text-slate-700 text-xs uppercase tracking-wide">
                Known Issues
              </span>
            </div>
            <ul className="ml-6 space-y-0.5">
              {checklist.known_issues.map((issue, i) => (
                <li key={i} className="text-slate-600 text-xs list-disc">
                  {issue}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Equipment verification */}
        {checklist.required_equipment.length > 0 && (
          <div>
            <div className="flex items-center gap-1 mb-2">
              <Wrench className="h-4 w-4 text-teal-500" />
              <span className="font-medium text-slate-700 text-xs uppercase tracking-wide">
                Required Equipment
              </span>
            </div>
            <div className="space-y-1.5">
              {checklist.required_equipment.map((item) => (
                <label
                  key={item}
                  className="flex items-center gap-2 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={!!checkedItems[item]}
                    onChange={() => toggleItem(item)}
                    className="h-4 w-4 rounded border-slate-300 text-teal-500 focus:ring-teal-400"
                    data-testid={`equipment-check-${item.toLowerCase().replace(/\s+/g, '-')}`}
                  />
                  <span
                    className={`text-xs ${checkedItems[item] ? 'text-slate-400 line-through' : 'text-slate-600'}`}
                  >
                    {item}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
