import { ReactNode, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Users,
  Briefcase,
  Calendar,
  UserCog,
  Settings,
  Menu,
  X,
  Droplets,
  Zap,
  FileText,
  Bell,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { UserMenu } from '@/features/auth';
import { GlobalSearch } from './GlobalSearch';

interface LayoutProps {
  children: ReactNode;
}

interface NavItem {
  label: string;
  href: string;
  icon: ReactNode;
  testId: string;
}

const navItems: NavItem[] = [
  {
    label: 'Dashboard',
    href: '/dashboard',
    icon: <LayoutDashboard className="h-5 w-5" />,
    testId: 'nav-dashboard',
  },
  {
    label: 'Customers',
    href: '/customers',
    icon: <Users className="h-5 w-5" />,
    testId: 'nav-customers',
  },
  {
    label: 'Jobs',
    href: '/jobs',
    icon: <Briefcase className="h-5 w-5" />,
    testId: 'nav-jobs',
  },
  {
    label: 'Schedule',
    href: '/schedule',
    icon: <Calendar className="h-5 w-5" />,
    testId: 'nav-schedule',
  },
  {
    label: 'Generate Routes',
    href: '/schedule/generate',
    icon: <Zap className="h-5 w-5" />,
    testId: 'nav-generate',
  },
  {
    label: 'Staff',
    href: '/staff',
    icon: <UserCog className="h-5 w-5" />,
    testId: 'nav-staff',
  },
  {
    label: 'Invoices',
    href: '/invoices',
    icon: <FileText className="h-5 w-5" />,
    testId: 'nav-invoices',
  },
  {
    label: 'Settings',
    href: '/settings',
    icon: <Settings className="h-5 w-5" />,
    testId: 'nav-settings',
  },
];

export function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background" data-testid="layout">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          data-testid="sidebar-backdrop"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 flex flex-col h-screen bg-white border-r border-slate-100 transform transition-transform duration-200 ease-in-out lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        data-testid="sidebar"
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5">
          <div className="w-8 h-8 bg-teal-500 rounded-lg shadow-lg shadow-teal-500/30 flex items-center justify-center">
            <Droplets className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight text-slate-900">Grin's Irrigation</span>
        </div>

        <Separator />

        {/* Navigation */}
        <nav className="flex flex-col gap-1 py-4 flex-1" data-testid="sidebar-nav">
          {navItems.map((item) => {
            // Check for exact match first, then check if it's a parent route
            // but only if no other nav item is a more specific match
            const isExactMatch = location.pathname === item.href;
            const isParentRoute = location.pathname.startsWith(item.href + '/');
            // For routes like /schedule, only highlight if we're exactly on /schedule
            // not on /schedule/generate (which has its own nav item)
            const hasMoreSpecificNavItem = navItems.some(
              (other) =>
                other.href !== item.href &&
                other.href.startsWith(item.href + '/') &&
                location.pathname.startsWith(other.href)
            );
            const isActive = isExactMatch || (isParentRoute && !hasMoreSpecificNavItem);
            return (
              <Link
                key={item.href}
                to={item.href}
                data-testid={item.testId}
                className={cn(
                  'relative flex items-center gap-3 px-6 py-4 text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'bg-teal-50 text-teal-600'
                    : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'
                )}
                onClick={() => setSidebarOpen(false)}
              >
                {isActive && (
                  <div className="absolute left-0 w-1 h-8 bg-teal-500 rounded-r-full" />
                )}
                {item.icon}
                {item.label}
              </Link>
            );
          })}
        </nav>

      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Header */}
        <header
          className="sticky top-0 z-10 flex h-16 items-center gap-4 border-b border-slate-100 bg-white/80 backdrop-blur-md px-4 lg:px-6"
          data-testid="header"
        >
          {/* Mobile menu button */}
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden transition-all duration-200"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            data-testid="mobile-menu-button"
            aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
          >
            {sidebarOpen ? (
              <X className="h-6 w-6" />
            ) : (
              <Menu className="h-6 w-6" />
            )}
          </Button>

          {/* Page title - mobile only */}
          <h1 className="text-lg font-semibold lg:hidden">
            Grin's Irrigation
          </h1>

          {/* Global search input */}
          <div className="hidden lg:flex flex-1 max-w-md">
            <GlobalSearch />
          </div>

          {/* Spacer to push actions to far right */}
          <div className="flex-1" />

          {/* Right side actions */}
          <div className="flex items-center gap-2">
            {/* Notification bell with badge */}
            <button
              className="relative p-2 rounded-lg hover:bg-slate-100 transition-colors"
              data-testid="notification-bell"
              aria-label="Notifications"
            >
              <Bell className="h-5 w-5 text-slate-600" />
              <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-rose-500 border-2 border-white flex items-center justify-center">
                <span className="text-[10px] font-medium text-white">3</span>
              </span>
            </button>

            {/* Vertical separator */}
            <div className="h-8 w-px bg-slate-200" data-testid="header-separator" />

            {/* User menu (hidden on mobile, shown on larger screens) */}
            <div className="hidden sm:block">
              <UserMenu />
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 lg:p-6" data-testid="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
