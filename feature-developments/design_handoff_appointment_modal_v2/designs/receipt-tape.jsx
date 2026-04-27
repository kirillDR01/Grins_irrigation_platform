// Direction B — alternate metaphor: "Receipt Tape"
// Full-bleed vertical receipt; extras stack onto it in real time.
// Same data model, different feel — for comparison only.

const rt_ink = '#0B1220';
const rt_line = '#E5E7EB';
const rt_soft = '#F9FAFB';
const rt_green = '#047857';
const rt_greenBg = '#D1FAE5';
const rt_blue = '#1D4ED8';
const rt_ink3 = '#4B5563';
const rt_ink4 = '#6B7280';
const rt_font = '"Inter", system-ui, sans-serif';
const rt_mono = '"JetBrains Mono", ui-monospace, monospace';

function ReceiptTape({ agreement }) {
  const base = { name: 'Spring startup', detail: '90-min service · included', price: 0, locked: true };
  const extras = [
    { name: 'Sprinkler head replacement', detail: '4" pop-up · ×2', price: 90 },
    { name: 'Valve wire splice', detail: '1 splice', price: 35 },
  ];
  const total = extras.reduce((s, i) => s + i.price, 0);

  return (
    <div style={{
      width: 560, fontFamily: rt_font, color: rt_ink,
      background: '#EDE7DC',
      borderRadius: 20, padding: 32,
      boxShadow: '0 30px 60px rgba(10,15,30,0.14)',
    }}>
      {/* paper */}
      <div style={{
        background: '#FCFAF5', borderRadius: '2px 2px 12px 12px',
        padding: '28px 28px 8px',
        boxShadow: '0 1px 0 #fff inset, 0 20px 40px rgba(0,0,0,0.08)',
        position: 'relative',
      }}>
        {/* torn top */}
        <div style={{
          position: 'absolute', top: -10, left: 0, right: 0, height: 14,
          background: 'repeating-linear-gradient(135deg, #FCFAF5 0 8px, transparent 8px 16px)',
        }}/>
        <div style={{ textAlign: 'center', borderBottom: `2px dashed ${rt_line}`, paddingBottom: 14 }}>
          <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 3, color: rt_ink4, textTransform: 'uppercase' }}>
            Grin's Irrigation
          </div>
          <div style={{ fontFamily: rt_mono, fontSize: 11, color: rt_ink4, marginTop: 4 }}>
            VISIT · 04/22/2026 · 09:00
          </div>
          <div style={{ fontSize: 20, fontWeight: 800, color: rt_ink, marginTop: 10, letterSpacing: -0.3 }}>
            Test User · 1 Test St.
          </div>
        </div>

        {agreement && (
          <div style={{
            marginTop: 14, padding: '10px 12px', borderRadius: 10,
            background: rt_greenBg, border: `1.5px solid ${rt_green}`,
            fontSize: 13, fontWeight: 800, color: rt_green, textAlign: 'center', letterSpacing: -0.2,
          }}>
            ✓ AGREEMENT · {agreement.toUpperCase()}
          </div>
        )}

        <div style={{ padding: '14px 0 6px' }}>
          <RTLine {...base}/>
          {extras.map((e, i) => <RTLine key={i} {...e}/>)}
        </div>

        <div style={{ borderTop: `2px dashed ${rt_line}`, paddingTop: 12, marginTop: 6 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, color: rt_ink3, fontWeight: 700 }}>
            <span>Extras subtotal</span>
            <span style={{ fontFamily: rt_mono }}>${total.toFixed(2)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 10 }}>
            <span style={{ fontSize: 20, fontWeight: 800, letterSpacing: -0.3 }}>TOTAL DUE</span>
            <span style={{ fontFamily: rt_mono, fontSize: 28, fontWeight: 800, letterSpacing: -1 }}>
              ${total.toFixed(2)}
            </span>
          </div>
        </div>

        <div style={{ textAlign: 'center', padding: '16px 0 6px', borderTop: `2px dashed ${rt_line}`, marginTop: 14 }}>
          <div style={{ fontFamily: rt_mono, fontSize: 10, color: rt_ink4, letterSpacing: 2 }}>
            █  ▌█▌ █  ▌██  █▌ █  ▌█
          </div>
        </div>
      </div>

      {/* Actions outside the paper */}
      <div style={{ marginTop: 18, display: 'flex', gap: 10 }}>
        <button style={{
          flex: 1, minHeight: 60, borderRadius: 14,
          background: '#fff', color: rt_ink, border: `2px solid ${rt_line}`,
          fontFamily: rt_font, fontSize: 15, fontWeight: 800, cursor: 'pointer',
        }}>+ Add extra</button>
        <button style={{
          flex: 2, minHeight: 60, borderRadius: 14,
          background: rt_ink, color: '#fff', border: 'none',
          fontFamily: rt_font, fontSize: 16, fontWeight: 800, cursor: 'pointer',
          letterSpacing: -0.2,
        }}>Charge ${total.toFixed(2)} →</button>
      </div>
    </div>
  );
}

function RTLine({ name, detail, price, locked }) {
  return (
    <div style={{ padding: '10px 0', borderBottom: `1px dotted ${rt_line}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 15, fontWeight: 800, color: rt_ink, letterSpacing: -0.2 }}>{name}</div>
          <div style={{ fontSize: 12.5, color: rt_ink4, fontWeight: 600, marginTop: 1 }}>{detail}</div>
        </div>
        <div style={{
          fontFamily: rt_mono, fontSize: 16, fontWeight: 800,
          color: locked ? rt_ink4 : rt_ink,
          textDecoration: locked ? 'line-through' : 'none',
        }}>
          ${price.toFixed(2)}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { ReceiptTape });
