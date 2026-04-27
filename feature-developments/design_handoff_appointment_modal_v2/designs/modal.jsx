// Unified appointment + job modal — sunlight-legible for field techs.
// Original design. Data from Grins_irrigation_platform.
// Removed: financials/pricing block. Payment kept.
// Changes vs prior: higher contrast, larger type, bigger hit targets.

const ink   = '#0B1220';                  // near-black for max contrast
const ink2  = '#1F2937';
const ink3  = '#4B5563';
const ink4  = '#6B7280';
const line  = '#E5E7EB';
const line2 = '#F3F4F6';
const surf  = '#FFFFFF';
const soft  = '#F9FAFB';

// Action colors — high saturation, dark enough on white for sun.
const blue     = '#1D4ED8';
const blueBg   = '#DBEAFE';
const orange   = '#C2410C';
const orangeBg = '#FFEDD5';
const green    = '#047857';
const greenBg  = '#D1FAE5';
const teal     = '#0F766E';
const tealBg   = '#CCFBF1';
const red      = '#B91C1C';
const redBg    = '#FEE2E2';
const amber    = '#B45309';
const amberBg  = '#FEF3C7';
const violet   = '#6D28D9';
const violetBg = '#EDE9FE';

const fontUI   = '"Inter", -apple-system, BlinkMacSystemFont, system-ui, sans-serif';
const fontMono = '"JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace';

function Icon({ d, size = 16, stroke = 'currentColor', fill = 'none', sw = 2 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={stroke} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
      {typeof d === 'string' ? <path d={d}/> : d}
    </svg>
  );
}

const I = {
  cal:    'M8 2v4M16 2v4M3 10h18M5 6h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z',
  clock:  <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  user:   <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
  phone:  'M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92Z',
  mail:   <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 7 9-7"/></>,
  pin:    <><path d="M20 10c0 7-8 12-8 12S4 17 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="3"/></>,
  nav:    'M2 11l20-9-9 20-2-9-9-2Z',
  play:   'M5 3l14 9-14 9V3Z',
  check:  'M4 12l5 5 11-11',
  checkC: <><circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/></>,
  star:   'M12 2 15 9l7 .7-5.3 4.8 1.7 7.1L12 18l-6.4 3.6 1.7-7.1L2 9.7 9 9l3-7Z',
  spark:  <><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/></>,
  card:   <><rect x="2" y="6" width="20" height="12" rx="2"/><path d="M2 11h20M6 15h4"/></>,
  box:    <><path d="M3 7l9-4 9 4v10l-9 4-9-4V7Z"/><path d="M3 7l9 4 9-4M12 11v10"/></>,
  chat:   'M21 11.5A8.38 8.38 0 0 1 12.5 20a8.5 8.5 0 0 1-4-1L3 20l1-4.5A8.5 8.5 0 0 1 12.5 3 8.38 8.38 0 0 1 21 11.5Z',
  doc:    <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 13h8M8 17h5"/></>,
  pencil: 'M11 4h-7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7M18.5 2.5a2.1 2.1 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5Z',
  x:      'M18 6 6 18M6 6l12 12',
  alert:  <><circle cx="12" cy="12" r="9"/><path d="M12 7v5M12 16v.5"/></>,
  route:  <><circle cx="6" cy="19" r="2"/><circle cx="18" cy="5" r="2"/><path d="M6 17V9a4 4 0 0 1 4-4h4M18 7v8a4 4 0 0 1-4 4h-4"/></>,
  tools:  <><path d="M14.7 6.3a3 3 0 0 0-4.2 4.2L3 18l3 3 7.5-7.5a3 3 0 0 0 4.2-4.2l-1.8 1.8L14 9l1.5-1.5-0.8-1.2Z"/></>,
  plus:   'M12 5v14M5 12h14',
  photo:  <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 16 5-5 4 4 3-3 6 6"/><circle cx="9" cy="10" r="1.5"/></>,
};

function Pill({ children, bg, color, size = 'md' }) {
  const pad = size === 'lg' ? '4px 12px' : '3px 10px';
  const fs = size === 'lg' ? 13 : 12;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      background: bg, color, padding: pad, borderRadius: 999,
      fontSize: fs, fontWeight: 700, lineHeight: 1.4, fontFamily: fontUI,
      whiteSpace: 'nowrap', flexShrink: 0,
    }}>{children}</span>
  );
}

function StatusBadge({ step }) {
  if (step === 0) return <Pill bg={blueBg} color={blue} size="lg">Scheduled</Pill>;
  if (step === 1) return <Pill bg={blueBg} color={blue} size="lg">On the way</Pill>;
  if (step === 2) return <Pill bg={orangeBg} color={orange} size="lg">On site</Pill>;
  return <Pill bg={greenBg} color={green} size="lg">Complete</Pill>;
}

// ─── Big action buttons ──────────────────────────────────────
// Tall (64px), high-contrast, icon-forward for quick glance & fat fingers.

function BigAction({ color, bg, border, icon, label, sub, done, disabled, fill = 'solid' }) {
  const solid = fill === 'solid';
  const st = done ? {
    background: '#fff', color: green, border: `2px solid ${green}`,
  } : solid ? {
    background: bg, color: '#fff', border: `2px solid ${bg}`,
  } : {
    background: '#fff', color, border: `2px solid ${border || color}`,
  };
  return (
    <button style={{
      flex: 1, minWidth: 0, ...st, borderRadius: 14,
      padding: '14px 10px', minHeight: 104,
      cursor: disabled ? 'not-allowed' : 'pointer',
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: 6, fontFamily: fontUI, textAlign: 'center',
      opacity: disabled ? 0.4 : 1,
      boxShadow: done ? 'none' : solid && !disabled ? '0 1px 0 rgba(0,0,0,0.1), 0 4px 8px rgba(0,0,0,0.06)' : 'none',
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: 18,
        background: done ? '#fff' : solid ? 'rgba(255,255,255,0.18)' : bg,
        color: done ? green : solid ? '#fff' : '#fff',
        border: done ? `2px solid ${green}` : 'none',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Icon d={done ? I.check : icon} size={20} sw={2.6}/>
      </div>
      <span style={{
        fontSize: 15, fontWeight: 800, letterSpacing: -0.2,
        whiteSpace: 'nowrap', lineHeight: 1,
      }}>{label}</span>
      <span style={{
        fontSize: 12, fontWeight: 700,
        fontFamily: done ? fontMono : fontUI,
        opacity: done ? 1 : 0.9, letterSpacing: -0.1, lineHeight: 1,
        whiteSpace: 'nowrap',
      }}>{sub}</span>
    </button>
  );
}

function ActionTrack({ step }) {
  return (
    <div style={{ display: 'flex', gap: 8 }}>
      <BigAction
        color="#fff" bg={blue} icon={I.nav}
        label="On my way"
        sub={step >= 1 ? '8:42 AM' : 'Text customer'}
        done={step >= 1}
      />
      <BigAction
        color="#fff" bg={orange} icon={I.play}
        label="Job started"
        sub={step >= 2 ? '9:06 AM' : 'Log arrival'}
        done={step >= 2}
        disabled={step < 1}
      />
      <BigAction
        color="#fff" bg={green} icon={I.checkC}
        label="Job complete"
        sub={step >= 3 ? '10:48 AM' : 'Close out'}
        done={step >= 3}
        disabled={step < 2}
      />
    </div>
  );
}

// ─── Row-based sections for scannable data ──────────────────

function Row({ icon, label, value, right, strong }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '14px 16px', borderBottom: `1px solid ${line}`,
      background: '#fff',
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: 10,
        background: soft, color: ink3, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Icon d={icon} size={18}/>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        {label && <div style={{ fontSize: 11.5, fontWeight: 700, color: ink4, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 2 }}>{label}</div>}
        <div style={{
          fontSize: strong ? 17 : 15, fontWeight: strong ? 800 : 600,
          color: ink, lineHeight: 1.25, letterSpacing: -0.2,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>{value}</div>
      </div>
      {right}
    </div>
  );
}

function BigLinkBtn({ icon, children, color = ink, bg = '#fff', border = line }) {
  return (
    <button style={{
      minHeight: 44, padding: '0 14px', borderRadius: 12,
      background: bg, color, border: `1.5px solid ${border}`,
      fontSize: 14, fontWeight: 700, fontFamily: fontUI, cursor: 'pointer',
      display: 'inline-flex', alignItems: 'center', gap: 6,
    }}>
      {icon && <Icon d={icon} size={16} sw={2.2}/>}
      {children}
    </button>
  );
}

// ─── Timeline dots (compact) ────────────────────────────────
function TimelineStrip({ step }) {
  const dots = [
    { label: 'Booked',   time: '9:00' },
    { label: 'En route', time: step >= 1 ? '8:42' : '—' },
    { label: 'On site',  time: step >= 2 ? '9:06' : '—' },
    { label: 'Done',     time: step >= 3 ? '10:48' : '—' },
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
                background: active ? ink : '#fff',
                border: `2px solid ${active ? ink : line}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#fff', boxShadow: now ? `0 0 0 4px ${blueBg}` : 'none',
              }}>
                {active && !now && <Icon d={I.check} size={12} sw={3.2}/>}
                {now && <div style={{ width: 8, height: 8, borderRadius: 4, background: blue }}/>}
              </div>
              <div style={{ fontSize: 12.5, fontWeight: 700, color: active ? ink : ink4, marginTop: 8, whiteSpace: 'nowrap' }}>{d.label}</div>
              <div style={{ fontSize: 11.5, fontFamily: fontMono, fontWeight: 600, color: ink4, marginTop: 1, whiteSpace: 'nowrap' }}>{d.time}</div>
            </div>
            {i < dots.length - 1 && (
              <div style={{ flex: 1, minWidth: 12, height: 2, background: i < step ? ink : line, marginTop: 10 }}/>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Payment block (kept per user request) ──────────────────

function PaymentBlock({ step, showEstimate }) {
  const payBtn = step === 3 ? (
    <div style={{
      padding: 16, borderRadius: 14,
      background: greenBg, border: `2px solid ${green}`,
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <div style={{
        width: 40, height: 40, borderRadius: 20, background: green, color: '#fff',
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        <Icon d={I.check} size={22} sw={3}/>
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 15, fontWeight: 800, color: green }}>Payment collected</div>
        <div style={{ fontSize: 13, fontWeight: 600, color: green }}>$100.00 · paid by card on site</div>
      </div>
    </div>
  ) : (
    <button style={{
      width: '100%', minHeight: 60, borderRadius: 14,
      background: '#fff', border: `2px solid ${teal}`,
      color: teal, fontFamily: fontUI, fontWeight: 800, fontSize: 16,
      cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
      padding: '0 16px',
    }}>
      <Icon d={I.card} size={22} sw={2.2}/>
      Collect payment
    </button>
  );
  return (
    <div style={{ margin: '0 20px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
      {payBtn}
      {showEstimate && (
        <button style={{
          width: '100%', minHeight: 60, borderRadius: 14,
          background: '#fff', border: `2px solid ${violet}`,
          color: violet, fontFamily: fontUI, fontWeight: 800, fontSize: 16,
          cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          padding: '0 16px',
        }}>
          <Icon d={I.doc} size={22} sw={2.2}/>
          Send estimate
        </button>
      )}
    </div>
  );
}

// ─── The modal ──────────────────────────────────────────────

function AppointmentModal({ role = 'admin', step = 0, showEstimate = false }) {
  const isDone = step === 3;
  return (
    <div style={{
      width: 560, background: surf,
      borderRadius: 18, overflow: 'hidden',
      border: `1px solid ${line}`,
      boxShadow: '0 30px 60px rgba(10,15,30,0.12), 0 4px 12px rgba(10,15,30,0.05)',
      fontFamily: fontUI, color: ink,
    }}>
      {/* Header — high-contrast, big type */}
      <div style={{ padding: '20px 20px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
              <StatusBadge step={step}/>
              <Pill bg={line2} color={ink2}>Residential</Pill>
              <span style={{ fontSize: 11, fontWeight: 700, color: ink4, fontFamily: fontMono }}>#dee04bb5</span>
            </div>
            <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: -0.6, color: ink, lineHeight: 1.1 }}>
              Spring Startup
            </div>
            <div style={{
              marginTop: 8, fontSize: 15, fontWeight: 700, color: ink2,
              display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
            }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <Icon d={I.cal} size={16} stroke={ink3}/> Wed, Apr 22
              </span>
              <span style={{ color: line }}>·</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontFamily: fontMono }}>
                <Icon d={I.clock} size={16} stroke={ink3}/> 9:00 – 11:00 AM
              </span>
            </div>
          </div>
          <button style={{
            width: 40, height: 40, borderRadius: 12, border: `1.5px solid ${line}`,
            background: '#fff', color: ink2, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}><Icon d={I.x} size={18} sw={2.4}/></button>
        </div>
      </div>

      {/* Timeline */}
      <div style={{ padding: '4px 20px 16px' }}>
        <TimelineStrip step={step}/>
      </div>

      {/* PRIMARY ACTIONS — giant buttons, promoted to the top */}
      <div style={{
        padding: '16px 20px 16px',
        background: soft,
        borderTop: `1px solid ${line}`, borderBottom: `1px solid ${line}`,
      }}>
        <div style={{ fontSize: 12, fontWeight: 800, color: ink3, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
          On-site operations
        </div>
        <ActionTrack step={step}/>
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          <BigLinkBtn icon={I.photo}>Add photo</BigLinkBtn>
          <BigLinkBtn icon={I.doc}>Notes</BigLinkBtn>
          <BigLinkBtn icon={I.star}>Review</BigLinkBtn>
          <div style={{ flex: 1 }}/>
          <BigLinkBtn icon={I.spark} color={violet} border={violet} bg={violetBg}>AI draft</BigLinkBtn>
        </div>
      </div>

      {/* Payment block (kept — financials removed) */}
      <div style={{ paddingTop: 16 }}>
        <PaymentBlock step={step} showEstimate={showEstimate}/>
      </div>

      {/* Customer — hero row */}
      <div style={{ margin: '0 20px 16px', borderRadius: 14, border: `1.5px solid ${line}`, overflow: 'hidden' }}>
        <div style={{
          padding: '14px 16px', background: tealBg,
          display: 'flex', alignItems: 'center', gap: 12,
          borderBottom: `1px solid ${line}`,
        }}>
          <div style={{
            width: 44, height: 44, borderRadius: 22, background: '#fff',
            color: teal, display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 800, fontSize: 16, border: `2px solid ${teal}`,
          }}>TU</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: ink, letterSpacing: -0.3 }}>Test User</div>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: ink3 }}>1 previous job · Last service Oct 2025</div>
          </div>
        </div>
        <a href="tel:9527373312" style={{
          display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px',
          textDecoration: 'none', color: ink, background: '#fff',
          borderBottom: `1px solid ${line}`,
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10, background: blueBg, color: blue, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><Icon d={I.phone} size={18}/></div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11.5, fontWeight: 700, color: ink4, textTransform: 'uppercase', letterSpacing: 0.8 }}>Phone</div>
            <div style={{ fontSize: 17, fontWeight: 800, fontFamily: fontMono, color: ink, letterSpacing: -0.2 }}>(952) 737-3312</div>
          </div>
          <div style={{
            padding: '8px 14px', background: blue, color: '#fff', borderRadius: 10,
            fontWeight: 800, fontSize: 13, minHeight: 36, display: 'flex', alignItems: 'center', gap: 4,
          }}>
            <Icon d={I.phone} size={14} sw={2.4}/> Call
          </div>
        </a>
        <a href="#" style={{
          display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px',
          textDecoration: 'none', color: ink, background: '#fff',
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10, background: soft, color: ink3, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><Icon d={I.mail} size={18}/></div>
          <div style={{ fontSize: 14, fontWeight: 600, color: ink2 }}>test@example.com</div>
        </a>
      </div>

      {/* Location */}
      <div style={{ margin: '0 20px 16px', borderRadius: 14, border: `1.5px solid ${line}`, overflow: 'hidden' }}>
        <div style={{ padding: '14px 16px', background: '#fff' }}>
          <div style={{ fontSize: 11.5, fontWeight: 700, color: ink4, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Icon d={I.pin} size={12} stroke={ink4}/> Property
          </div>
          <div style={{ fontSize: 19, fontWeight: 800, color: ink, letterSpacing: -0.3, lineHeight: 1.2 }}>
            1 Test Street
          </div>
          <div style={{ fontSize: 15, fontWeight: 600, color: ink2, marginTop: 2 }}>
            Eden Prairie, MN 55344
          </div>
        </div>
        <button style={{
          width: '100%', padding: '14px 16px',
          background: blue, color: '#fff', border: 'none',
          fontFamily: fontUI, fontSize: 16, fontWeight: 800,
          cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          minHeight: 52,
        }}>
          <Icon d={I.nav} size={20} sw={2.4}/>
          Get directions
        </button>
      </div>

      {/* Job scope & materials */}
      <div style={{ margin: '0 20px 16px', borderRadius: 14, border: `1.5px solid ${line}`, overflow: 'hidden', background: '#fff' }}>
        <Row icon={I.tools} label="Scope" value="Full spring startup & zone check" strong/>
        <div style={{ padding: '14px 16px', borderBottom: `1px solid ${line}` }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <Pill bg={line2} color={ink2}>~90 min</Pill>
            <Pill bg={line2} color={ink2}>1 staff</Pill>
            <Pill bg={amberBg} color={amber}>Normal</Pill>
          </div>
        </div>
        <div style={{ padding: '14px 16px' }}>
          <div style={{ fontSize: 11.5, fontWeight: 700, color: ink4, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Icon d={I.box} size={12} stroke={ink4}/> Materials
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {['Rotor nozzles (×4)', 'Pressure regulator', 'Backflow kit', 'Thread tape'].map((m) => (
              <span key={m} style={{
                padding: '8px 12px', borderRadius: 10, background: soft,
                fontSize: 13.5, fontWeight: 700, color: ink, border: `1.5px solid ${line}`,
                letterSpacing: -0.1,
              }}>{m}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Technician assignment — admin only */}
      {role === 'admin' && (
        <div style={{ margin: '0 20px 16px', borderRadius: 14, border: `1.5px solid ${line}`, background: '#fff' }}>
          <Row
            icon={I.user}
            label="Assigned tech"
            value="Viktor K. · Route #3"
            right={<BigLinkBtn>Reassign</BigLinkBtn>}
          />
        </div>
      )}

      {/* Footer */}
      <div style={{
        padding: '14px 20px 18px', background: soft,
        borderTop: `1px solid ${line}`,
        display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
      }}>
        <BigLinkBtn icon={I.pencil}>Edit</BigLinkBtn>
        <BigLinkBtn icon={I.alert}>No show</BigLinkBtn>
        <BigLinkBtn icon={I.x} color={red} border={'#FCA5A5'}>Cancel</BigLinkBtn>
      </div>
    </div>
  );
}

Object.assign(window, { AppointmentModal });
