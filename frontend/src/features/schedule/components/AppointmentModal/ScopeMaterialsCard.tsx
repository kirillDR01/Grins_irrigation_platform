/**
 * ScopeMaterialsCard — job scope, duration/staff/priority pills, materials.
 * Requirements: 9.1, 9.2, 9.3
 */

interface ScopeMaterialsCardProps {
  scope: string;
  durationMinutes?: number | null;
  staffCount?: number | null;
  priority?: number | null;
  materials?: string[];
}

export function ScopeMaterialsCard({
  scope,
  durationMinutes,
  staffCount,
  priority,
  materials,
}: ScopeMaterialsCardProps) {
  const hasMaterials = materials && materials.length > 0;

  return (
    <div className="rounded-[14px] border border-[#E5E7EB] bg-white px-4 py-3 space-y-3">
      {/* Notes (was: Scope) */}
      <div>
        <p className="text-[10px] font-extrabold tracking-[0.6px] text-[#9CA3AF] uppercase mb-1.5">
          Notes
        </p>
        <p className="text-[17px] font-extrabold text-[#0B1220] leading-snug">{scope}</p>
      </div>

      {/* Pills row */}
      <div className="flex flex-wrap gap-2">
        {durationMinutes != null && (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-gray-100 text-gray-700 text-[12px] font-bold border border-gray-200">
            ~{durationMinutes} min
          </span>
        )}
        {staffCount != null && (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-gray-100 text-gray-700 text-[12px] font-bold border border-gray-200">
            {staffCount} tech{staffCount !== 1 ? 's' : ''}
          </span>
        )}
        {priority != null && priority > 0 && (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 text-[12px] font-bold border border-amber-200">
            Priority {priority}
          </span>
        )}
      </div>

      {/* Materials */}
      {hasMaterials && (
        <div>
          <p className="text-[10px] font-extrabold tracking-[0.6px] text-[#9CA3AF] uppercase mb-1.5">
            Materials
          </p>
          <div className="flex flex-wrap gap-1.5">
            {materials.map((m) => (
              <span
                key={m}
                className="inline-flex items-center px-2.5 py-1 rounded-full bg-gray-100 text-gray-700 text-[12px] font-semibold border border-gray-200"
              >
                {m}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
