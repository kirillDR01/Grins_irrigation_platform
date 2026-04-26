/**
 * CustomerHero — teal header strip with avatar, name, tags, phone, email.
 * Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
 */

import { Mail, Phone } from 'lucide-react';
import { TagChip } from '@/shared/components/TagChip';
import type { CustomerTag } from '../../types';

interface CustomerHeroProps {
  customerId: string;
  firstName: string;
  lastName: string;
  phone: string;
  email?: string | null;
  tags?: CustomerTag[];
  historySummary?: string | null;
}

export function CustomerHero({
  firstName,
  lastName,
  phone,
  email,
  tags,
  historySummary,
}: CustomerHeroProps) {
  const initials = `${firstName[0] ?? ''}${lastName[0] ?? ''}`.toUpperCase();
  const hasTags = tags && tags.length > 0;

  return (
    <div className="rounded-[14px] overflow-hidden border border-[#E5E7EB]">
      {/* Teal header strip */}
      <div className="bg-teal-600 px-4 py-3 flex items-center gap-3">
        <div className="w-11 h-11 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
          <span className="text-white text-[15px] font-extrabold">{initials}</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-white text-[18px] font-extrabold leading-tight">
            {firstName} {lastName}
          </p>
          {historySummary && (
            <p className="text-teal-100 text-[12px] font-semibold mt-0.5">{historySummary}</p>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="bg-white px-4 py-3 space-y-2.5">
        {/* Tags row */}
        {hasTags && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-extrabold tracking-[0.6px] text-[#9CA3AF] uppercase">
              Tags
            </span>
            {tags.map((tag) => (
              <TagChip key={tag.id} label={tag.label} tone={tag.tone} />
            ))}
          </div>
        )}

        {/* Phone row */}
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-[8px] bg-blue-50 flex items-center justify-center flex-shrink-0">
            <Phone size={14} className="text-blue-600" strokeWidth={2.2} />
          </div>
          <a
            href={`tel:${phone}`}
            className="text-[17px] font-extrabold text-[#0B1220] font-mono tracking-[-0.3px] hover:text-blue-600"
          >
            {phone}
          </a>
          <a
            href={`tel:${phone}`}
            className="ml-auto inline-flex items-center justify-center min-h-[44px] min-w-[44px] px-4 py-2 rounded-full bg-blue-50 text-blue-700 text-[12px] font-bold border border-blue-200 hover:bg-blue-100"
          >
            Call
          </a>
        </div>

        {/* Email row */}
        {email && (
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-[8px] bg-gray-100 flex items-center justify-center flex-shrink-0">
              <Mail size={14} className="text-gray-500" strokeWidth={2.2} />
            </div>
            <a
              href={`mailto:${email}`}
              className="text-[14px] font-semibold text-[#374151] hover:text-blue-600 truncate"
            >
              {email}
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
