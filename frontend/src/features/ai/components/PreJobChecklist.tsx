/**
 * PreJobChecklist — Pre-job requirements display for Resource mobile view.
 */

import { useState } from 'react';
import type { PreJobChecklist as PreJobChecklistData } from '../types/aiScheduling';

interface PreJobChecklistProps {
  checklist: PreJobChecklistData;
}

export function PreJobChecklist({ checklist }: PreJobChecklistProps) {
  const [equipmentChecked, setEquipmentChecked] = useState<
    Record<string, boolean>
  >({});

  const toggleEquipment = (item: string) => {
    setEquipmentChecked((prev) => ({ ...prev, [item]: !prev[item] }));
  };

  const allChecked =
    checklist.required_equipment.length > 0 &&
    checklist.required_equipment.every((e) => equipmentChecked[e]);

  return (
    <div
      className="bg-white rounded-lg border border-gray-200 p-4 space-y-3"
      data-testid="prejob-checklist"
    >
      <h3 className="text-sm font-semibold text-gray-900">Pre-Job Checklist</h3>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        <span className="text-gray-500">Job Type</span>
        <span className="font-medium">{checklist.job_type}</span>

        <span className="text-gray-500">Customer</span>
        <span className="font-medium">{checklist.customer_name}</span>

        <span className="text-gray-500">Address</span>
        <span className="font-medium">{checklist.customer_address}</span>

        <span className="text-gray-500">Est. Duration</span>
        <span className="font-medium">{checklist.estimated_duration} min</span>
      </div>

      {checklist.gate_code && (
        <div className="bg-yellow-50 border border-yellow-200 rounded p-2 text-sm">
          <span className="font-medium text-yellow-800">Gate Code: </span>
          <span className="text-yellow-900">{checklist.gate_code}</span>
        </div>
      )}

      {checklist.known_issues && (
        <div className="bg-red-50 border border-red-200 rounded p-2 text-sm">
          <p className="font-medium text-red-800 mb-1">Known Issues</p>
          <p className="text-red-700">{checklist.known_issues}</p>
        </div>
      )}

      {checklist.special_instructions && (
        <div className="bg-blue-50 border border-blue-200 rounded p-2 text-sm">
          <p className="font-medium text-blue-800 mb-1">Special Instructions</p>
          <p className="text-blue-700">{checklist.special_instructions}</p>
        </div>
      )}

      {checklist.required_equipment.length > 0 && (
        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">
            Equipment Verification
          </p>
          <ul className="space-y-1">
            {checklist.required_equipment.map((item) => (
              <li key={item} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id={`equip-${item}`}
                  checked={!!equipmentChecked[item]}
                  onChange={() => toggleEquipment(item)}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label
                  htmlFor={`equip-${item}`}
                  className={`text-sm ${
                    equipmentChecked[item]
                      ? 'line-through text-gray-400'
                      : 'text-gray-700'
                  }`}
                >
                  {item}
                </label>
              </li>
            ))}
          </ul>
          {allChecked && (
            <p className="mt-2 text-sm text-green-600 font-medium">
              ✓ All equipment verified
            </p>
          )}
        </div>
      )}
    </div>
  );
}
