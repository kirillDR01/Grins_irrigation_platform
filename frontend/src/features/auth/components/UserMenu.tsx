/**
 * UserMenu component - displays user name with dropdown for settings and logout.
 *
 * Requirements: 19.8
 */

import { useNavigate } from 'react-router-dom';
import { Settings, LogOut, ChevronDown } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuth } from './AuthProvider';

export function UserMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) {
    return null;
  }

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleSettings = () => {
    navigate('/settings');
  };

  // Get initials for avatar
  const initials = user.name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          className="flex items-center gap-2 hover:bg-slate-100 rounded-lg p-1 transition-colors"
          data-testid="user-menu"
        >
          {/* User avatar - teal-100 bg with teal-700 text, font-bold text-xs */}
          <div className="w-8 h-8 rounded-full bg-teal-100 text-teal-700 font-bold text-xs flex items-center justify-center">
            {initials}
          </div>
          <span className="text-sm text-slate-700 hidden sm:inline">{user.name}</span>
          <ChevronDown className="h-4 w-4 text-slate-400" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent 
        align="end" 
        className="w-56 bg-white rounded-lg shadow-lg border border-slate-100" 
        data-testid="user-menu-dropdown"
      >
        <DropdownMenuLabel className="font-normal px-3 py-2">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium text-slate-700 leading-none" data-testid="user-menu-name">
              {user.name}
            </p>
            <p className="text-xs leading-none text-slate-400" data-testid="user-menu-email">
              {user.email || user.username}
            </p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator className="bg-slate-100" />
        <DropdownMenuItem 
          onClick={handleSettings} 
          className="px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 cursor-pointer"
          data-testid="settings-btn"
        >
          <Settings className="mr-2 h-4 w-4" />
          <span>Settings</span>
        </DropdownMenuItem>
        <DropdownMenuSeparator className="bg-slate-100" />
        <DropdownMenuItem
          onClick={handleLogout}
          className="px-3 py-2 text-sm text-red-600 hover:bg-red-50 cursor-pointer"
          data-testid="logout-btn"
        >
          <LogOut className="mr-2 h-4 w-4" />
          <span>Log out</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
