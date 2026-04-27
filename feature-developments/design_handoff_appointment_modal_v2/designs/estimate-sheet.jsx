// Estimate flow — mirrors payment-sheet structure.
// States:
//  1. Start (empty) → add line items
//  2. Add line item picker (same pattern as payment picker)
//  3. Ready to send (line items + total) with SMS/Email toggle
//  4. SMS preview (plain text)
//  5. Sent — waiting for customer
//  6. Customer phone view (SMS + decision)
//  7. Approved confirmation
//  8. Declined confirmation

const es_ink   = '#0B1220';
const es_ink2  = '#1F2937';
const es_ink3  = '#4B5563';
const es_ink4  = '#6B7280';
const es_line  = '#E5E7EB';
const es_line2 = '#F3F4F6';
const es_soft  = '#F9FAFB';
const es_surf  = '#FFFFFF';

const es_blue     = '#1D4ED8';
const es_blueBg   = '#DBEAFE';
const es_green    = '#047857';
const es_greenBg  = '#D1FAE5';
const es_violet   = '#6D28D9';
const es_violetBg = '#EDE9FE';
const es_amber    = '#B45309';
const es_amberBg  = '#FEF3C7';
const es_red      = '#B91C1C';
const es_redBg    = '#FEE2E2';

const es_font = '"Inter", system-ui, sans-serif';
const es_mono = '"JetBrains Mono", ui-monospace, monospace';

const ES_CATALOG = [
  { id: 'head-4', name: 'Sprinkler head replacement', detail: '4" pop-up', price: 45 },
  { id: 'head-6', name: 'Sprinkler head replacement', detail: '6" pop-up', price: 55 },
  { id: 'rotor', name: 'Rotor head replacement', detail: 'Standard residential', price: 75 },
  { id: 'controller', name: 'Smart controller install', detail: 'Parts + labor', price: 325 },
  { id: 'backflow', name: 'Backflow test', detail: 'Certified test & report', price: 95 },
  { id: 'valve', name: 'Valve rebuild', detail: '1" residential', price: 85 },
  { id: 'zone-add', name: 'Add zone (full)', detail: '6-head zone + trenching', price: 620 },
  { id: 'dripline', name: 'Drip line install', detail: 'Per 50 ft', price: 180 },
];

function EIcon({ d, size = 16, sw = 2, stroke = 'currentColor', fill = 'none' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={stroke} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
      {typeof d === 'string' ? <path d={d}/> : d}
    </svg>
  );
}

const EI = {
  x: 'M18 6 6 18M6 6l12 12',
  chev: 'M9 6l6 6-6 6',
  back: 'M15 18l-6-6 6-6',
  search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>,
  plus: 'M12 5v14M5 12h14',
  trash: <><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14"/></>,
  check: 'M4 12l5 5 11-11',
  pencil: 'M11 4h-7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7M18.5 2.5a2.1 2.1 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5Z',
  sms: 'M21 11.5A8.38 8.38 0 0 1 12.5 20a8.5 8.5 0 0 1-4-1L3 20l1-4.5A8.5 8.5 0 0 1 12.5 3 8.38 8.38 0 0 1 21 11.5Z',
  mail: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 7 9-7"/></>,
  send: 'M22 2 11 13M22 2l-7 20-4-9-9-4 20-7Z',
  doc: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/></>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  thumb: 'M7 11V21a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V12a1 1 0 0 1 1-1h4Zm0 0 5-9a2 2 0 0 1 2 1v4h5a2 2 0 0 1 2 2l-2 7a2 2 0 0 1-2 1H7',
  thumbD: 'M17 13V3a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-4Zm0 0-5 9a2 2 0 0 1-2-1v-4H5a2 2 0 0 1-2-2l2-7a2 2 0 0 1 2-1h10',
};

function ESheet({ title, subtitle, onBack, onClose, children, footer, pad = true }) {
  return (
    <div style={{
      width: 560, background: es_surf, borderRadius: 20, overflow: 'hidden',
      border: `1px solid ${es_line}`,
      boxShadow: '0 30px 60px rgba(10,15,30,0.14), 0 4px 12px rgba(10,15,30,0.05)',
      fontFamily: es_font, color: es_ink,
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0 4px' }}>
        <div style={{ width: 44, height: 5, borderRadius: 3, background: es_line }}/>
      </div>
      <div style={{ padding: '4px 20px 16px', display: 'flex', alignItems: 'center', gap: 12 }}>
        {onBack && (
          <button style={{
            width: 44, height: 44, borderRadius: 12, border: `1.5px solid ${es_line}`,
            background: '#fff', color: es_ink2, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}><EIcon d={EI.back} size={20} sw={2.4}/></button>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5, color: es_ink, lineHeight: 1.1 }}>{title}</div>
          {subtitle && <div style={{ fontSize: 13.5, fontWeight: 600, color: es_ink3, marginTop: 3 }}>{subtitle}</div>}
        </div>
        {onClose && (
          <button style={{
            width: 44, height: 44, borderRadius: 12, border: `1.5px solid ${es_line}`,
            background: '#fff', color: es_ink2, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}><EIcon d={EI.x} size={20} sw={2.4}/></button>
        )}
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: pad ? '0 20px 20px' : 0 }}>{children}</div>
      {footer && (
        <div style={{ padding: '14px 20px 18px', background: es_soft, borderTop: `1px solid ${es_line}` }}>
          {footer}
        </div>
      )}
    </div>
  );
}

function EBtn({ kind = 'primary', color, children, icon, iconRight, disabled, style }) {
  const base = {
    width: '100%', minHeight: 60, borderRadius: 14, fontFamily: es_font,
    fontSize: 17, fontWeight: 800, letterSpacing: -0.2,
    cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.45 : 1,
    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
    padding: '0 16px', border: '2px solid transparent',
  };
  const styles = {
    primary: { background: color || es_ink, color: '#fff', borderColor: color || es_ink },
    secondary: { background: '#fff', color: color || es_ink, borderColor: color || es_ink },
    ghost: { background: '#fff', color: es_ink2, borderColor: es_line },
    danger: { background: '#fff', color: es_red, borderColor: '#FCA5A5' },
  };
  return (
    <button disabled={disabled} style={{ ...base, ...styles[kind], ...style }}>
      {icon && <EIcon d={icon} size={20} sw={2.4}/>}
      <span>{children}</span>
      {iconRight && <EIcon d={iconRight} size={18} sw={2.4}/>}
    </button>
  );
}

function ELine({ name, detail, price, qty = 1, onRemove }) {
  return (
    <div style={{
      padding: '12px 14px', borderRadius: 12, background: '#fff',
      border: `1.5px solid ${es_line}`, marginBottom: 8,
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 15, fontWeight: 800, color: es_ink, letterSpacing: -0.2 }}>{name}</div>
        {detail && <div style={{ fontSize: 13, color: es_ink3, fontWeight: 600, marginTop: 1 }}>{detail}{qty > 1 ? ` · qty ${qty}` : ''}</div>}
      </div>
      <div style={{ fontFamily: es_mono, fontSize: 16, fontWeight: 800, color: es_ink, minWidth: 72, textAlign: 'right' }}>
        ${price.toFixed(2)}
      </div>
      {onRemove && (
        <button style={{
          width: 36, height: 36, borderRadius: 10, background: '#fff',
          border: `1.5px solid ${es_line}`, color: es_red, cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}><EIcon d={EI.trash} size={16} sw={2.2}/></button>
      )}
    </div>
  );
}

// ─── 1. Start ─────────────────────────────────────

function E1_Start() {
  return (
    <ESheet title="Send estimate" subtitle="Build a quote for work beyond today's visit" onClose
      footer={<EBtn kind="primary" disabled>Next · $0.00</EBtn>}>
      <div style={{
        padding: '14px 16px', borderRadius: 14, marginBottom: 16,
        background: es_violetBg, border: `2px solid ${es_violet}`,
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div style={{
          width: 40, height: 40, borderRadius: 20, background: es_violet, color: '#fff',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}><EIcon d={EI.doc} size={22} sw={2.2}/></div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: es_violet, letterSpacing: -0.2 }}>Estimate for Test User</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: es_violet }}>Customer approves or declines via SMS</div>
        </div>
      </div>

      <div style={{ fontSize: 12, fontWeight: 800, color: es_ink4, textTransform: 'uppercase', letterSpacing: 1, margin: '4px 0 10px' }}>
        Line items
      </div>
      <button style={{
        width: '100%', minHeight: 60, borderRadius: 14,
        background: '#fff', border: `2px dashed ${es_line}`,
        color: es_ink2, fontFamily: es_font, fontSize: 15, fontWeight: 700,
        cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
      }}>
        <EIcon d={EI.plus} size={18} sw={2.6}/> Add service or custom item
      </button>
      <div style={{ fontSize: 13, fontWeight: 600, color: es_ink4, textAlign: 'center', marginTop: 14, lineHeight: 1.4 }}>
        Search from common services or type a custom line with your own price.
      </div>
    </ESheet>
  );
}

// ─── 2. Picker ────────────────────────────────────

function E2_Picker() {
  return (
    <ESheet title="Add line item" subtitle="Search or add custom" onBack>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '0 14px', minHeight: 56, borderRadius: 14,
        background: es_soft, border: `1.5px solid ${es_line}`, marginBottom: 14,
      }}>
        <EIcon d={EI.search} size={20} stroke={es_ink3}/>
        <input defaultValue="zone"
          style={{ flex: 1, border: 'none', background: 'transparent', outline: 'none',
            fontFamily: es_font, fontSize: 17, fontWeight: 700, color: es_ink, letterSpacing: -0.2 }}/>
      </div>
      <div style={{ fontSize: 12, fontWeight: 800, color: es_ink4, textTransform: 'uppercase', letterSpacing: 1, margin: '6px 0 10px' }}>
        Matches
      </div>
      {ES_CATALOG.filter(c => c.name.toLowerCase().includes('zone')).map(c => (
        <button key={c.id} style={{
          width: '100%', padding: '14px', borderRadius: 12,
          border: `1.5px solid ${es_line}`, background: '#fff',
          marginBottom: 8, cursor: 'pointer', textAlign: 'left',
          display: 'flex', alignItems: 'center', gap: 12, fontFamily: es_font,
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: es_ink, letterSpacing: -0.2 }}>{c.name}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: es_ink3, marginTop: 1 }}>{c.detail}</div>
          </div>
          <div style={{ fontFamily: es_mono, fontSize: 16, fontWeight: 800, color: es_ink2 }}>${c.price.toFixed(2)}</div>
          <div style={{
            width: 36, height: 36, borderRadius: 18, background: es_ink, color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><EIcon d={EI.plus} size={18} sw={2.8}/></div>
        </button>
      ))}

      <div style={{ fontSize: 12, fontWeight: 800, color: es_ink4, textTransform: 'uppercase', letterSpacing: 1, margin: '18px 0 10px' }}>
        Common services
      </div>
      {ES_CATALOG.slice(0, 4).map(c => (
        <button key={c.id} style={{
          width: '100%', padding: '14px', borderRadius: 12,
          border: `1.5px solid ${es_line}`, background: '#fff',
          marginBottom: 8, cursor: 'pointer', textAlign: 'left',
          display: 'flex', alignItems: 'center', gap: 12, fontFamily: es_font,
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: es_ink, letterSpacing: -0.2 }}>{c.name}</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: es_ink3, marginTop: 1 }}>{c.detail}</div>
          </div>
          <div style={{ fontFamily: es_mono, fontSize: 16, fontWeight: 800, color: es_ink2 }}>${c.price.toFixed(2)}</div>
        </button>
      ))}

      <button style={{
        width: '100%', padding: '14px', borderRadius: 12,
        border: `1.5px dashed ${es_violet}`, background: es_violetBg,
        color: es_violet, cursor: 'pointer', fontFamily: es_font,
        fontSize: 15, fontWeight: 800, marginTop: 10,
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
      }}>
        <EIcon d={EI.pencil} size={18} sw={2.4}/>
        Custom line — type description + price
      </button>
    </ESheet>
  );
}

// ─── 3. Ready to send ─────────────────────────────

function E3_Ready() {
  const items = [
    { name: 'Add zone (full)', detail: '6-head zone + trenching', price: 620 },
    { name: 'Smart controller install', detail: 'Parts + labor', price: 325 },
    { name: 'Backflow test', detail: 'Certified test & report', price: 95 },
  ];
  const total = items.reduce((s, i) => s + i.price, 0);
  return (
    <ESheet title="Review & send" subtitle="Estimate for Test User" onBack
      footer={<EBtn kind="primary" color={es_violet} icon={EI.send}>Send estimate · ${total.toFixed(2)}</EBtn>}>
      <div style={{ fontSize: 12, fontWeight: 800, color: es_ink4, textTransform: 'uppercase', letterSpacing: 1, margin: '4px 0 10px' }}>
        Line items ({items.length})
      </div>
      {items.map((it, i) => <ELine key={i} {...it} onRemove/>)}
      <button style={{
        width: '100%', minHeight: 52, borderRadius: 12,
        background: '#fff', border: `2px dashed ${es_line}`,
        color: es_ink2, fontFamily: es_font, fontSize: 14.5, fontWeight: 700,
        cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        marginTop: 4,
      }}>
        <EIcon d={EI.plus} size={16} sw={2.6}/> Add another
      </button>

      <div style={{ marginTop: 18, padding: 14, borderRadius: 14, background: es_soft, border: `1.5px solid ${es_line}` }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 17, fontWeight: 800, color: es_ink, letterSpacing: -0.3 }}>Estimate total</span>
          <span style={{ fontFamily: es_mono, fontSize: 24, fontWeight: 800, color: es_ink, letterSpacing: -0.5 }}>
            ${total.toFixed(2)}
          </span>
        </div>
      </div>

      <div style={{ fontSize: 12, fontWeight: 800, color: es_ink4, textTransform: 'uppercase', letterSpacing: 1, margin: '18px 0 10px' }}>
        Send via
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <DeliveryToggle icon={EI.sms} label="Text (SMS)" value="(952) 737-3312" active/>
        <DeliveryToggle icon={EI.mail} label="Email" value="test@example.com"/>
      </div>
    </ESheet>
  );
}

function DeliveryToggle({ icon, label, value, active }) {
  return (
    <button style={{
      flex: 1, padding: '12px 14px', borderRadius: 12,
      background: active ? es_violetBg : '#fff',
      border: `2px solid ${active ? es_violet : es_line}`,
      cursor: 'pointer', textAlign: 'left', fontFamily: es_font,
      display: 'flex', alignItems: 'center', gap: 10,
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: 10,
        background: active ? es_violet : es_soft,
        color: active ? '#fff' : es_ink3,
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}><EIcon d={icon} size={18}/></div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 800, color: active ? es_violet : es_ink, letterSpacing: -0.1 }}>{label}</div>
        <div style={{ fontSize: 11.5, fontWeight: 600, color: active ? es_violet : es_ink4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</div>
      </div>
    </button>
  );
}

// ─── 4. SMS preview ───────────────────────────────

function E4_Preview() {
  const body =
`Hi Test — Grin's Irrigation here. Viktor put together an estimate from today's visit:

• Add zone (full) — $620.00
• Smart controller install — $325.00
• Backflow test — $95.00

Total: $1,040.00

Reply YES to approve or NO to decline. Or view & sign: grins.io/e/8F2K`;
  return (
    <ESheet title="Preview message" subtitle="This is what the customer sees" onBack
      footer={<EBtn kind="primary" color={es_violet} icon={EI.send}>Send now</EBtn>}>
      <div style={{
        padding: '12px 14px', borderRadius: 12, background: es_soft, border: `1.5px solid ${es_line}`,
        marginBottom: 14, display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, background: es_violet, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <EIcon d={EI.sms} size={18}/>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 11.5, fontWeight: 700, color: es_ink4, textTransform: 'uppercase', letterSpacing: 0.8 }}>To</div>
          <div style={{ fontSize: 15, fontWeight: 800, fontFamily: es_mono, color: es_ink }}>(952) 737-3312</div>
        </div>
      </div>
      <div style={{
        padding: 14, borderRadius: 14, border: `1.5px solid ${es_line}`, background: '#fff',
      }}>
        <div style={{ fontSize: 11.5, fontWeight: 700, color: es_ink4, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 8 }}>SMS body</div>
        <pre style={{
          margin: 0, fontFamily: es_font, fontSize: 14.5, lineHeight: 1.55,
          color: es_ink, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontWeight: 500,
        }}>{body}</pre>
      </div>
      <div style={{ fontSize: 12, fontWeight: 600, color: es_ink4, textAlign: 'center', marginTop: 12 }}>
        Reply is tracked — the appointment updates automatically.
      </div>
    </ESheet>
  );
}

// ─── 5. Sent / waiting ────────────────────────────

function E5_Waiting() {
  return (
    <ESheet title="Estimate sent" subtitle="Waiting on customer reply" onClose
      footer={<div style={{ display: 'flex', gap: 10 }}>
        <EBtn kind="ghost" icon={EI.sms}>Resend</EBtn>
        <EBtn kind="primary" color={es_ink}>Done</EBtn>
      </div>}>
      <div style={{ textAlign: 'center', padding: '14px 0' }}>
        <div style={{
          width: 80, height: 80, borderRadius: 40,
          background: es_violetBg, border: `3px solid ${es_violet}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 10px', color: es_violet,
        }}>
          <EIcon d={EI.send} size={36} sw={2}/>
        </div>
        <div style={{ fontSize: 20, fontWeight: 800, color: es_ink, letterSpacing: -0.4 }}>
          Estimate #EST-0142
        </div>
        <div style={{ fontFamily: es_mono, fontSize: 15, fontWeight: 700, color: es_ink3, marginTop: 2 }}>
          $1,040.00 · sent 10:52 AM
        </div>
      </div>

      <div style={{ padding: 14, borderRadius: 12, background: '#fff', border: `1.5px solid ${es_line}`,
        display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <div style={{ width: 36, height: 36, borderRadius: 10, background: es_blueBg, color: es_blue, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <EIcon d={EI.sms} size={18}/>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 11.5, fontWeight: 700, color: es_ink4, textTransform: 'uppercase', letterSpacing: 0.8 }}>Text</div>
          <div style={{ fontSize: 15, fontWeight: 800, fontFamily: es_mono, color: es_ink }}>(952) 737-3312</div>
        </div>
        <div style={{ background: es_greenBg, color: es_green, padding: '4px 10px', borderRadius: 999, fontSize: 11.5, fontWeight: 800, letterSpacing: 0.5, textTransform: 'uppercase' }}>Delivered</div>
      </div>

      <div style={{ padding: 14, borderRadius: 14, background: es_amberBg, border: `1.5px solid ${es_amber}`, marginTop: 10 }}>
        <div style={{ fontSize: 14, fontWeight: 800, color: es_amber, letterSpacing: -0.2, display: 'flex', alignItems: 'center', gap: 6 }}>
          <EIcon d={EI.clock} size={14} stroke={es_amber} sw={2.4}/>
          Awaiting reply
        </div>
        <div style={{ fontSize: 13, fontWeight: 600, color: es_amber, marginTop: 3 }}>
          You'll get notified when Test User approves or declines.
        </div>
      </div>
    </ESheet>
  );
}

// ─── 6. Customer phone view ───────────────────────

function E6_CustomerSMS() {
  return (
    <div style={{ width: 400, fontFamily: es_font }}>
      <div style={{
        background: '#000', borderRadius: 44, padding: 14,
        boxShadow: '0 30px 60px rgba(10,15,30,0.25)',
      }}>
        <div style={{ background: '#F5F5F7', borderRadius: 32, overflow: 'hidden', minHeight: 780 }}>
          {/* status bar */}
          <div style={{ padding: '14px 28px 8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13, fontWeight: 700, color: es_ink }}>
            <span>10:53</span>
            <span style={{ fontFamily: es_mono }}>●●●● 5G  ▮▮▮</span>
          </div>
          {/* msg header */}
          <div style={{ padding: '8px 16px 14px', borderBottom: `0.5px solid ${es_line}`, textAlign: 'center' }}>
            <div style={{ width: 56, height: 56, borderRadius: 28, background: es_violetBg, color: es_violet, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 6px', fontWeight: 800, fontSize: 20 }}>G</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: es_ink }}>Grin's Irrigation</div>
            <div style={{ fontSize: 11, color: es_ink4, fontFamily: es_mono }}>+1 (612) 555-0142</div>
          </div>
          {/* message bubble */}
          <div style={{ padding: '18px 16px' }}>
            <div style={{ fontSize: 11, color: es_ink4, textAlign: 'center', marginBottom: 8 }}>Today 10:52 AM</div>
            <div style={{
              background: '#fff', padding: '12px 14px', borderRadius: 20,
              borderTopLeftRadius: 6, maxWidth: '88%',
              fontSize: 14.5, lineHeight: 1.5, color: es_ink, fontWeight: 500,
              whiteSpace: 'pre-wrap', boxShadow: '0 1px 1px rgba(0,0,0,0.04)',
            }}>{`Hi Test — Grin's Irrigation here. Viktor put together an estimate from today's visit:

• Add zone (full) — $620.00
• Smart controller install — $325.00
• Backflow test — $95.00

Total: $1,040.00

Reply YES to approve or NO to decline. Or view & sign: grins.io/e/8F2K`}</div>
          </div>

          {/* Action panel — "smart actions" above keyboard */}
          <div style={{ margin: '12px 12px 0', padding: 14, borderRadius: 18, background: '#fff', boxShadow: '0 8px 20px rgba(0,0,0,0.06)' }}>
            <div style={{ fontSize: 11.5, fontWeight: 800, color: es_ink4, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10, textAlign: 'center' }}>
              Quick reply
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button style={{
                flex: 1, padding: '14px 12px', borderRadius: 14,
                background: es_green, color: '#fff', border: 'none',
                fontFamily: es_font, fontWeight: 800, fontSize: 15, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}>
                <EIcon d={EI.thumb} size={18} sw={2.2}/>
                YES — Approve
              </button>
              <button style={{
                flex: 1, padding: '14px 12px', borderRadius: 14,
                background: '#fff', color: es_red, border: `2px solid #FCA5A5`,
                fontFamily: es_font, fontWeight: 800, fontSize: 15, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}>
                <EIcon d={EI.thumbD} size={18} sw={2.2}/>
                NO — Decline
              </button>
            </div>
            <div style={{ fontSize: 11.5, fontWeight: 600, color: es_ink4, marginTop: 10, textAlign: 'center' }}>
              Or tap the link to review & sign online
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── 7 & 8. Outcomes ─────────────────────────────

function E7_Approved() {
  return (
    <ESheet title="Customer approved!" subtitle="Estimate #EST-0142 · $1,040.00" onClose
      footer={<div style={{ display: 'flex', gap: 10 }}>
        <EBtn kind="secondary">View estimate</EBtn>
        <EBtn kind="primary" color={es_ink}>Schedule follow-up</EBtn>
      </div>}>
      <div style={{ textAlign: 'center', padding: '14px 0' }}>
        <div style={{
          width: 88, height: 88, borderRadius: 44,
          background: es_greenBg, border: `3px solid ${es_green}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 12px',
        }}>
          <EIcon d={EI.check} size={44} stroke={es_green} sw={3.5}/>
        </div>
        <div style={{ fontSize: 26, fontWeight: 800, color: es_ink, letterSpacing: -0.5 }}>
          Approved
        </div>
        <div style={{ fontSize: 14, fontWeight: 700, color: es_ink3, marginTop: 6 }}>
          Test User replied YES · 11:04 AM
        </div>
      </div>
      <div style={{ padding: 14, borderRadius: 14, background: es_soft, border: `1.5px solid ${es_line}`, marginTop: 6 }}>
        <div style={{ fontSize: 11.5, fontWeight: 800, color: es_ink4, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
          Next step
        </div>
        <div style={{ fontSize: 14.5, fontWeight: 700, color: es_ink2, lineHeight: 1.45 }}>
          Create a follow-up job for the approved work. Pricing and line items carry over automatically.
        </div>
      </div>
    </ESheet>
  );
}

function E8_Declined() {
  return (
    <ESheet title="Customer declined" subtitle="Estimate #EST-0142" onClose
      footer={<div style={{ display: 'flex', gap: 10 }}>
        <EBtn kind="ghost">Archive</EBtn>
        <EBtn kind="primary" color={es_ink}>Revise & resend</EBtn>
      </div>}>
      <div style={{ textAlign: 'center', padding: '14px 0' }}>
        <div style={{
          width: 88, height: 88, borderRadius: 44,
          background: es_redBg, border: `3px solid #FCA5A5`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 12px', color: es_red,
        }}>
          <EIcon d={EI.x} size={40} sw={3.2}/>
        </div>
        <div style={{ fontSize: 22, fontWeight: 800, color: es_ink, letterSpacing: -0.4 }}>
          Not this time
        </div>
        <div style={{ fontSize: 14, fontWeight: 700, color: es_ink3, marginTop: 6 }}>
          Test User replied NO · 11:04 AM
        </div>
      </div>
      <div style={{ padding: 14, borderRadius: 14, background: es_soft, border: `1.5px solid ${es_line}`, marginTop: 6 }}>
        <div style={{ fontSize: 14.5, fontWeight: 700, color: es_ink2, lineHeight: 1.45 }}>
          You can revise the line items and resend, or archive this estimate. The original appointment is unaffected.
        </div>
      </div>
    </ESheet>
  );
}

Object.assign(window, {
  E1_Start, E2_Picker, E3_Ready, E4_Preview,
  E5_Waiting, E6_CustomerSMS, E7_Approved, E8_Declined,
});
