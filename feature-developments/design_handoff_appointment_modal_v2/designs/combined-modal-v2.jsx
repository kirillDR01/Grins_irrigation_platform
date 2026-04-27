// Combined modal v2 — extends combined-modal.jsx with:
//  - Inline expandable "Attached photos" panel under the secondary actions row
//  - Inline expandable "Attached notes" panel with view + edit
//  - Add photo / Notes buttons now toggle their own attached panels
//
// Reuses tokens, icons, and primitives from combined-modal.jsx (loaded first).

const v2_ink   = ck_ink;
const v2_ink2  = ck_ink2;
const v2_ink3  = ck_ink3;
const v2_ink4  = ck_ink4;
const v2_line  = ck_line;
const v2_line2 = ck_line2;
const v2_surf  = ck_surf;
const v2_soft  = ck_soft;

// Compact secondary action button — supports 'open' state and trailing chevron/count
function V2LinkBtn({ icon, children, color = v2_ink, bg = '#fff', border = v2_line, onClick, open, count, accent }) {
  const activeBg = accent === 'violet' ? ck_violetBg : accent === 'blue' ? ck_blueBg : accent === 'amber' ? ck_amberBg : v2_line2;
  const activeColor = accent === 'violet' ? ck_violet : accent === 'blue' ? ck_blue : accent === 'amber' ? ck_amber : v2_ink;
  const activeBorder = accent === 'violet' ? ck_violet : accent === 'blue' ? ck_blue : accent === 'amber' ? ck_amber : v2_ink2;
  return (
    <button onClick={onClick} style={{
      minHeight: 44, padding: '0 12px', borderRadius: 12,
      background: open ? activeBg : bg,
      color: open ? activeColor : color,
      border: `1.5px solid ${open ? activeBorder : border}`,
      fontSize: 14, fontWeight: 700, fontFamily: ck_fontUI, cursor: 'pointer',
      display: 'inline-flex', alignItems: 'center', gap: 6, position: 'relative',
    }}>
      {icon && <CKIcon d={icon} size={16} sw={2.2}/>}
      {children}
      {typeof count === 'number' && (
        <span style={{
          marginLeft: 2, padding: '1px 7px', borderRadius: 999,
          background: open ? activeColor : v2_line2,
          color: open ? '#fff' : v2_ink3,
          fontSize: 11.5, fontWeight: 800, fontFamily: ck_fontMono, letterSpacing: -0.2,
          minWidth: 20, textAlign: 'center',
        }}>{count}</span>
      )}
      <CKIcon
        d={open ? 'M6 15l6-6 6 6' : 'M6 9l6 6 6-6'}
        size={14}
        stroke={open ? activeColor : v2_ink4}
        sw={2.4}
      />
    </button>
  );
}

// SVG-based photo placeholder — striped + label, no fake hand-drawn imagery
function V2PhotoCard({ label, caption, date, w = 180, h = 134, hue = 'amber' }) {
  const hueMap = {
    amber: { c1: '#FEF3C7', c2: '#FDE68A', stroke: '#F59E0B', text: '#92400E' },
    teal:  { c1: '#CCFBF1', c2: '#99F6E4', stroke: '#0D9488', text: '#115E59' },
    violet:{ c1: '#EDE9FE', c2: '#DDD6FE', stroke: '#8B5CF6', text: '#5B21B6' },
    blue:  { c1: '#DBEAFE', c2: '#BFDBFE', stroke: '#3B82F6', text: '#1E40AF' },
    slate: { c1: '#E5E7EB', c2: '#D1D5DB', stroke: '#6B7280', text: '#374151' },
  };
  const t = hueMap[hue] || hueMap.amber;
  const stripeId = `stripe-${hue}-${Math.random().toString(36).slice(2, 7)}`;
  return (
    <div style={{
      width: w, flexShrink: 0,
      borderRadius: 12, overflow: 'hidden',
      border: `1.5px solid ${v2_line}`, background: '#fff',
    }}>
      <div style={{ position: 'relative', width: '100%', height: h, background: t.c1 }}>
        <svg width="100%" height="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: 'block' }}>
          <defs>
            <pattern id={stripeId} patternUnits="userSpaceOnUse" width="14" height="14" patternTransform="rotate(45)">
              <rect width="14" height="14" fill={t.c1}/>
              <line x1="0" y1="0" x2="0" y2="14" stroke={t.c2} strokeWidth="6"/>
            </pattern>
          </defs>
          <rect width={w} height={h} fill={`url(#${stripeId})`}/>
        </svg>
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: ck_fontMono, fontSize: 11, fontWeight: 700, color: t.text,
          letterSpacing: 0.5, textTransform: 'uppercase', textAlign: 'center', padding: 6,
        }}>{label}</div>
      </div>
      <div style={{ padding: '8px 10px', borderTop: `1px solid ${v2_line}` }}>
        <div style={{
          fontSize: 12, fontWeight: 700, color: v2_ink, letterSpacing: -0.1,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>{caption}</div>
        <div style={{ fontSize: 10.5, fontWeight: 600, color: v2_ink4, fontFamily: ck_fontMono, marginTop: 1 }}>{date}</div>
      </div>
    </div>
  );
}

// Camera roll icon — phone with photo
const CI_camRoll = <><rect x="3" y="6" width="18" height="14" rx="2"/><circle cx="12" cy="13" r="3.5"/><path d="M8 6l1.5-2h5L16 6"/></>;
const CI_upload = <><path d="M12 16V4"/><path d="m6 10 6-6 6 6"/><path d="M4 20h16"/></>;
function V2AttachedPhotos({ photos }) {
  const list = photos || [
    { label: 'Front yard · zone 1', caption: 'Backflow valve', date: 'Oct 2025', hue: 'amber' },
    { label: 'Side gate access',    caption: 'Back gate code', date: 'Oct 2025', hue: 'teal' },
    { label: 'Rotor head leak',     caption: 'NE corner — replaced', date: 'Oct 2025', hue: 'violet' },
    { label: 'Controller box',      caption: 'Hunter X-Core', date: 'Mar 2024', hue: 'blue' },
    { label: 'Backyard layout',     caption: 'Zone map', date: 'Mar 2024', hue: 'slate' },
  ];
  return (
    <div style={{
      marginTop: 10, borderRadius: 14, overflow: 'hidden',
      border: `1.5px solid ${ck_blue}`, background: '#fff',
    }}>
      <div style={{
        padding: '10px 14px', background: ck_blueBg,
        borderBottom: `1px solid ${v2_line}`,
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <CKIcon d={CI.photo} size={16} stroke={ck_blue} sw={2.4}/>
        <div style={{ fontSize: 13, fontWeight: 800, color: ck_blue, letterSpacing: -0.1 }}>
          Attached photos
        </div>
        <span style={{
          padding: '1px 8px', borderRadius: 999, background: ck_blue, color: '#fff',
          fontSize: 11.5, fontWeight: 800, fontFamily: ck_fontMono,
        }}>{list.length}</span>
        <div style={{ flex: 1 }}/>
        <div style={{ fontSize: 11.5, fontWeight: 700, color: ck_blue, opacity: 0.85 }}>
          From customer file
        </div>
      </div>

      {/* Upload CTAs — primary path for adding from phone camera roll */}
      <div style={{
        padding: 12, display: 'flex', gap: 8,
        borderBottom: `1px solid ${v2_line}`, background: '#fff',
      }}>
        <button style={{
          flex: 1, minHeight: 48, borderRadius: 12,
          background: ck_blue, border: `1.5px solid ${ck_blue}`, color: '#fff',
          fontFamily: ck_fontUI, fontSize: 14.5, fontWeight: 800, letterSpacing: -0.1,
          cursor: 'pointer', display: 'inline-flex', alignItems: 'center',
          justifyContent: 'center', gap: 8, padding: '0 14px',
        }}>
          <CKIcon d={CI_upload} size={18} sw={2.4}/>
          Upload photo
          <span style={{
            marginLeft: 4, fontSize: 11.5, fontWeight: 700, opacity: 0.9,
            fontFamily: ck_fontMono, letterSpacing: 0,
          }}>· camera roll</span>
        </button>
        <button style={{
          minHeight: 48, padding: '0 14px', borderRadius: 12,
          background: '#fff', border: `1.5px solid ${ck_blue}`, color: ck_blue,
          fontFamily: ck_fontUI, fontSize: 14, fontWeight: 800, letterSpacing: -0.1,
          cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6,
        }}>
          <CKIcon d={CI_camRoll} size={18} sw={2.2}/>
          Take photo
        </button>
      </div>

      <div style={{
        padding: 12, display: 'flex', gap: 10, overflowX: 'auto',
        WebkitOverflowScrolling: 'touch',
      }}>
        {list.map((p, i) => <V2PhotoCard key={i} {...p}/>)}
        <button style={{
          width: 110, flexShrink: 0, borderRadius: 12,
          border: `1.5px dashed ${v2_ink4}`, background: v2_soft,
          color: v2_ink2, cursor: 'pointer', fontFamily: ck_fontUI,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          gap: 6, padding: 10,
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: 16, background: '#fff',
            border: `1.5px solid ${v2_line}`, color: v2_ink2,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <CKIcon d={CI.plus} size={16} sw={2.6}/>
          </div>
          <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: -0.1 }}>Add more</div>
          <div style={{ fontSize: 10.5, fontWeight: 600, color: v2_ink4, fontFamily: ck_fontMono }}>From library</div>
        </button>
      </div>
      <div style={{
        padding: '8px 14px 10px', background: v2_soft,
        borderTop: `1px solid ${v2_line}`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10,
      }}>
        <div style={{ fontSize: 11.5, fontWeight: 700, color: v2_ink4 }}>
          Tap a photo to expand · pinch to zoom
        </div>
        <button style={{
          padding: '6px 10px', borderRadius: 8, border: `1.5px solid ${v2_line}`,
          background: '#fff', color: v2_ink2, fontSize: 12, fontWeight: 800,
          fontFamily: ck_fontUI, cursor: 'pointer',
        }}>View all ({list.length})</button>
      </div>
    </div>
  );
}

// Centralized "Internal Notes" panel — single source of truth for everyone
// (dispatch, tech, customer-relayed). Replaces the per-author thread pattern.
const v2_slate = '#64748B';   // muted blue-slate eyebrow color (matches refs)
const v2_teal  = '#14B8A6';   // primary teal CTA (matches Save Notes button)
const v2_tealD = '#0D9488';

function V2InternalNotes({ body, editing }) {
  const text = body !== undefined ? body :
    'Gate code 4521#. Dog is friendly but barks. Replaced rotor head NE corner Oct 12 — backflow tested OK at 65 PSI. Customer asked about smart controller upgrade; quote next visit. Please text on arrival, side gate sometimes locked from inside.';

  return (
    <div style={{
      marginTop: 10, borderRadius: 14, overflow: 'hidden',
      border: `1.5px solid ${v2_line}`, background: '#fff',
      boxShadow: '0 1px 2px rgba(10,15,30,0.04)',
    }}>
      <div style={{
        padding: '18px 20px 14px',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <div style={{
          fontSize: 12.5, fontWeight: 800, color: v2_slate,
          textTransform: 'uppercase', letterSpacing: 1.4,
        }}>
          Internal notes
        </div>
        <div style={{ flex: 1 }}/>
        {!editing && (
          <button style={{
            padding: '4px 4px 4px 0', background: 'transparent', border: 'none',
            cursor: 'pointer', color: v2_slate, fontFamily: ck_fontUI,
            fontSize: 14, fontWeight: 700,
            display: 'inline-flex', alignItems: 'center', gap: 6,
          }}>
            <CKIcon d={CI.pencil} size={16} stroke={v2_slate} sw={2.2}/>
            Edit
          </button>
        )}
      </div>

      {editing ? (
        <div style={{ padding: '0 20px 18px' }}>
          <textarea
            defaultValue={text}
            style={{
              width: '100%', minHeight: 150, padding: '12px 14px',
              borderRadius: 12, border: `1.5px solid ${v2_line}`,
              background: '#fff', color: v2_ink,
              fontFamily: ck_fontUI, fontSize: 14.5, fontWeight: 500,
              lineHeight: 1.5, resize: 'vertical', outline: 'none',
            }}
          />
          <div style={{ display: 'flex', gap: 12, marginTop: 14, justifyContent: 'flex-end' }}>
            <button style={{
              padding: '12px 28px', borderRadius: 999,
              border: `1.5px solid ${v2_line}`, background: '#fff',
              color: v2_ink2, fontSize: 15, fontWeight: 700,
              fontFamily: ck_fontUI, cursor: 'pointer',
              minWidth: 120,
            }}>Cancel</button>
            <button style={{
              padding: '12px 28px', borderRadius: 999,
              border: `1.5px solid ${v2_teal}`, background: v2_teal,
              color: '#fff', fontSize: 15, fontWeight: 700,
              fontFamily: ck_fontUI, cursor: 'pointer',
              minWidth: 140,
            }}>Save Notes</button>
          </div>
        </div>
      ) : (
        <div style={{
          padding: '0 20px 22px', minHeight: 80,
          fontSize: 14.5, fontWeight: 500, color: v2_ink,
          lineHeight: 1.6, letterSpacing: -0.1,
        }}>
          {text}
        </div>
      )}
    </div>
  );
}

// Backwards-compat alias so v1 demos keep working
const V2AttachedNotes = V2InternalNotes;

// ─── THE COMBINED MODAL V2 ──────────────────────────────────

function CombinedModalV2({
  step = 2,
  showMapsPopover = false,
  showEstimate = true,
  showTagsEditMode = false,
  openPanel = null,         // 'photos' | 'notes' | null
  editingNote = false,
  tags: propTags,
}) {
  const defaultTags = [
    { label: 'Repeat customer', tone: 'green' },
    { label: 'Back gate — side yard', tone: 'amber' },
    { label: 'Prefers text', tone: 'blue' },
  ];
  const tags = propTags || defaultTags;
  const photoCount = 5;
  const noteCount = 1;

  return (
    <div style={{
      width: 560, background: v2_surf,
      borderRadius: 18, overflow: 'hidden',
      border: `1px solid ${v2_line}`,
      boxShadow: '0 30px 60px rgba(10,15,30,0.12), 0 4px 12px rgba(10,15,30,0.05)',
      fontFamily: ck_fontUI, color: v2_ink,
    }}>
      {/* Header */}
      <div style={{ padding: '20px 20px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
              <CKStatusBadge step={step}/>
              <CKPill bg={v2_line2} color={v2_ink2}>Residential</CKPill>
              <CKPill bg={v2_line2} color={v2_ink2}>#APT-2086</CKPill>
            </div>
            <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: -0.8, color: v2_ink, lineHeight: 1.1 }}>
              Spring startup · zone check
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, color: v2_ink3, marginTop: 6 }}>
              Thu, Apr 23 · 9:00 – 10:30 AM
            </div>
          </div>
          <button style={{
            width: 40, height: 40, borderRadius: 12, border: `1.5px solid ${v2_line}`,
            background: '#fff', color: v2_ink2, cursor: 'pointer',
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
        padding: '16px 20px 16px', background: v2_soft,
        borderTop: `1px solid ${v2_line}`, borderBottom: `1px solid ${v2_line}`,
      }}>
        <div style={{ fontSize: 12, fontWeight: 800, color: v2_ink3, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 10 }}>
          On-site operations
        </div>
        <CKActionTrack step={step}/>

        {/* Secondary row — now with dropdown affordances on Add photo & Notes */}
        <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
          <V2LinkBtn icon={CI.photo} accent="blue" open={openPanel === 'photos'} count={photoCount}>
            See attached photos
          </V2LinkBtn>
          <V2LinkBtn icon={CI.doc} accent="amber" open={openPanel === 'notes'} count={noteCount}>
            See attached notes
          </V2LinkBtn>
          <CKLinkBtn icon={CI.star}>Send Review Request</CKLinkBtn>
          <CKLinkBtn icon={CI.tag} active={showTagsEditMode}>Edit tags</CKLinkBtn>
        </div>

        {/* Inline expansion panels */}
        {openPanel === 'photos' && <V2AttachedPhotos/>}
        {openPanel === 'notes'  && <V2InternalNotes editing={editingNote}/>}
      </div>

      {/* Collect payment + Send estimate */}
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
      <div style={{ margin: '16px 20px 16px', borderRadius: 14, border: `1.5px solid ${v2_line}`, overflow: 'hidden' }}>
        <div style={{
          padding: '14px 16px', background: ck_tealBg,
          display: 'flex', alignItems: 'center', gap: 12,
          borderBottom: `1px solid ${v2_line}`,
        }}>
          <div style={{
            width: 44, height: 44, borderRadius: 22, background: '#fff',
            color: ck_teal, display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 800, fontSize: 16, border: `2px solid ${ck_teal}`,
          }}>TU</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: v2_ink, letterSpacing: -0.3 }}>Test User</div>
            <div style={{ fontSize: 12.5, fontWeight: 600, color: v2_ink3 }}>1 previous job · Last service Oct 2025</div>
          </div>
        </div>

        <div style={{
          padding: '12px 16px', background: '#fff',
          borderBottom: `1px solid ${v2_line}`,
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <div style={{ fontSize: 11.5, fontWeight: 800, color: v2_ink4, textTransform: 'uppercase', letterSpacing: 0.8, flexShrink: 0 }}>
            Tags
          </div>
          <div style={{ flex: 1, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {tags.map((t, i) => <CKTagChip key={i} tone={t.tone}>{t.label}</CKTagChip>)}
          </div>
        </div>

        <a href="tel:9527373312" style={{
          display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px',
          textDecoration: 'none', color: v2_ink, background: '#fff',
          borderBottom: `1px solid ${v2_line}`,
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10, background: ck_blueBg, color: ck_blue, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><CKIcon d={CI.phone} size={18}/></div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11.5, fontWeight: 700, color: v2_ink4, textTransform: 'uppercase', letterSpacing: 0.8 }}>Phone</div>
            <div style={{ fontSize: 17, fontWeight: 800, fontFamily: ck_fontMono, color: v2_ink, letterSpacing: -0.2 }}>(952) 737-3312</div>
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
          textDecoration: 'none', color: v2_ink, background: '#fff',
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10, background: v2_soft, color: v2_ink3, flexShrink: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><CKIcon d={CI.mail} size={18}/></div>
          <div style={{ fontSize: 14, fontWeight: 600, color: v2_ink2 }}>test@example.com</div>
        </a>
      </div>

      {/* Location */}
      <div style={{
        margin: '0 20px 16px', borderRadius: 14, border: `1.5px solid ${v2_line}`,
        overflow: showMapsPopover ? 'visible' : 'hidden', position: 'relative',
      }}>
        <div style={{ padding: '14px 16px', background: '#fff' }}>
          <div style={{ fontSize: 11.5, fontWeight: 700, color: v2_ink4, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
            <CKIcon d={CI.pin} size={12} stroke={v2_ink4}/> Property
          </div>
          <div style={{ fontSize: 19, fontWeight: 800, color: v2_ink, letterSpacing: -0.3, lineHeight: 1.2 }}>
            1 Test Street
          </div>
          <div style={{ fontSize: 15, fontWeight: 600, color: v2_ink2, marginTop: 2 }}>
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
      <div style={{ margin: '0 20px 16px', borderRadius: 14, border: `1.5px solid ${v2_line}`, overflow: 'hidden', background: '#fff' }}>
        <CKRow icon={CI.tools} label="Scope" value="Full spring startup & zone check" strong/>
        <div style={{ padding: '14px 16px', borderBottom: `1px solid ${v2_line}` }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <CKPill bg={v2_line2} color={v2_ink2}>~90 min</CKPill>
            <CKPill bg={v2_line2} color={v2_ink2}>1 staff</CKPill>
            <CKPill bg={ck_amberBg} color={ck_amber}>Normal</CKPill>
          </div>
        </div>
        <div style={{ padding: '14px 16px' }}>
          <div style={{ fontSize: 11.5, fontWeight: 700, color: v2_ink4, textTransform: 'uppercase', letterSpacing: 0.8, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <CKIcon d={CI.box} size={12} stroke={v2_ink4}/> Materials
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {['Rotor nozzles (×4)', 'Pressure regulator', 'Backflow kit', 'Thread tape'].map((m) => (
              <span key={m} style={{
                padding: '8px 12px', borderRadius: 10, background: v2_soft,
                fontSize: 13.5, fontWeight: 700, color: v2_ink, border: `1.5px solid ${v2_line}`,
                letterSpacing: -0.1,
              }}>{m}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Tech assignment */}
      <div style={{ margin: '0 20px 16px', borderRadius: 14, border: `1.5px solid ${v2_line}`, background: '#fff' }}>
        <CKRow icon={CI.user} label="Assigned tech" value="Viktor K. · Route #3"
          right={<CKLinkBtn>Reassign</CKLinkBtn>}/>
      </div>

      {/* Footer */}
      <div style={{
        padding: '14px 20px 18px', background: v2_soft,
        borderTop: `1px solid ${v2_line}`,
        display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
      }}>
        <CKLinkBtn icon={CI.pencil}>Edit</CKLinkBtn>
        <CKLinkBtn icon={CI.alert}>No show</CKLinkBtn>
        <CKLinkBtn icon={CI.x} color={ck_red} border={'#FCA5A5'}>Cancel</CKLinkBtn>
      </div>
    </div>
  );
}

Object.assign(window, { CombinedModalV2, V2AttachedPhotos, V2AttachedNotes, V2InternalNotes, V2LinkBtn });
