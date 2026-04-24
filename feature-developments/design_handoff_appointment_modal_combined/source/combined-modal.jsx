// Combined modal — forks modal.jsx with:
//  - "AI draft" button removed
//  - "Edit tags" button added next to Review
//  - "Get directions" now toggles a small popover (Apple Maps / Google Maps)
//  - Customer tags row (editable, permeates to customer + future jobs)
// Plus: one canvas showing BOTH payment & estimate sheets in their flows.

const ck_ink   = '#0B1220';
const ck_ink2  = '#1F2937';
const ck_ink3  = '#4B5563';
const ck_ink4  = '#6B7280';
const ck_line  = '#E5E7EB';
const ck_line2 = '#F3F4F6';
const ck_surf  = '#FFFFFF';
const ck_soft  = '#F9FAFB';

const ck_blue     = '#1D4ED8';
const ck_blueBg   = '#DBEAFE';
const ck_orange   = '#C2410C';
const ck_orangeBg = '#FFEDD5';
const ck_green    = '#047857';
const ck_greenBg  = '#D1FAE5';
const ck_teal     = '#0F766E';
const ck_tealBg   = '#CCFBF1';
const ck_red      = '#B91C1C';
const ck_amber    = '#B45309';
const ck_amberBg  = '#FEF3C7';
const ck_violet   = '#6D28D9';
const ck_violetBg = '#EDE9FE';

const ck_fontUI   = '"Inter", -apple-system, system-ui, sans-serif';
const ck_fontMono = '"JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace';

function CKIcon({ d, size = 16, stroke = 'currentColor', fill = 'none', sw = 2 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={stroke} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
      {typeof d === 'string' ? <path d={d}/> : d}
    </svg>
  );
}

const CI = {
  phone: 'M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92Z',
  mail: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 7 9-7"/></>,
  pin: <><path d="M20 10c0 7-8 12-8 12S4 17 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="3"/></>,
  nav: 'M2 11l20-9-9 20-2-9-9-2Z',
  play: 'M5 3l14 9-14 9V3Z',
  check: 'M4 12l5 5 11-11',
  checkC: <><circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/></>,
  star: 'M12 2 15 9l7 .7-5.3 4.8 1.7 7.1L12 18l-6.4 3.6 1.7-7.1L2 9.7 9 9l3-7Z',
  card: <><rect x="2" y="6" width="20" height="12" rx="2"/><path d="M2 11h20M6 15h4"/></>,
  box: <><path d="M3 7l9-4 9 4v10l-9 4-9-4V7Z"/><path d="M3 7l9 4 9-4M12 11v10"/></>,
  doc: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h5"/></>,
  pencil: 'M11 4h-7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7M18.5 2.5a2.1 2.1 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5Z',
  x: 'M18 6 6 18M6 6l12 12',
  alert: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5M12 16v.5"/></>,
  tools: <><path d="M14.7 6.3a3 3 0 0 0-4.2 4.2L3 18l3 3 7.5-7.5a3 3 0 0 0 4.2-4.2l-1.8 1.8L14 9l1.5-1.5-0.8-1.2Z"/></>,
  photo: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 16 5-5 4 4 3-3 6 6"/><circle cx="9" cy="10" r="1.5"/></>,
  user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
  tag: 'M20.59 13.41 13.42 20.58a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82zM7 7h.01',
  plus: 'M12 5v14M5 12h14',
  ext: <><path d="M14 3h7v7"/><path d="M10 14 21 3"/><path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5"/></>,
};

function CKPill({ children, bg, color, size = 'md' }) {
  const pad = size === 'lg' ? '4px 12px' : '3px 10px';
  const fs = size === 'lg' ? 13 : 12;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      background: bg, color, padding: pad, borderRadius: 999,
      fontSize: fs, fontWeight: 700, lineHeight: 1.4, fontFamily: ck_fontUI,
      whiteSpace: 'nowrap', flexShrink: 0,
    }}>{children}</span>
  );
}

function CKStatusBadge({ step }) {
  if (step === 0) return <CKPill bg={ck_blueBg} color={ck_blue} size="lg">Scheduled</CKPill>;
  if (step === 1) return <CKPill bg={ck_blueBg} color={ck_blue} size="lg">On the way</CKPill>;
  if (step === 2) return <CKPill bg={ck_orangeBg} color={ck_orange} size="lg">On site</CKPill>;
  return <CKPill bg={ck_greenBg} color={ck_green} size="lg">Complete</CKPill>;
}

function CKBigAction({ bg, icon, label, sub, done, disabled }) {
  const st = done
    ? { background: '#fff', color: ck_green, border: `2px solid ${ck_green}` }
    : { background: bg, color: '#fff', border: `2px solid ${bg}` };
  return (
    <button style={{
      flex: 1, minWidth: 0, ...st, borderRadius: 14,
      padding: '14px 10px', minHeight: 104,
      cursor: disabled ? 'not-allowed' : 'pointer',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: 6, fontFamily: ck_fontUI, textAlign: 'center', opacity: disabled ? 0.4 : 1,
      boxShadow: done ? 'none' : disabled ? 'none' : '0 1px 0 rgba(0,0,0,0.1), 0 4px 8px rgba(0,0,0,0.06)',
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: 18,
        background: done ? '#fff' : 'rgba(255,255,255,0.18)',
        color: done ? ck_green : '#fff',
        border: done ? `2px solid ${ck_green}` : 'none',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <CKIcon d={done ? CI.check : icon} size={20} sw={2.6}/>
      </div>
      <span style={{ fontSize: 15, fontWeight: 800, letterSpacing: -0.2, whiteSpace: 'nowrap', lineHeight: 1 }}>{label}</span>
      <span style={{
        fontSize: 12, fontWeight: 700, fontFamily: done ? ck_fontMono : ck_fontUI,
        opacity: done ? 1 : 0.9, letterSpacing: -0.1, lineHeight: 1, whiteSpace: 'nowrap',
      }}>{sub}</span>
    </button>
  );
}

function CKActionTrack({ step }) {
  return (
    <div style={{ display: 'flex', gap: 8 }}>
      <CKBigAction bg={ck_blue} icon={CI.nav} label="On my way" sub={step >= 1 ? '8:42 AM' : 'Text customer'} done={step >= 1}/>
      <CKBigAction bg={ck_orange} icon={CI.play} label="Job started" sub={step >= 2 ? '9:06 AM' : 'Log arrival'} done={step >= 2} disabled={step < 1}/>
      <CKBigAction bg={ck_green} icon={CI.checkC} label="Job complete" sub={step >= 3 ? '10:48 AM' : 'Close out'} done={step >= 3} disabled={step < 2}/>
    </div>
  );
}

function CKLinkBtn({ icon, children, color = ck_ink, bg = '#fff', border = ck_line, onClick, active }) {
  return (
    <button onClick={onClick} style={{
      minHeight: 44, padding: '0 14px', borderRadius: 12,
      background: active ? ck_violetBg : bg,
      color: active ? ck_violet : color,
      border: `1.5px solid ${active ? ck_violet : border}`,
      fontSize: 14, fontWeight: 700, fontFamily: ck_fontUI, cursor: 'pointer',
      display: 'inline-flex', alignItems: 'center', gap: 6, position: 'relative',
    }}>
      {icon && <CKIcon d={icon} size={16} sw={2.2}/>}
      {children}
    </button>
  );
}

function CKTimelineStrip({ step }) {
  const dots = [
    { label: 'Booked', time: '9:00' },
    { label: 'En route', time: step >= 1 ? '8:42' : '—' },
    { label: 'On site', time: step >= 2 ? '9:06' : '—' },
    { label: 'Done', time: step >= 3 ? '10:48' : '—' },
  ];
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 0, padding: '6px 0' }}>
      {dots.map((d, i) => {
        const active = i <= step;
        const now = i === step && step < 3;
        return (
          <React.Fragment key={i}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0, minWidth: 72 }}>
              <div style={{
                width: 22, height: 22, borderRadius: 11,
                background: active ? ck_ink : '#fff',
                border: `2px solid ${active ? ck_ink : ck_line}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#fff', boxShadow: now ? `0 0 0 4px ${ck_blueBg}` : 'none',
              }}>
                {active && !now && <CKIcon d={CI.check} size={12} sw={3.2}/>}
                {now && <div style={{ width: 8, height: 8, borderRadius: 4, background: ck_blue }}/>}
              </div>
              <div style={{ fontSize: 12.5, fontWeight: 700, color: active ? ck_ink : ck_ink4, marginTop: 8, whiteSpace: 'nowrap' }}>{d.label}</div>
              <div style={{ fontSize: 11.5, fontFamily: ck_fontMono, fontWeight: 600, color: ck_ink4, marginTop: 1, whiteSpace: 'nowrap' }}>{d.time}</div>
            </div>
            {i < dots.length - 1 && (
              <div style={{ flex: 1, minWidth: 12, height: 2, background: i < step ? ck_ink : ck_line, marginTop: 10 }}/>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// Tag chip with removable X when editing
function CKTagChip({ children, tone = 'neutral', onRemove }) {
  const tones = {
    neutral: { bg: ck_line2, color: ck_ink2, border: ck_line },
    blue: { bg: ck_blueBg, color: ck_blue, border: '#93C5FD' },
    green: { bg: ck_greenBg, color: ck_green, border: '#86EFAC' },
    amber: { bg: ck_amberBg, color: ck_amber, border: '#FCD34D' },
    violet: { bg: ck_violetBg, color: ck_violet, border: '#C4B5FD' },
  };
  const t = tones[tone] || tones.neutral;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: onRemove ? '5px 6px 5px 10px' : '5px 10px',
      borderRadius: 999, background: t.bg, color: t.color,
      border: `1.5px solid ${t.border}`,
      fontSize: 12.5, fontWeight: 800, letterSpacing: -0.1, fontFamily: ck_fontUI,
      whiteSpace: 'nowrap',
    }}>
      {children}
      {onRemove && (
        <button style={{
          width: 18, height: 18, borderRadius: 10, border: 'none',
          background: 'rgba(0,0,0,0.08)', color: t.color, cursor: 'pointer',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        }}><CKIcon d={CI.x} size={11} sw={3}/></button>
      )}
    </span>
  );
}

// Maps directions popover — a little menu anchored above the button
function CKDirectionsPopover() {
  const row = (label, sub, bg, color) => (
    <button style={{
      width: '100%', display: 'flex', alignItems: 'center', gap: 12,
      padding: '12px 14px', background: '#fff', border: 'none',
      cursor: 'pointer', textAlign: 'left', fontFamily: ck_fontUI,
      borderBottom: `1px solid ${ck_line}`,
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: 10, background: bg, color,
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        <CKIcon d={CI.nav} size={18} sw={2.4}/>
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14.5, fontWeight: 800, color: ck_ink, letterSpacing: -0.2 }}>{label}</div>
        <div style={{ fontSize: 12.5, fontWeight: 600, color: ck_ink4 }}>{sub}</div>
      </div>
      <CKIcon d={CI.ext} size={14} stroke={ck_ink4} sw={2.2}/>
    </button>
  );
  return (
    <div style={{
      position: 'absolute', left: 16, right: 16, bottom: 'calc(100% + 8px)',
      borderRadius: 14, background: '#fff',
      border: `1.5px solid ${ck_line}`, overflow: 'hidden',
      boxShadow: '0 20px 40px rgba(10,15,30,0.18), 0 4px 8px rgba(10,15,30,0.08)',
      zIndex: 5,
    }}>
      <div style={{
        padding: '10px 14px', background: ck_soft, borderBottom: `1px solid ${ck_line}`,
        fontSize: 11.5, fontWeight: 800, color: ck_ink4, textTransform: 'uppercase', letterSpacing: 1,
      }}>
        Open in
      </div>
      {row('Apple Maps', 'Default iOS maps app', '#CCFBF1', '#0F766E')}
      <div style={{ marginTop: -1 }}>{row('Google Maps', 'Opens in Google Maps app', '#DBEAFE', '#1D4ED8')}</div>
      <div style={{ padding: '8px 10px', background: ck_soft, borderTop: `1px solid ${ck_line}` }}>
        <button style={{
          width: '100%', padding: '8px', background: 'transparent', border: 'none',
          fontSize: 12.5, fontWeight: 700, color: ck_ink4, cursor: 'pointer',
          fontFamily: ck_fontUI,
        }}>Remember my choice</button>
      </div>
    </div>
  );
}

// Tag editor bottom sheet
function CKTagEditor({ tags, onClose }) {
  const suggested = ['Repeat customer', 'Commercial', 'Difficult access', 'Dog on property', 'Prefers text', 'Gate code needed', 'Corner lot'];
  return (
    <div style={{
      width: 560, background: ck_surf, borderRadius: 20, overflow: 'hidden',
      border: `1px solid ${ck_line}`,
      boxShadow: '0 30px 60px rgba(10,15,30,0.14), 0 4px 12px rgba(10,15,30,0.05)',
      fontFamily: ck_fontUI, color: ck_ink, display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0 4px' }}>
        <div style={{ width: 44, height: 5, borderRadius: 3, background: ck_line }}/>
      </div>
      <div style={{ padding: '4px 20px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5, color: ck_ink, lineHeight: 1.1 }}>Edit tags</div>
          <div style={{ fontSize: 13.5, fontWeight: 600, color: ck_ink3, marginTop: 3 }}>
            Tags apply to Test User across every job — past and future
          </div>
        </div>
        <button style={{
          width: 44, height: 44, borderRadius: 12, border: `1.5px solid ${ck_line}`,
          background: '#fff', color: ck_ink2, cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}><CKIcon d={CI.x} size={20} sw={2.4}/></button>
      </div>

      <div style={{ padding: '0 20px 20px', flex: 1, overflow: 'auto' }}>
        <div style={{ fontSize: 12, fontWeight: 800, color: ck_ink4, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
          Current tags
        </div>
        <div style={{
          padding: '12px', borderRadius: 12, background: ck_soft, border: `1.5px solid ${ck_line}`,
          display: 'flex', flexWrap: 'wrap', gap: 8, minHeight: 58, alignItems: 'center',
        }}>
          {tags.map((t, i) => (
            <CKTagChip key={i} tone={t.tone} onRemove>{t.label}</CKTagChip>
          ))}
          <button style={{
            padding: '5px 10px', borderRadius: 999,
            border: `1.5px dashed ${ck_ink4}`, background: 'transparent',
            color: ck_ink3, fontSize: 12.5, fontWeight: 700, cursor: 'pointer',
            fontFamily: ck_fontUI, display: 'inline-flex', alignItems: 'center', gap: 4,
          }}>
            <CKIcon d={CI.plus} size={12} sw={3}/>
            Add custom
          </button>
        </div>

        <div style={{ fontSize: 12, fontWeight: 800, color: ck_ink4, textTransform: 'uppercase', letterSpacing: 1, margin: '18px 0 10px' }}>
          Suggested
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {suggested.map((s, i) => (
            <button key={i} style={{
              padding: '8px 12px', borderRadius: 999, background: '#fff',
              border: `1.5px solid ${ck_line}`, color: ck_ink2,
              fontSize: 13, fontWeight: 700, cursor: 'pointer', fontFamily: ck_fontUI,
              display: 'inline-flex', alignItems: 'center', gap: 6,
            }}>
              <CKIcon d={CI.plus} size={12} sw={3}/>
              {s}
            </button>
          ))}
        </div>

        <div style={{
          marginTop: 18, padding: 14, borderRadius: 12,
          background: ck_blueBg, border: `1.5px solid ${ck_blue}`,
          display: 'flex', alignItems: 'flex-start', gap: 10,
        }}>
          <div style={{
            width: 28, height: 28, borderRadius: 14, background: ck_blue, color: '#fff', flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <CKIcon d={CI.user} size={14} sw={2.4}/>
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: ck_blue, lineHeight: 1.45 }}>
            Changes save to Test User's customer profile. Next job auto-inherits these tags — techs will see them on the route card.
          </div>
        </div>
      </div>

      <div style={{
        padding: '14px 20px 18px', background: ck_soft,
        borderTop: `1px solid ${ck_line}`, display: 'flex', gap: 10,
      }}>
        <button style={{
          flex: 1, minHeight: 52, borderRadius: 12, background: '#fff',
          border: `2px solid ${ck_line}`, color: ck_ink2, cursor: 'pointer',
          fontFamily: ck_fontUI, fontSize: 15, fontWeight: 800,
        }}>Cancel</button>
        <button style={{
          flex: 2, minHeight: 52, borderRadius: 12, background: ck_ink,
          border: `2px solid ${ck_ink}`, color: '#fff', cursor: 'pointer',
          fontFamily: ck_fontUI, fontSize: 15, fontWeight: 800,
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        }}>
          <CKIcon d={CI.check} size={18} sw={2.6}/>
          Save tags · applies everywhere
        </button>
      </div>
    </div>
  );
}

function CKRow({ icon, label, value, right, strong }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '14px 16px', borderBottom: `1px solid ${ck_line}`, background: '#fff',
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: 10, background: ck_soft, color: ck_ink3,
        flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <CKIcon d={icon} size={18}/>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        {label && <div style={{ fontSize: 11.5, fontWeight: 700, color: ck_ink4, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 2 }}>{label}</div>}
        <div style={{
          fontSize: strong ? 17 : 15, fontWeight: strong ? 800 : 600,
          color: ck_ink, lineHeight: 1.25, letterSpacing: -0.2,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>{value}</div>
      </div>
      {right}
    </div>
  );
}

// ─── THE COMBINED MODAL ─────────────────────────────────────

function CombinedModal({ step = 2, showMapsPopover = false, showEstimate = true, showTagsEditMode = false, tags: propTags }) {
  const defaultTags = [
    { label: 'Repeat customer', tone: 'green' },
    { label: 'Back gate — side yard', tone: 'amber' },
    { label: 'Prefers text', tone: 'blue' },
  ];
  const tags = propTags || defaultTags;
  return (
    <div style={{
      width: 560, background: ck_surf,
      borderRadius: 18, overflow: 'hidden',
      border: `1px solid ${ck_line}`,
      boxShadow: '0 30px 60px rgba(10,15,30,0.12), 0 4px 12px rgba(10,15,30,0.05)',
      fontFamily: ck_fontUI, color: ck_ink,
    }}>
      {/* Header */}
      <div style={{ padding: '20px 20px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
              <CKStatusBadge step={step}/>
              <CKPill bg={ck_line2} color={ck_ink2}>Residential</CKPill>
              <CKPill bg={ck_line2} color={ck_ink2}>#APT-2086</CKPill>
            </div>
            <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: -0.8, color: ck_ink, lineHeight: 1.1 }}>
              Spring startup · zone check
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, color: ck_ink3, marginTop: 6 }}>
              Thu, Apr 23 · 9:00 – 10:30 AM
            </div>
          </div>
          <button style={{
            width: 40, height: 40, borderRadius: 12, border: `1.5px solid ${ck_line}`,
            background: '#fff', color: ck_ink2, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}><CKIcon d={CI.x} size={18} sw={2.4}/></button>
        </div>
      </div>

      {/* Timeline */}
      <div style={{ padding: '4px 20px 16px' }}>
        <CKTimelineStrip step={step}/>
      </div>

      {/* Primary actions */}
      <div style={{
        padding: '16px 20px 16px', background: ck_soft,
        borderTop: `1px solid ${ck_line}`, borderBottom: `1px solid ${ck_line}`,
      }}>
        <div style={{ fontSize: 12, fontWeight: 800, color: ck_ink3, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
          On-site operations
        </div>
        <CKActionTrack step={step}/>
        {/* Secondary row — AI draft REMOVED, Edit tags ADDED */}
        <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
          <CKLinkBtn icon={CI.photo}>Add photo</CKLinkBtn>
          <CKLinkBtn icon={CI.doc}>Notes</CKLinkBtn>
          <CKLinkBtn icon={CI.star}>Review</CKLinkBtn>
          <CKLinkBtn icon={CI.tag} active={showTagsEditMode}>Edit tags</CKLinkBtn>
        </div>
      </div>

      {/* Collect payment + Send estimate — both combined */}
      <div style={{ padding: '16px 20px 0', display: 'flex', flexDirection: 'column', gap: 10 }}>
        <button style={{
          width: '100%', minHeight: 60, borderRadius: 14,
          background: '#fff', border: `2px solid ${ck_teal}`,
          color: ck_teal, fontFamily: ck_fontUI, fontWeight: 800, fontSize: 16,
          cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          padding: '0 16px',
        }}>
          <CKIcon d={CI.card} size={22} sw={2.2}/>
          Collect payment
        </button>
        {showEstimate && (
          <button style={{
            width: '100%', minHeight: 60, borderRadius: 14,
            background: '#fff', border: `2px solid ${ck_violet}`,
            color: ck_violet, fontFamily: ck_fontUI, fontWeight: 800, fontSize: 16,
            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
            padding: '0 16px',
          }}>
            <CKIcon d={CI.doc} size={22} sw={2.2}/>
            Send estimate
          </button>
        )}
      </div>

      {/* Customer hero */}
      <div style={{ margin: '16px 20px 16px', borderRadius: 14, border: `1.5px solid ${ck_line}`, overflow: 'hidden' }}>
        <div style={{
          padding: '14px 16px', background: ck_tealBg,
          display: 'flex', alignItems: 'center', gap: 12,
          borderBottom: `1px solid ${ck_line}`,
        }}>
          <div style={{
            width: 44, height: 44, borderRadius: 22, background: '#fff',
            color: ck_teal, display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 800, fontSize: 16, border: `2px solid ${ck_teal}`,
          }}>TU</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: ck_ink, letterSpacing: -0.3 }}>Test User</div>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: ck_ink3 }}>1 previous job · Last service Oct 2025</div>
          </div>
        </div>

        {/* Tags row — NEW — shows current customer tags inline */}
        <div style={{
          padding: '12px 16px', background: '#fff',
          borderBottom: `1px solid ${ck_line}`,
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <div style={{ fontSize: 11.5, fontWeight: 800, color: ck_ink4, textTransform: 'uppercase', letterSpacing: 0.8, flexShrink: 0 }}>
            Tags
          </div>
          <div style={{ flex: 1, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {tags.map((t, i) => <CKTagChip key={i} tone={t.tone}>{t.label}</CKTagChip>)}
          </div>
        </div>

        <a href="tel:9527373312" style={{
          display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px',
          textDecoration: 'none', color: ck_ink, background: '#fff',
          borderBottom: `1px solid ${ck_line}`,
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10, background: ck_blueBg, color: ck_blue, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><CKIcon d={CI.phone} size={18}/></div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11.5, fontWeight: 700, color: ck_ink4, textTransform: 'uppercase', letterSpacing: 0.8 }}>Phone</div>
            <div style={{ fontSize: 17, fontWeight: 800, fontFamily: ck_fontMono, color: ck_ink, letterSpacing: -0.2 }}>(952) 737-3312</div>
          </div>
          <div style={{
            padding: '8px 14px', background: ck_blue, color: '#fff', borderRadius: 10,
            fontWeight: 800, fontSize: 13, minHeight: 36, display: 'flex', alignItems: 'center', gap: 4,
          }}>
            <CKIcon d={CI.phone} size={14} sw={2.4}/> Call
          </div>
        </a>
        <a href="#" style={{
          display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px',
          textDecoration: 'none', color: ck_ink, background: '#fff',
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10, background: ck_soft, color: ck_ink3, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><CKIcon d={CI.mail} size={18}/></div>
          <div style={{ fontSize: 14, fontWeight: 600, color: ck_ink2 }}>test@example.com</div>
        </a>
      </div>

      {/* Location with Get directions popover */}
      <div style={{
        margin: '0 20px 16px', borderRadius: 14, border: `1.5px solid ${ck_line}`,
        overflow: showMapsPopover ? 'visible' : 'hidden', position: 'relative',
      }}>
        <div style={{ padding: '14px 16px', background: '#fff' }}>
          <div style={{ fontSize: 11.5, fontWeight: 700, color: ck_ink4, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
            <CKIcon d={CI.pin} size={12} stroke={ck_ink4}/> Property
          </div>
          <div style={{ fontSize: 19, fontWeight: 800, color: ck_ink, letterSpacing: -0.3, lineHeight: 1.2 }}>
            1 Test Street
          </div>
          <div style={{ fontSize: 15, fontWeight: 600, color: ck_ink2, marginTop: 2 }}>
            Eden Prairie, MN 55344
          </div>
        </div>
        <div style={{ position: 'relative' }}>
          {showMapsPopover && <CKDirectionsPopover/>}
          <button style={{
            width: '100%', padding: '14px 16px',
            background: ck_blue, color: '#fff', border: 'none',
            fontFamily: ck_fontUI, fontSize: 16, fontWeight: 800,
            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            minHeight: 52, borderBottomLeftRadius: 12, borderBottomRightRadius: 12,
          }}>
            <CKIcon d={CI.nav} size={20} sw={2.4}/>
            Get directions
          </button>
        </div>
      </div>

      {/* Job scope & materials */}
      <div style={{ margin: '0 20px 16px', borderRadius: 14, border: `1.5px solid ${ck_line}`, overflow: 'hidden', background: '#fff' }}>
        <CKRow icon={CI.tools} label="Scope" value="Full spring startup & zone check" strong/>
        <div style={{ padding: '14px 16px', borderBottom: `1px solid ${ck_line}` }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <CKPill bg={ck_line2} color={ck_ink2}>~90 min</CKPill>
            <CKPill bg={ck_line2} color={ck_ink2}>1 staff</CKPill>
            <CKPill bg={ck_amberBg} color={ck_amber}>Normal</CKPill>
          </div>
        </div>
        <div style={{ padding: '14px 16px' }}>
          <div style={{ fontSize: 11.5, fontWeight: 700, color: ck_ink4, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <CKIcon d={CI.box} size={12} stroke={ck_ink4}/> Materials
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {['Rotor nozzles (×4)', 'Pressure regulator', 'Backflow kit', 'Thread tape'].map((m) => (
              <span key={m} style={{
                padding: '8px 12px', borderRadius: 10, background: ck_soft,
                fontSize: 13.5, fontWeight: 700, color: ck_ink, border: `1.5px solid ${ck_line}`,
                letterSpacing: -0.1,
              }}>{m}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Tech assignment */}
      <div style={{ margin: '0 20px 16px', borderRadius: 14, border: `1.5px solid ${ck_line}`, background: '#fff' }}>
        <CKRow icon={CI.user} label="Assigned tech" value="Viktor K. · Route #3"
          right={<CKLinkBtn>Reassign</CKLinkBtn>}/>
      </div>

      {/* Footer */}
      <div style={{
        padding: '14px 20px 18px', background: ck_soft,
        borderTop: `1px solid ${ck_line}`,
        display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
      }}>
        <CKLinkBtn icon={CI.pencil}>Edit</CKLinkBtn>
        <CKLinkBtn icon={CI.alert}>No show</CKLinkBtn>
        <CKLinkBtn icon={CI.x} color={ck_red} border={'#FCA5A5'}>Cancel</CKLinkBtn>
      </div>
    </div>
  );
}

Object.assign(window, { CombinedModal, CKTagEditor });
