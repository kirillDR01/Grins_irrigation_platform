import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { AddressAutocomplete } from './AddressAutocomplete';

type FetchMock = ReturnType<typeof vi.fn>;

function mockMapboxResponse(features: unknown[]) {
  return {
    ok: true,
    status: 200,
    json: async () => ({ features }),
  } as Response;
}

const SAMPLE_FEATURE = {
  id: 'address.1',
  place_name: '1600 Pennsylvania Ave NW, Washington, DC 20500, United States',
  text: 'Pennsylvania Ave NW',
  address: '1600',
  context: [
    { id: 'place.123', text: 'Washington' },
    { id: 'region.456', text: 'District of Columbia', short_code: 'US-DC' },
    { id: 'postcode.789', text: '20500' },
  ],
};

describe('AddressAutocomplete', () => {
  let fetchMock: FetchMock;

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue(mockMapboxResponse([SAMPLE_FEATURE]));
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
    vi.useRealTimers();
  });

  it('renders as a plain Input when token is missing', () => {
    vi.stubEnv('VITE_MAPBOX_ACCESS_TOKEN', '');
    const onChange = vi.fn();
    render(
      <AddressAutocomplete
        value=""
        onChange={onChange}
        placeholder="Street"
        data-testid="addr"
      />,
    );
    const input = screen.getByTestId('addr');
    fireEvent.change(input, { target: { value: 'Main' } });
    expect(onChange).toHaveBeenCalledWith('Main');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('debounces typing — only one fetch within 250ms', async () => {
    vi.stubEnv('VITE_MAPBOX_ACCESS_TOKEN', 'pk.test');
    vi.useFakeTimers();
    const onChange = vi.fn();

    const { rerender } = render(
      <AddressAutocomplete
        value="Main"
        onChange={onChange}
        data-testid="addr"
      />,
    );
    rerender(
      <AddressAutocomplete
        value="Main S"
        onChange={onChange}
        data-testid="addr"
      />,
    );

    expect(fetchMock).not.toHaveBeenCalled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(260);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('does not fire fetch when query under 3 chars', async () => {
    vi.stubEnv('VITE_MAPBOX_ACCESS_TOKEN', 'pk.test');
    vi.useFakeTimers();
    render(
      <AddressAutocomplete value="Ma" onChange={vi.fn()} data-testid="addr" />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('renders suggestions dropdown after fetch returns features', async () => {
    vi.stubEnv('VITE_MAPBOX_ACCESS_TOKEN', 'pk.test');
    vi.useFakeTimers();
    render(
      <AddressAutocomplete
        value="1600 Penn"
        onChange={vi.fn()}
        data-testid="addr"
      />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    expect(screen.getByTestId('addr-suggestions')).toBeInTheDocument();
    expect(
      screen.getByText(/1600 Pennsylvania Ave NW/),
    ).toBeInTheDocument();
  });

  it('selecting a suggestion fires onChange and onAddressSelected', async () => {
    vi.stubEnv('VITE_MAPBOX_ACCESS_TOKEN', 'pk.test');
    vi.useFakeTimers();
    const onChange = vi.fn();
    const onAddressSelected = vi.fn();
    render(
      <AddressAutocomplete
        value="1600 Penn"
        onChange={onChange}
        onAddressSelected={onAddressSelected}
        data-testid="addr"
      />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    const option = screen.getByText(/1600 Pennsylvania Ave NW/);
    fireEvent.mouseDown(option);

    expect(onChange).toHaveBeenCalledWith(SAMPLE_FEATURE.place_name);
    expect(onAddressSelected).toHaveBeenCalledWith({
      street: '1600 Pennsylvania Ave NW',
      city: 'Washington',
      state: 'DC',
      zipCode: '20500',
    });
  });

  it('Escape closes the dropdown without firing onChange', async () => {
    vi.stubEnv('VITE_MAPBOX_ACCESS_TOKEN', 'pk.test');
    vi.useFakeTimers();
    const onChange = vi.fn();
    render(
      <AddressAutocomplete
        value="1600 Penn"
        onChange={onChange}
        data-testid="addr"
      />,
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    expect(screen.getByTestId('addr-suggestions')).toBeInTheDocument();

    fireEvent.keyDown(screen.getByTestId('addr'), { key: 'Escape' });
    expect(screen.queryByTestId('addr-suggestions')).not.toBeInTheDocument();
    // onChange was called once by the initial render's controlled state — but
    // not by the Escape itself; verify no NEW calls beyond what the test setup
    // already exercised (which is zero, since we never typed).
    expect(onChange).not.toHaveBeenCalled();
  });
});
