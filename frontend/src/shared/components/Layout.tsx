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
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

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
          'fixed inset-y-0 left-0 z-50 w-64 bg-card border-r transform transition-transform duration-200 ease-in-out lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        data-testid="sidebar"
      >
        {/* Logo */}
        <div className="flex items-center gap-2 px-6 py-4">
          <Droplets className="h-8 w-8 text-primary" />
          <span className="text-xl font-bold">Grin's Irrigation</span>
        </div>

        <Separator />

        {/* Navigation */}
        <nav className="flex flex-col gap-1 p-4" data-testid="sidebar-nav">
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
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
                onClick={() => setSidebarOpen(false)}
              >
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
          className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b bg-background px-4 lg:px-6"
          data-testid="header"
        >
          {/* Mobile menu button */}
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
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

          {/* Page title - could be dynamic based on route */}
          <div className="flex-1">
            <h1 className="text-lg font-semibold lg:hidden">
              Grin's Irrigation
            </h1>
          </div>

          {/* User info placeholder */}
          <div className="flex items-center gap-2" data-testid="user-info">
            <span className="text-sm text-muted-foreground">Viktor</span>
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
              <span className="text-sm font-medium">VG</span>
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
