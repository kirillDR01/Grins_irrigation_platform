// PaymentSheet — Direction A: vertical sheet/drawer.
// Handles all 8 states the user asked for, plus one-off vs agreement variants.
// Sunlight-legible: big type, fat buttons, high contrast.

const ps_ink   = '#0B1220';
const ps_ink2  = '#1F2937';
const ps_ink3  = '#4B5563';
const ps_ink4  = '#6B7280';
const ps_line  = '#E5E7EB';
const ps_line2 = '#F3F4F6';
const ps_soft  = '#F9FAFB';
const ps_surf  = '#FFFFFF';

const ps_blue     = '#1D4ED8';
const ps_blueBg   = '#DBEAFE';
const ps_green    = '#047857';
const ps_greenBg  = '#D1FAE5';
const ps_teal     = '#0F766E';
const ps_tealBg   = '#CCFBF1';
const ps_orange   = '#C2410C';
const ps_orangeBg = '#FFEDD5';
const ps_amber    = '#B45309';
const ps_amberBg  = '#FEF3C7';
const ps_red      = '#B91C1C';
const ps_violet   = '#6D28D9';
const ps_violetBg = '#EDE9FE';

const ps_font = '"Inter", system-ui, sans-serif';
const ps_mono = '"JetBrains Mono", ui-monospace, monospace';

const PS_CATALOG = [
  { id: 'head-4', name: 'Sprinkler head replacement', detail: '4" pop-up', price: 45 },
  { id: 'head-6', name: 'Sprinkler head replacement', detail: '6" pop-up', price: 55 },
  { id: 'rotor', name: 'Rotor head replacement', detail: 'Standard residential', price: 75 },
  { id: 'nozzle', name: 'Nozzle swap', detail: 'Any standard nozzle', price: 12 },
  { id: 'wire', name: 'Valve wire splice', detail: 'Per splice', price: 35 },
  { id: 'valve', name: 'Valve diaphragm rebuild', detail: '1" residential', price: 85 },
  { id: 'backflow', name: 'Backflow test', detail: 'Certified test & report', price: 95 },
  { id: 'drip-repair', name: 'Drip line repair', detail: 'Per repair', price: 40 },
  { id: 'controller', name: 'Controller replacement', detail: 'Smart controller, parts + labor', price: 325 },
  { id: 'pipe', name: 'Pipe repair', detail: 'PVC, under 3ft', price: 90 },
];

function PSIcon({ d, size = 16, sw = 2, stroke = 'currentColor', fill = 'none' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={stroke} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
      {typeof d === 'string' ? <path d={d}/> : d}
    </svg>
  );
}

const PI = {
  x: 'M18 6 6 18M6 6l12 12',
  chev: 'M9 6l6 6-6 6',
  chevD: 'M6 9l6 6 6-6',
  back: 'M15 18l-6-6 6-6',
  search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>,
  plus: 'M12 5v14M5 12h14',
  minus: 'M5 12h14',
  trash: <><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14"/></>,
  shield: <><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3Z"/><path d="m9 12 2 2 4-4"/></>,
  check: 'M4 12l5 5 11-11',
  checkC: <><circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/></>,
  card: <><rect x="2" y="6" width="20" height="12" rx="2"/><path d="M2 11h20M6 15h4"/></>,
  cash: <><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/><path d="M6 9v.01M18 15v.01"/></>,
  cheque: <><rect x="3" y="6" width="18" height="12" rx="1.5"/><path d="M7 11h6M7 14h4"/></>,
  mail: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 7 9-7"/></>,
  sms: 'M21 11.5A8.38 8.38 0 0 1 12.5 20a8.5 8.5 0 0 1-4-1L3 20l1-4.5A8.5 8.5 0 0 1 12.5 3 8.38 8.38 0 0 1 21 11.5Z',
  tap: <><path d="M12 2a10 10 0 0 1 10 10"/><path d="M12 7a5 5 0 0 1 5 5"/><circle cx="12" cy="12" r="2"/><path d="M8 20l-2 2M16 20l2 2"/></>,
  tag: <><path d="M20 12V4a1 1 0 0 0-1-1h-8L3 11l10 10 7-7a1 1 0 0 0 0-1.4Z"/><circle cx="9" cy="9" r="1"/></>,
  link: <><path d="M9 15l6-6"/><path d="M11 7l1-1a4 4 0 0 1 6 6l-2 2M13 17l-1 1a4 4 0 0 1-6-6l2-2"/></>,
  sparkle: <><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.5 5.5l2.5 2.5M16 16l2.5 2.5M5.5 18.5l2.5-2.5M16 8l2.5-2.5"/></>,
  copy: <><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></>,
  print: <><path d="M6 9V3h12v6"/><rect x="4" y="9" width="16" height="8" rx="2"/><path d="M6 17h12v4H6z"/></>,
  phone: 'M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92Z',
};

// ─── Shared sheet chrome ───────────────────────────────────

function Sheet({ title, subtitle, onBack, onClose, children, footer, pad = true }) {
  return (
    <div style={{
      width: 560, background: ps_surf, borderRadius: 20, overflow: 'hidden',
      border: `1px solid ${ps_line}`,
      boxShadow: '0 30px 60px rgba(10,15,30,0.14), 0 4px 12px rgba(10,15,30,0.05)',
      fontFamily: ps_font, color: ps_ink,
      display: 'flex', flexDirection: 'column',
    }}>
      {/* grabber */}
      <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0 4px' }}>
        <div style={{ width: 44, height: 5, borderRadius: 3, background: ps_line }}/>
      </div>
      <div style={{ padding: '4px 20px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
        {onBack && (
          <button style={{
            width: 44, height: 44, borderRadius: 12, border: `1.5px solid ${ps_line}`,
            background: '#fff', color: ps_ink2, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}><PSIcon d={PI.back} size={20} sw={2.4}/></button>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5, color: ps_ink, lineHeight: 1.1 }}>
            {title}
          </div>
          {subtitle && (
            <div style={{ fontSize: 13.5, fontWeight: 600, color: ps_ink3, marginTop: 3 }}>
              {subtitle}
            </div>
          )}
        </div>
        {onClose && (
          <button style={{
            width: 44, height: 44, borderRadius: 12, border: `1.5px solid ${ps_line}`,
            background: '#fff', color: ps_ink2, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}><PSIcon d={PI.x} size={20} sw={2.4}/></button>
        )}
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: pad ? '0 20px 20px' : 0 }}>
        {children}
      </div>
      {footer && (
        <div style={{
          padding: '14px 20px 18px', background: ps_soft,
          borderTop: `1px solid ${ps_line}`,
        }}>
          {footer}
        </div>
      )}
    </div>
  );
}

function Btn({ kind = 'primary', color, children, icon, iconRight, style, size = 'lg', disabled }) {
  const base = {
    width: '100%', minHeight: size === 'lg' ? 60 : 48,
    borderRadius: 14, fontFamily: ps_font,
    fontSize: size === 'lg' ? 17 : 15, fontWeight: 800, letterSpacing: -0.2,
    cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.45 : 1,
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
    padding: '0 16px', border: '2px solid transparent',
  };
  const styles = {
    primary: { background: color || ps_ink, color: '#fff', borderColor: color || ps_ink },
    secondary: { background: '#fff', color: color || ps_ink, borderColor: color || ps_ink },
    ghost: { background: '#fff', color: ps_ink2, borderColor: ps_line },
    danger: { background: '#fff', color: ps_red, borderColor: '#FCA5A5' },
  };
  return (
    <button disabled={disabled} style={{ ...base, ...styles[kind], ...style }}>
      {icon && <PSIcon d={icon} size={20} sw={2.4}/>}
      <span>{children}</span>
      {iconRight && <PSIcon d={iconRight} size={18} sw={2.4}/>}
    </button>
  );
}

// ─── Banner (agreement jobs) ───────────────────────────────

function AgreementBanner({ name }) {
  return (
    <div style={{
      padding: '14px 16px', borderRadius: 14,
      background: ps_greenBg, border: `2px solid ${ps_green}`,
      display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16,
    }}>
      <div style={{
        width: 40, height: 40, borderRadius: 20, background: ps_green, color: '#fff',
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        <PSIcon d={PI.shield} size={22} sw={2.2}/>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 15, fontWeight: 800, color: ps_green, letterSpacing: -0.2 }}>
          Covered by {name}
        </div>
        <div style={{ fontSize: 13, fontWeight: 600, color: ps_green }}>
          Visit is already paid — add extras only
        </div>
      </div>
    </div>
  );
}

// ─── Line items list ───────────────────────────────────────

function LineItem({ name, detail, price, qty = 1, onRemove, locked }) {
  return (
    <div style={{
      padding: '12px 14px', borderRadius: 12,
      background: locked ? ps_soft : '#fff',
      border: `1.5px solid ${ps_line}`, marginBottom: 8,
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 15, fontWeight: 800, color: ps_ink, letterSpacing: -0.2,
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          {locked && <PSIcon d={PI.shield} size={14} stroke={ps_green} sw={2.4}/>}
          {name}
        </div>
        {detail && <div style={{ fontSize: 13, color: ps_ink3, fontWeight: 600, marginTop: 1 }}>{detail}{qty > 1 ? ` · qty ${qty}` : ''}</div>}
      </div>
      <div style={{
        fontFamily: ps_mono, fontSize: 16, fontWeight: 800,
        color: locked ? ps_ink4 : ps_ink, textDecoration: locked ? 'line-through' : 'none',
        minWidth: 72, textAlign: 'right',
      }}>
        ${price.toFixed(2)}
      </div>
      {onRemove && !locked && (
        <button style={{
          width: 36, height: 36, borderRadius: 10, background: '#fff',
          border: `1.5px solid ${ps_line}`, color: ps_red, cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}><PSIcon d={PI.trash} size={16} sw={2.2}/></button>
      )}
    </div>
  );
}

// ─── State 1: Starting sheet (agreement) ─────────────────

function State_Start({ agreement }) {
  return (
    <Sheet
      title="Collect payment"
      subtitle="Visit covered — add any extras"
      onClose
      footer={<Btn kind="primary" disabled>Continue · $0.00</Btn>}
    >
      {agreement && <AgreementBanner name={agreement}/>}
      <LineItem
        locked
        name="Spring startup"
        detail="Covered by agreement"
        price={0}
      />

      <div style={{ fontSize: 12, fontWeight: 800, color: ps_ink4, textTransform: 'uppercase', letterSpacing: 1, margin: '20px 0 10px' }}>
        Extras for this visit
      </div>
      <button style={{
        width: '100%', minHeight: 60, borderRadius: 14,
        background: '#fff', border: `2px dashed ${ps_line}`,
        color: ps_ink2, fontFamily: ps_font, fontSize: 15, fontWeight: 700,
        cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
      }}>
        <PSIcon d={PI.plus} size={18} sw={2.6}/> Add service or repair
      </button>

      <div style={{ fontSize: 13, fontWeight: 600, color: ps_ink4, textAlign: 'center', marginTop: 14, lineHeight: 1.4 }}>
        No extras? Close this sheet — the visit is already paid.
      </div>
    </Sheet>
  );
}

// ─── State 2: Picker (mid-interaction) ─────────────────────

function State_Picker() {
  return (
    <Sheet
      title="Add extra"
      subtitle="Search or add custom"
      onBack
    >
      {/* search */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '0 14px', minHeight: 56, borderRadius: 14,
        background: ps_soft, border: `1.5px solid ${ps_line}`, marginBottom: 14,
      }}>
        <PSIcon d={PI.search} size={20} stroke={ps_ink3}/>
        <input
          defaultValue="sprink"
          style={{
            flex: 1, border: 'none', background: 'transparent', outline: 'none',
            fontFamily: ps_font, fontSize: 17, fontWeight: 700, color: ps_ink, letterSpacing: -0.2,
          }}
        />
      </div>
      <div style={{ fontSize: 12, fontWeight: 800, color: ps_ink4, textTransform: 'uppercase', letterSpacing: 1, margin: '6px 0 10px' }}>
        Matches
      </div>
      {PS_CATALOG.filter(c => c.name.toLowerCase().includes('sprink')).map((c) => (
        <button key={c.id} style={{
          width: '100%', padding: '14px 14px', borderRadius: 12,
          border: `1.5px solid ${ps_line}`, background: '#fff',
          marginBottom: 8, cursor: 'pointer', textAlign: 'left',
          display: 'flex', alignItems: 'center', gap: 12, fontFamily: ps_font,
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: ps_ink, letterSpacing: -0.2 }}>{c.name}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: ps_ink3, marginTop: 1 }}>{c.detail}</div>
          </div>
          <div style={{ fontFamily: ps_mono, fontSize: 16, fontWeight: 800, color: ps_ink2 }}>${c.price.toFixed(2)}</div>
          <div style={{
            width: 36, height: 36, borderRadius: 18, background: ps_ink, color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><PSIcon d={PI.plus} size={18} sw={2.8}/></div>
        </button>
      ))}

      <div style={{ fontSize: 12, fontWeight: 800, color: ps_ink4, textTransform: 'uppercase', letterSpacing: 1, margin: '18px 0 10px' }}>
        Common
      </div>
      {PS_CATALOG.slice(3, 7).map((c) => (
        <button key={c.id} style={{
          width: '100%', padding: '14px 14px', borderRadius: 12,
          border: `1.5px solid ${ps_line}`, background: '#fff',
          marginBottom: 8, cursor: 'pointer', textAlign: 'left',
          display: 'flex', alignItems: 'center', gap: 12, fontFamily: ps_font,
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: ps_ink, letterSpacing: -0.2 }}>{c.name}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: ps_ink3, marginTop: 1 }}>{c.detail}</div>
          </div>
          <div style={{ fontFamily: ps_mono, fontSize: 16, fontWeight: 800, color: ps_ink2 }}>${c.price.toFixed(2)}</div>
        </button>
      ))}

      <button style={{
        width: '100%', padding: '14px 14px', borderRadius: 12,
        border: `1.5px dashed ${ps_violet}`, background: ps_violetBg,
        color: ps_violet, cursor: 'pointer', fontFamily: ps_font,
        fontSize: 15, fontWeight: 800, marginTop: 10,
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
      }}>
        <PSIcon d={PI.pencil || PI.plus} size={18} sw={2.4}/>
        Custom line — type description + price
      </button>
    </Sheet>
  );
}

// ─── State 3: Ready to charge (agreement, with extras) ─────

function State_Ready({ agreement }) {
  const items = [
    { name: 'Sprinkler head replacement', detail: '4" pop-up', price: 45, qty: 2 },
    { name: 'Valve wire splice', detail: 'Per splice', price: 35 },
  ];
  const extras = items.reduce((s, i) => s + i.price * (i.qty || 1), 0);
  return (
    <Sheet
      title="Collect payment"
      subtitle={agreement ? 'Extras beyond agreement' : undefined}
      onClose
      footer={
        <Btn kind="primary" color={ps_ink} iconRight={PI.chev}>
          Continue · ${extras.toFixed(2)}
        </Btn>
      }
    >
      {agreement && <AgreementBanner name={agreement}/>}
      <LineItem
        locked
        name="Spring startup"
        detail="Covered by agreement"
        price={0}
      />

      <div style={{ fontSize: 12, fontWeight: 800, color: ps_ink4, textTransform: 'uppercase', letterSpacing: 1, margin: '20px 0 10px' }}>
        Extras ({items.length})
      </div>
      {items.map((it, i) => (
        <LineItem key={i} {...it} onRemove/>
      ))}
      <button style={{
        width: '100%', minHeight: 52, borderRadius: 12,
        background: '#fff', border: `2px dashed ${ps_line}`,
        color: ps_ink2, fontFamily: ps_font, fontSize: 14.5, fontWeight: 700,
        cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        marginTop: 4,
      }}>
        <PSIcon d={PI.plus} size={16} sw={2.6}/> Add another
      </button>

      {/* discount + totals */}
      <div style={{
        marginTop: 18, padding: 14, borderRadius: 14,
        background: ps_soft, border: `1.5px solid ${ps_line}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10, background: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: `1.5px solid ${ps_line}`, color: ps_ink3,
          }}><PSIcon d={PI.tag} size={16}/></div>
          <span style={{ fontSize: 14, fontWeight: 700, color: ps_ink2 }}>Discount</span>
          <div style={{ flex: 1 }}/>
          <button style={{
            background: 'transparent', border: 'none', color: ps_blue,
            fontFamily: ps_font, fontSize: 14, fontWeight: 800, cursor: 'pointer',
          }}>+ Add</button>
        </div>
        <div style={{ height: 1, background: ps_line, margin: '12px 0' }}/>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 17, fontWeight: 800, color: ps_ink, letterSpacing: -0.3 }}>Total due</span>
          <span style={{ fontFamily: ps_mono, fontSize: 24, fontWeight: 800, color: ps_ink, letterSpacing: -0.5 }}>
            ${extras.toFixed(2)}
          </span>
        </div>
      </div>
    </Sheet>
  );
}

// ─── State 4: One-off (no agreement) ready to charge ───────

function State_OneOffReady() {
  const items = [
    { name: 'Backflow test', detail: 'Certified test & report', price: 95 },
    { name: 'Sprinkler head replacement', detail: '6" pop-up', price: 55 },
  ];
  const total = items.reduce((s, i) => s + i.price, 0);
  return (
    <Sheet
      title="Collect payment"
      subtitle="One-off service call"
      onClose
      footer={
        <Btn kind="primary" color={ps_ink} iconRight={PI.chev}>
          Continue · ${total.toFixed(2)}
        </Btn>
      }
    >
      <div style={{ fontSize: 12, fontWeight: 800, color: ps_ink4, textTransform: 'uppercase', letterSpacing: 1, margin: '4px 0 10px' }}>
        Services ({items.length})
      </div>
      {items.map((it, i) => (
        <LineItem key={i} {...it} onRemove/>
      ))}
      <button style={{
        width: '100%', minHeight: 52, borderRadius: 12,
        background: '#fff', border: `2px dashed ${ps_line}`,
        color: ps_ink2, fontFamily: ps_font, fontSize: 14.5, fontWeight: 700,
        cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        marginTop: 4,
      }}>
        <PSIcon d={PI.plus} size={16} sw={2.6}/> Add another
      </button>

      <div style={{
        marginTop: 18, padding: 14, borderRadius: 14,
        background: ps_soft, border: `1.5px solid ${ps_line}`,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: ps_ink3 }}>Subtotal</span>
          <span style={{ fontFamily: ps_mono, fontSize: 14, fontWeight: 700, color: ps_ink2 }}>${total.toFixed(2)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: ps_ink3 }}>Discount</span>
          <button style={{
            background: 'transparent', border: 'none', color: ps_blue,
            fontFamily: ps_font, fontSize: 14, fontWeight: 800, cursor: 'pointer', padding: 0,
          }}>+ Add</button>
        </div>
        <div style={{ height: 1, background: ps_line, margin: '8px 0 12px' }}/>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 17, fontWeight: 800, color: ps_ink, letterSpacing: -0.3 }}>Total due</span>
          <span style={{ fontFamily: ps_mono, fontSize: 24, fontWeight: 800, color: ps_ink, letterSpacing: -0.5 }}>
            ${total.toFixed(2)}
          </span>
        </div>
      </div>
    </Sheet>
  );
}

// ─── State 5: Pick payment method ──────────────────────────

function PayMethod({ bg, color, icon, title, sub, recommended }) {
  return (
    <button style={{
      width: '100%', padding: '16px 16px', borderRadius: 14,
      background: '#fff', border: `2px solid ${recommended ? color : ps_line}`,
      marginBottom: 10, cursor: 'pointer', textAlign: 'left',
      display: 'flex', alignItems: 'center', gap: 14, fontFamily: ps_font,
      position: 'relative',
    }}>
      <div style={{
        width: 48, height: 48, borderRadius: 12, background: bg, color,
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        <PSIcon d={icon} size={24} sw={2.2}/>
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 17, fontWeight: 800, color: ps_ink, letterSpacing: -0.3 }}>{title}</div>
        {sub && <div style={{ fontSize: 13, fontWeight: 600, color: ps_ink3, marginTop: 2 }}>{sub}</div>}
      </div>
      {recommended && (
        <div style={{
          position: 'absolute', top: -10, right: 14,
          background: color, color: '#fff',
          fontSize: 10.5, fontWeight: 800, padding: '3px 8px',
          borderRadius: 999, letterSpacing: 0.5, textTransform: 'uppercase',
        }}>Fastest</div>
      )}
      <PSIcon d={PI.chev} size={20} stroke={ps_ink3}/>
    </button>
  );
}

function State_PayMethod({ total }) {
  const stripeFee = +(total * 0.03).toFixed(2);
  const stripeTotal = +(total + stripeFee).toFixed(2);
  return (
    <Sheet
      title="How is it paid?"
      subtitle={`Total · $${total.toFixed(2)}`}
      onBack
    >
      <PayMethod
        icon={PI.tap} bg={ps_blueBg} color={ps_blue}
        title={`Tap to Pay · $${stripeTotal.toFixed(2)}`}
        sub={`Stripe · includes 3% surcharge ($${stripeFee.toFixed(2)})`}
        recommended
      />
      <PayMethod
        icon={PI.cash} bg={ps_greenBg} color={ps_green}
        title="Cash" sub="Mark as received"
      />
      <PayMethod
        icon={PI.cheque} bg={ps_amberBg} color={ps_amber}
        title="Check" sub="Record check number"
      />
      <PayMethod
        icon={PI.mail} bg={ps_violetBg} color={ps_violet}
        title="Send invoice" sub="Text + email · pay online"
      />
    </Sheet>
  );
}

// ─── State 6: Tap-to-Pay waiting ───────────────────────────

function State_TapWaiting({ total }) {
  const stripeFee = +(total * 0.03).toFixed(2);
  const chargeTotal = +(total + stripeFee).toFixed(2);
  return (
    <Sheet title="Ready to tap" subtitle="Hand the phone to the customer" onBack>
      <div style={{
        background: ps_ink, borderRadius: 18, padding: '32px 24px',
        color: '#fff', textAlign: 'center',
      }}>
        <div style={{ fontSize: 12.5, fontWeight: 800, letterSpacing: 2, opacity: 0.6 }}>
          AMOUNT
        </div>
        <div style={{
          fontFamily: ps_mono, fontSize: 56, fontWeight: 800,
          letterSpacing: -2, marginTop: 4, lineHeight: 1,
        }}>
          ${chargeTotal.toFixed(2)}
        </div>
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          marginTop: 10, padding: '5px 12px', borderRadius: 999,
          background: 'rgba(147,197,253,0.15)', border: '1px solid rgba(147,197,253,0.35)',
          fontSize: 12, fontWeight: 700, color: '#BFDBFE', letterSpacing: -0.1,
          fontFamily: ps_mono,
        }}>
          ${total.toFixed(2)} + ${stripeFee.toFixed(2)} Stripe surcharge
        </div>

        <div style={{
          marginTop: 28, padding: '28px 16px', borderRadius: 16,
          background: 'rgba(255,255,255,0.06)', border: '2px dashed rgba(255,255,255,0.25)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12,
        }}>
          <div style={{
            width: 96, height: 96, borderRadius: 48,
            background: 'rgba(29,78,216,0.25)', border: '2px solid rgba(96,165,250,0.6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            position: 'relative',
          }}>
            <PSIcon d={PI.tap} size={42} stroke="#93C5FD" sw={2}/>
            <div style={{
              position: 'absolute', inset: -8, borderRadius: 52,
              border: '2px solid rgba(147,197,253,0.35)',
            }}/>
          </div>
          <div style={{ fontSize: 17, fontWeight: 800, letterSpacing: -0.2 }}>
            Hold card near the top of the phone
          </div>
          <div style={{ fontSize: 13, opacity: 0.7, fontWeight: 600 }}>
            Card, Apple Pay, or Google Pay accepted
          </div>
        </div>
      </div>

      <div style={{ marginTop: 14 }}>
        <Btn kind="ghost">Cancel & choose another method</Btn>
      </div>
    </Sheet>
  );
}

// ─── State 7: Paid confirmation ────────────────────────────

function State_Paid({ total, method = 'Tap to Pay · Visa •4821', stripe = true }) {
  const stripeFee = stripe ? +(total * 0.03).toFixed(2) : 0;
  const grandTotal = +(total + stripeFee).toFixed(2);
  return (
    <Sheet title="Payment received" onClose
      footer={
        <div style={{ display: 'flex', gap: 10 }}>
          <Btn kind="secondary" icon={PI.sms}>Text receipt</Btn>
          <Btn kind="primary" color={ps_ink}>Done</Btn>
        </div>
      }
    >
      <div style={{
        textAlign: 'center', padding: '20px 0 8px',
      }}>
        <div style={{
          width: 88, height: 88, borderRadius: 44,
          background: ps_greenBg, border: `3px solid ${ps_green}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 12px',
        }}>
          <PSIcon d={PI.check} size={44} stroke={ps_green} sw={3.5}/>
        </div>
        <div style={{
          fontFamily: ps_mono, fontSize: 44, fontWeight: 800,
          letterSpacing: -1.5, color: ps_ink, lineHeight: 1,
        }}>
          ${grandTotal.toFixed(2)}
        </div>
        <div style={{ fontSize: 14, fontWeight: 700, color: ps_ink3, marginTop: 8 }}>
          Paid via {method}
        </div>
      </div>

      <div style={{
        marginTop: 18, padding: 14, borderRadius: 14,
        background: ps_soft, border: `1.5px solid ${ps_line}`,
      }}>
        <div style={{ fontSize: 11.5, fontWeight: 800, color: ps_ink4, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
          Receipt
        </div>
        {[
          ['Sprinkler head replacement ×2', '$90.00'],
          ['Valve wire splice', '$35.00'],
        ].map(([l, p]) => (
          <div key={l} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', fontSize: 14 }}>
            <span style={{ color: ps_ink2, fontWeight: 600 }}>{l}</span>
            <span style={{ fontFamily: ps_mono, color: ps_ink, fontWeight: 700 }}>{p}</span>
          </div>
        ))}
        <div style={{ height: 1, background: ps_line, margin: '8px 0' }}/>
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 14 }}>
          <span style={{ color: ps_ink2, fontWeight: 600 }}>Subtotal</span>
          <span style={{ fontFamily: ps_mono, color: ps_ink2, fontWeight: 700 }}>${total.toFixed(2)}</span>
        </div>
        {stripe && (
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: 14 }}>
            <span style={{ color: ps_ink2, fontWeight: 600 }}>Stripe surcharge (3%)</span>
            <span style={{ fontFamily: ps_mono, color: ps_ink2, fontWeight: 700 }}>+${stripeFee.toFixed(2)}</span>
          </div>
        )}
        <div style={{ height: 1, background: ps_line, margin: '8px 0' }}/>
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
          <span style={{ fontSize: 15, fontWeight: 800, color: ps_ink }}>Total charged</span>
          <span style={{ fontFamily: ps_mono, fontSize: 16, fontWeight: 800, color: ps_ink }}>${grandTotal.toFixed(2)}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 10, fontSize: 12, color: ps_ink4, fontWeight: 600 }}>
          <PSIcon d={PI.link} size={12}/> Reference · ch_3Q8xLm2e · Apr 22, 10:48 AM
        </div>
      </div>
    </Sheet>
  );
}

// ─── State 8: Invoice sent, unpaid ─────────────────────────

function State_InvoiceSent({ total }) {
  return (
    <Sheet title="Invoice sent" subtitle="Waiting on payment" onClose
      footer={
        <div style={{ display: 'flex', gap: 10 }}>
          <Btn kind="ghost" icon={PI.sms}>Resend</Btn>
          <Btn kind="primary" color={ps_ink}>Done</Btn>
        </div>
      }
    >
      <div style={{ textAlign: 'center', padding: '12px 0' }}>
        <div style={{
          width: 72, height: 72, borderRadius: 36,
          background: ps_violetBg, border: `3px solid ${ps_violet}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 10px', color: ps_violet,
        }}>
          <PSIcon d={PI.mail} size={34} sw={2}/>
        </div>
        <div style={{ fontSize: 17, fontWeight: 800, color: ps_ink, letterSpacing: -0.3 }}>
          Invoice #INV-2042
        </div>
        <div style={{ fontSize: 14, fontWeight: 700, color: ps_ink3, marginTop: 2 }}>
          Due in 7 days · ${total.toFixed(2)}
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        <div style={{ fontSize: 12, fontWeight: 800, color: ps_ink4, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
          Sent to
        </div>
        <div style={{
          padding: 14, borderRadius: 12,
          background: '#fff', border: `1.5px solid ${ps_line}`,
          display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8,
        }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: ps_blueBg, color: ps_blue, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <PSIcon d={PI.sms} size={18}/>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11.5, fontWeight: 700, color: ps_ink4, textTransform: 'uppercase', letterSpacing: 0.8 }}>Text</div>
            <div style={{ fontSize: 15, fontWeight: 800, fontFamily: ps_mono, color: ps_ink }}>(952) 737-3312</div>
          </div>
          <div style={{
            background: ps_greenBg, color: ps_green, padding: '4px 10px',
            borderRadius: 999, fontSize: 11.5, fontWeight: 800, letterSpacing: 0.5, textTransform: 'uppercase',
          }}>Delivered</div>
        </div>
        <div style={{
          padding: 14, borderRadius: 12,
          background: '#fff', border: `1.5px solid ${ps_line}`,
          display: 'flex', alignItems: 'center', gap: 12,
        }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: ps_violetBg, color: ps_violet, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <PSIcon d={PI.mail} size={18}/>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11.5, fontWeight: 700, color: ps_ink4, textTransform: 'uppercase', letterSpacing: 0.8 }}>Email</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: ps_ink2 }}>test@example.com</div>
          </div>
          <div style={{
            background: ps_greenBg, color: ps_green, padding: '4px 10px',
            borderRadius: 999, fontSize: 11.5, fontWeight: 800, letterSpacing: 0.5, textTransform: 'uppercase',
          }}>Delivered</div>
        </div>
      </div>

      <div style={{ marginTop: 16, padding: 14, borderRadius: 14, background: ps_amberBg, border: `1.5px solid ${ps_amber}` }}>
        <div style={{ fontSize: 14, fontWeight: 800, color: ps_amber, letterSpacing: -0.2 }}>
          Status will auto-update when paid
        </div>
        <div style={{ fontSize: 13, fontWeight: 600, color: ps_amber, marginTop: 3 }}>
          Customer can pay online with card via the link we sent.
        </div>
      </div>
    </Sheet>
  );
}

Object.assign(window, {
  State_Start, State_Picker, State_Ready,
  State_OneOffReady, State_PayMethod, State_TapWaiting,
  State_Paid, State_InvoiceSent,
});
