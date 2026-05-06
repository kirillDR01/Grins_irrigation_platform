/**
 * Tests for PhotosPanel — inline expansion panel for customer photos.
 * Validates: Requirements 4.1–4.12, 9.1–9.6, 13.2
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PhotosPanel } from './PhotosPanel';

// ── Mock customer hooks ──────────────────────────────────────────────────────

const mockPhotos = [
  {
    id: 'photo-1',
    download_url: 'https://example.com/photo1.jpg',
    file_name: 'photo1.jpg',
    caption: 'Front yard',
    created_at: '2025-06-10T10:00:00Z',
  },
  {
    id: 'photo-2',
    download_url: 'https://example.com/photo2.jpg',
    file_name: 'photo2.jpg',
    caption: 'Back yard',
    created_at: '2025-06-11T14:30:00Z',
  },
];

const mockMutateAsync = vi.fn().mockResolvedValue({});

vi.mock('@/features/customers', () => ({
  useCustomerPhotos: vi.fn(() => ({
    data: mockPhotos,
    isLoading: false,
    error: null,
  })),
  useUploadCustomerPhotos: vi.fn(() => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  })),
}));

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

// ── Helpers ──────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

function renderPhotosPanel() {
  return render(
    <PhotosPanel customerId="cust-001" appointmentId="appt-001" />,
    { wrapper: createWrapper() },
  );
}

// ── Header rendering ─────────────────────────────────────────────────────────

describe('PhotosPanel — Header rendering', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders "Attached photos" label', () => {
    renderPhotosPanel();
    expect(screen.getByText('Attached photos')).toBeInTheDocument();
  });

  it('renders count chip with photo count', () => {
    renderPhotosPanel();
    // Count chip shows total photos (2 real + 0 optimistic)
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('renders "From customer file" label', () => {
    renderPhotosPanel();
    expect(screen.getByText('From customer file')).toBeInTheDocument();
  });

  it('renders the panel with data-testid', () => {
    renderPhotosPanel();
    expect(screen.getByTestId('photos-panel')).toBeInTheDocument();
  });
});

// ── Upload CTA buttons ──────────────────────────────────────────────────────

describe('PhotosPanel — Upload CTA buttons', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders "Upload photo" button with correct label', () => {
    renderPhotosPanel();
    expect(screen.getByText('Upload photo')).toBeInTheDocument();
    expect(screen.getByText('· camera roll')).toBeInTheDocument();
  });

  it('renders "Take photo" button', () => {
    renderPhotosPanel();
    expect(screen.getByText('Take photo')).toBeInTheDocument();
  });

  it('has hidden file input with accept="image/*" and multiple for upload', () => {
    renderPhotosPanel();
    const uploadInput = screen.getByTestId('upload-photo-input');
    expect(uploadInput).toHaveAttribute('type', 'file');
    expect(uploadInput).toHaveAttribute('accept', 'image/*');
    expect(uploadInput).toHaveAttribute('multiple');
  });

  it('has hidden file input with capture="environment" for camera', () => {
    renderPhotosPanel();
    const cameraInput = screen.getByTestId('take-photo-input');
    expect(cameraInput).toHaveAttribute('type', 'file');
    expect(cameraInput).toHaveAttribute('accept', 'image/*');
    expect(cameraInput).toHaveAttribute('capture', 'environment');
  });
});

// ── Photo strip renders PhotoCard components ─────────────────────────────────

describe('PhotosPanel — Photo strip', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders photo cards for each photo', () => {
    renderPhotosPanel();
    const strip = screen.getByTestId('photo-strip');

    // Each photo card renders an img with the photo's alt text
    expect(within(strip).getByAltText('Front yard')).toBeInTheDocument();
    expect(within(strip).getByAltText('Back yard')).toBeInTheDocument();
  });

  it('renders photo captions', () => {
    renderPhotosPanel();
    expect(screen.getByText('Front yard')).toBeInTheDocument();
    expect(screen.getByText('Back yard')).toBeInTheDocument();
  });
});

// ── "Add more · From library" trailing tile ──────────────────────────────────

describe('PhotosPanel — Add more tile', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders "Add more" trailing tile', () => {
    renderPhotosPanel();
    expect(screen.getByText('Add more')).toBeInTheDocument();
    expect(screen.getByText('From library')).toBeInTheDocument();
  });

  it('has accessible label for add more tile', () => {
    renderPhotosPanel();
    expect(screen.getByLabelText('Add more photos from library')).toBeInTheDocument();
  });

  it('has hidden file input for add more', () => {
    renderPhotosPanel();
    const addMoreInput = screen.getByTestId('add-more-photo-input');
    expect(addMoreInput).toHaveAttribute('type', 'file');
    expect(addMoreInput).toHaveAttribute('accept', 'image/*');
    expect(addMoreInput).toHaveAttribute('multiple');
  });
});

// ── Footer ───────────────────────────────────────────────────────────────────

describe('PhotosPanel — Footer', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders hint text', () => {
    renderPhotosPanel();
    expect(screen.getByText('Tap a photo to expand · pinch to zoom')).toBeInTheDocument();
  });

  it('renders "View all (N)" button with correct count', () => {
    renderPhotosPanel();
    expect(screen.getByText('View all (2)')).toBeInTheDocument();
  });
});

// ── File input triggers on button click ──────────────────────────────────────

describe('PhotosPanel — File input triggers', () => {
  beforeEach(() => vi.clearAllMocks());

  it('triggers upload file input when "Upload photo" button is clicked', async () => {
    const user = userEvent.setup();
    renderPhotosPanel();

    const uploadInput = screen.getByTestId('upload-photo-input') as HTMLInputElement;
    const clickSpy = vi.spyOn(uploadInput, 'click');

    const uploadBtn = screen.getByLabelText('Upload photo from camera roll');
    await user.click(uploadBtn);

    expect(clickSpy).toHaveBeenCalled();
  });

  it('triggers camera file input when "Take photo" button is clicked', async () => {
    const user = userEvent.setup();
    renderPhotosPanel();

    const cameraInput = screen.getByTestId('take-photo-input') as HTMLInputElement;
    const clickSpy = vi.spyOn(cameraInput, 'click');

    const cameraBtn = screen.getByLabelText('Take photo with camera');
    await user.click(cameraBtn);

    expect(clickSpy).toHaveBeenCalled();
  });
});

// ── Upload validation and error handling ────────────────────────────────────

describe('PhotosPanel — upload validation and error handling', () => {
  beforeEach(() => vi.clearAllMocks());

  it('rejects unsupported MIME types before calling the upload mutation', async () => {
    const { toast } = await import('sonner');
    renderPhotosPanel();
    const input = screen.getByTestId('upload-photo-input') as HTMLInputElement;
    const gif = new File(['x'], 'evil.gif', { type: 'image/gif' });
    await userEvent.upload(input, gif);
    expect(toast.error).toHaveBeenCalledWith(
      expect.stringContaining('evil.gif'),
    );
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it('rejects files larger than 10 MB before calling the upload mutation', async () => {
    const { toast } = await import('sonner');
    renderPhotosPanel();
    const input = screen.getByTestId('upload-photo-input') as HTMLInputElement;
    const big = new File([new Uint8Array(11 * 1024 * 1024)], 'huge.jpg', {
      type: 'image/jpeg',
    });
    await userEvent.upload(input, big);
    expect(toast.error).toHaveBeenCalledWith(
      expect.stringContaining('huge.jpg'),
    );
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it('emits "File too large" toast on 413 response from the upload mutation', async () => {
    const { toast } = await import('sonner');
    const err = Object.assign(new Error('413'), {
      isAxiosError: true,
      response: { status: 413, data: { detail: 'too big' } },
    });
    mockMutateAsync.mockRejectedValueOnce(err);
    renderPhotosPanel();
    const input = screen.getByTestId('upload-photo-input') as HTMLInputElement;
    const ok = new File(['x'], 'ok.jpg', { type: 'image/jpeg' });
    await userEvent.upload(input, ok);
    expect(toast.error).toHaveBeenCalledWith(
      'File too large',
      expect.objectContaining({ description: expect.stringContaining('10 MB') }),
    );
  });

  it('emits "Unsupported file type" toast on 415 response from the upload mutation', async () => {
    const { toast } = await import('sonner');
    const err = Object.assign(new Error('415'), {
      isAxiosError: true,
      response: { status: 415, data: { detail: 'bad mime' } },
    });
    mockMutateAsync.mockRejectedValueOnce(err);
    renderPhotosPanel();
    const input = screen.getByTestId('upload-photo-input') as HTMLInputElement;
    const ok = new File(['x'], 'ok.jpg', { type: 'image/jpeg' });
    await userEvent.upload(input, ok);
    expect(toast.error).toHaveBeenCalledWith(
      'Unsupported file type',
      expect.any(Object),
    );
  });
});
