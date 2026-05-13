import { useEffect, useRef, useState } from 'react';
import { Input } from '@/components/ui/input';
import { cn } from '@/shared/utils/cn';

export type AddressSelection = {
  street: string;
  city: string;
  state: string;
  zipCode: string;
};

type Props = {
  value: string;
  onChange: (v: string) => void;
  onAddressSelected?: (parts: AddressSelection) => void;
  placeholder?: string;
  'data-testid'?: string;
  className?: string;
  id?: string;
  disabled?: boolean;
  name?: string;
};

type MapboxContext = {
  id: string;
  text?: string;
  short_code?: string;
};

type MapboxFeature = {
  id: string;
  place_name: string;
  text?: string;
  address?: string;
  context?: MapboxContext[];
};

const MAPBOX_ENDPOINT = 'https://api.mapbox.com/geocoding/v5/mapbox.places';
const PROXIMITY = '-93.265,44.977';
const DEBOUNCE_MS = 250;
const MIN_QUERY_LEN = 3;

let warnedNoToken = false;

function parseFeature(feature: MapboxFeature): AddressSelection {
  const ctx = feature.context ?? [];
  const find = (prefix: string) =>
    ctx.find((c) => typeof c.id === 'string' && c.id.startsWith(prefix));

  const place = find('place');
  const region = find('region');
  const postcode = find('postcode');

  const stateRaw = region?.short_code ?? region?.text ?? '';
  const stateAbbr = stateRaw.startsWith('US-')
    ? stateRaw.slice(3)
    : stateRaw;

  const street = feature.address
    ? `${feature.address} ${feature.text ?? ''}`.trim()
    : feature.text ?? '';

  return {
    street,
    city: place?.text ?? '',
    state: stateAbbr,
    zipCode: postcode?.text ?? '',
  };
}

export function AddressAutocomplete({
  value,
  onChange,
  onAddressSelected,
  placeholder,
  className,
  id,
  disabled,
  name,
  'data-testid': testId,
}: Props) {
  const token = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN as string | undefined;
  const hasToken = !!token && token.length > 0;

  const [open, setOpen] = useState(false);
  const [suggestions, setSuggestions] = useState<MapboxFeature[]>([]);
  const [highlight, setHighlight] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const blurTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!hasToken) {
      if (!warnedNoToken) {
        warnedNoToken = true;
        // eslint-disable-next-line no-console
        console.warn(
          'AddressAutocomplete: VITE_MAPBOX_ACCESS_TOKEN not set — falling back to plain input.',
        );
      }
      return;
    }

    const q = value.trim();
    if (q.length < MIN_QUERY_LEN) {
      setSuggestions([]);
      setOpen(false);
      return;
    }

    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const url =
          `${MAPBOX_ENDPOINT}/${encodeURIComponent(q)}.json` +
          `?access_token=${token}` +
          `&country=US&types=address&autocomplete=true&limit=5&proximity=${PROXIMITY}`;
        const res = await fetch(url);
        if (!res.ok) return;
        const data = (await res.json()) as { features?: MapboxFeature[] };
        if (cancelled) return;
        const features = data.features ?? [];
        setSuggestions(features);
        setOpen(features.length > 0);
        setHighlight(-1);
      } catch {
        // Swallow network errors; degrade to plain input.
      }
    }, DEBOUNCE_MS);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [value, hasToken, token]);

  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  useEffect(() => {
    return () => {
      if (blurTimer.current) clearTimeout(blurTimer.current);
    };
  }, []);

  const handleSelect = (feature: MapboxFeature) => {
    onChange(feature.place_name);
    if (onAddressSelected) {
      onAddressSelected(parseFeature(feature));
    }
    setOpen(false);
    setSuggestions([]);
    setHighlight(-1);
  };

  if (!hasToken) {
    return (
      <Input
        id={id}
        name={name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className={className}
        data-testid={testId}
      />
    );
  }

  const suggestionsTestId = testId ? `${testId}-suggestions` : undefined;

  return (
    <div ref={containerRef} className="relative">
      <Input
        id={id}
        name={name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className={className}
        data-testid={testId}
        autoComplete="off"
        onFocus={() => {
          if (suggestions.length > 0) setOpen(true);
        }}
        onBlur={() => {
          blurTimer.current = setTimeout(() => setOpen(false), 100);
        }}
        onKeyDown={(e) => {
          if (!open || suggestions.length === 0) return;
          if (e.key === 'ArrowDown') {
            e.preventDefault();
            setHighlight((h) => Math.min(h + 1, suggestions.length - 1));
          } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setHighlight((h) => Math.max(h - 1, 0));
          } else if (e.key === 'Enter') {
            if (highlight >= 0 && suggestions[highlight]) {
              e.preventDefault();
              handleSelect(suggestions[highlight]);
            }
          } else if (e.key === 'Escape') {
            e.preventDefault();
            setOpen(false);
          }
        }}
      />
      {open && suggestions.length > 0 && (
        <ul
          data-testid={suggestionsTestId}
          className={cn(
            'absolute z-50 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg',
          )}
          role="listbox"
        >
          {suggestions.map((f, idx) => (
            <li key={f.id} role="option" aria-selected={idx === highlight}>
              <button
                type="button"
                className={cn(
                  'block w-full cursor-pointer px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50',
                  idx === highlight && 'bg-slate-100',
                )}
                onMouseDown={(e) => {
                  e.preventDefault();
                  handleSelect(f);
                }}
              >
                {f.place_name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
