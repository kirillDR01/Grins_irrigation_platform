import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { Layout } from './Layout';

// Mock the UserMenu component to avoid AuthProvider dependency
vi.mock('@/features/auth', () => ({
  UserMenu: () => (
    <div data-testid="user-info">
      <span>Viktor</span>
      <span>VG</span>
    </div>
  ),
}));

// Wrapper component for tests
const renderWithRouter = (ui: React.ReactElement, { route = '/' } = {}) => {
  return render(
    <MemoryRouter initialEntries={[route]}>
      {ui}
    </MemoryRouter>
  );
};

describe('Layout', () => {
  describe('rendering', () => {
    it('should render the layout container', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      expect(screen.getByTestId('layout')).toBeInTheDocument();
    });

    it('should render children content', () => {
      renderWithRouter(<Layout><div data-testid="child">Test Content</div></Layout>);
      
      expect(screen.getByTestId('child')).toBeInTheDocument();
      expect(screen.getByText('Test Content')).toBeInTheDocument();
    });

    it('should render the sidebar', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      expect(screen.getByTestId('sidebar')).toBeInTheDocument();
    });

    it('should render the header', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      expect(screen.getByTestId('header')).toBeInTheDocument();
    });

    it('should render the main content area', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      expect(screen.getByTestId('main-content')).toBeInTheDocument();
    });

    it('should render the logo text', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      // There are two instances: sidebar logo and mobile header
      const logoTexts = screen.getAllByText("Grin's Irrigation");
      expect(logoTexts.length).toBeGreaterThanOrEqual(1);
    });

    it('should render user info', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      expect(screen.getByTestId('user-info')).toBeInTheDocument();
      expect(screen.getByText('Viktor')).toBeInTheDocument();
      // There are two instances of 'VG': one in user menu and one in sidebar profile card
      const vgTexts = screen.getAllByText('VG');
      expect(vgTexts.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('navigation', () => {
    it('should render all navigation items', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      expect(screen.getByTestId('nav-dashboard')).toBeInTheDocument();
      expect(screen.getByTestId('nav-customers')).toBeInTheDocument();
      expect(screen.getByTestId('nav-jobs')).toBeInTheDocument();
      expect(screen.getByTestId('nav-schedule')).toBeInTheDocument();
      expect(screen.getByTestId('nav-staff')).toBeInTheDocument();
      expect(screen.getByTestId('nav-settings')).toBeInTheDocument();
    });

    it('should render navigation labels', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Customers')).toBeInTheDocument();
      expect(screen.getByText('Jobs')).toBeInTheDocument();
      expect(screen.getByText('Schedule')).toBeInTheDocument();
      expect(screen.getByText('Staff')).toBeInTheDocument();
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });

    it('should have correct href for navigation links', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      expect(screen.getByTestId('nav-dashboard')).toHaveAttribute('href', '/dashboard');
      expect(screen.getByTestId('nav-customers')).toHaveAttribute('href', '/customers');
      expect(screen.getByTestId('nav-jobs')).toHaveAttribute('href', '/jobs');
      expect(screen.getByTestId('nav-schedule')).toHaveAttribute('href', '/schedule');
      expect(screen.getByTestId('nav-staff')).toHaveAttribute('href', '/staff');
      expect(screen.getByTestId('nav-settings')).toHaveAttribute('href', '/settings');
    });

    it('should highlight active navigation item based on route', () => {
      renderWithRouter(<Layout>Content</Layout>, { route: '/customers' });
      
      const customersLink = screen.getByTestId('nav-customers');
      expect(customersLink).toHaveClass('bg-teal-50');
      expect(customersLink).toHaveClass('text-teal-600');
    });

    it('should highlight dashboard when on dashboard route', () => {
      renderWithRouter(<Layout>Content</Layout>, { route: '/dashboard' });
      
      const dashboardLink = screen.getByTestId('nav-dashboard');
      expect(dashboardLink).toHaveClass('bg-teal-50');
      expect(dashboardLink).toHaveClass('text-teal-600');
    });

    it('should highlight jobs when on jobs route', () => {
      renderWithRouter(<Layout>Content</Layout>, { route: '/jobs' });
      
      const jobsLink = screen.getByTestId('nav-jobs');
      expect(jobsLink).toHaveClass('bg-teal-50');
      expect(jobsLink).toHaveClass('text-teal-600');
    });

    it('should highlight schedule when on schedule route', () => {
      renderWithRouter(<Layout>Content</Layout>, { route: '/schedule' });
      
      const scheduleLink = screen.getByTestId('nav-schedule');
      expect(scheduleLink).toHaveClass('bg-teal-50');
      expect(scheduleLink).toHaveClass('text-teal-600');
    });

    it('should highlight staff when on staff route', () => {
      renderWithRouter(<Layout>Content</Layout>, { route: '/staff' });
      
      const staffLink = screen.getByTestId('nav-staff');
      expect(staffLink).toHaveClass('bg-teal-50');
      expect(staffLink).toHaveClass('text-teal-600');
    });

    it('should highlight settings when on settings route', () => {
      renderWithRouter(<Layout>Content</Layout>, { route: '/settings' });
      
      const settingsLink = screen.getByTestId('nav-settings');
      expect(settingsLink).toHaveClass('bg-teal-50');
      expect(settingsLink).toHaveClass('text-teal-600');
    });
  });

  describe('mobile menu', () => {
    it('should render mobile menu button', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      expect(screen.getByTestId('mobile-menu-button')).toBeInTheDocument();
    });

    it('should have correct aria-label when menu is closed', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      const button = screen.getByTestId('mobile-menu-button');
      expect(button).toHaveAttribute('aria-label', 'Open menu');
    });

    it('should toggle sidebar visibility when mobile menu button is clicked', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      const sidebar = screen.getByTestId('sidebar');
      const button = screen.getByTestId('mobile-menu-button');
      
      // Initially sidebar should be hidden on mobile (has -translate-x-full)
      expect(sidebar).toHaveClass('-translate-x-full');
      
      // Click to open
      fireEvent.click(button);
      expect(sidebar).toHaveClass('translate-x-0');
      expect(button).toHaveAttribute('aria-label', 'Close menu');
      
      // Click to close
      fireEvent.click(button);
      expect(sidebar).toHaveClass('-translate-x-full');
      expect(button).toHaveAttribute('aria-label', 'Open menu');
    });

    it('should show backdrop when sidebar is open', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      const button = screen.getByTestId('mobile-menu-button');
      
      // Initially no backdrop
      expect(screen.queryByTestId('sidebar-backdrop')).not.toBeInTheDocument();
      
      // Click to open
      fireEvent.click(button);
      expect(screen.getByTestId('sidebar-backdrop')).toBeInTheDocument();
    });

    it('should close sidebar when backdrop is clicked', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      const button = screen.getByTestId('mobile-menu-button');
      
      // Open sidebar
      fireEvent.click(button);
      expect(screen.getByTestId('sidebar-backdrop')).toBeInTheDocument();
      
      // Click backdrop
      fireEvent.click(screen.getByTestId('sidebar-backdrop'));
      
      // Sidebar should be closed
      expect(screen.queryByTestId('sidebar-backdrop')).not.toBeInTheDocument();
      const sidebar = screen.getByTestId('sidebar');
      expect(sidebar).toHaveClass('-translate-x-full');
    });

    it('should close sidebar when navigation link is clicked', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      const button = screen.getByTestId('mobile-menu-button');
      
      // Open sidebar
      fireEvent.click(button);
      expect(screen.getByTestId('sidebar')).toHaveClass('translate-x-0');
      
      // Click a nav link
      fireEvent.click(screen.getByTestId('nav-customers'));
      
      // Sidebar should be closed
      expect(screen.getByTestId('sidebar')).toHaveClass('-translate-x-full');
    });
  });

  describe('sidebar navigation', () => {
    it('should render sidebar-nav container', () => {
      renderWithRouter(<Layout>Content</Layout>);
      
      expect(screen.getByTestId('sidebar-nav')).toBeInTheDocument();
    });
  });
});
