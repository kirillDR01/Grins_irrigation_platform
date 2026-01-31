import { useState, useEffect, useCallback, useRef } from 'react';
import { Check, ChevronsUpDown, Loader2, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { cn } from '@/lib/utils';
import { customerApi } from '@/features/customers/api/customerApi';
import type { Customer } from '@/features/customers/types';

interface SearchableCustomerDropdownProps {
  value?: string;
  onChange: (customerId: string) => void;
  disabled?: boolean;
}

export function SearchableCustomerDropdown({
  value,
  onChange,
  disabled = false,
}: SearchableCustomerDropdownProps) {
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const debounceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch selected customer details when value changes
  useEffect(() => {
    if (value && !selectedCustomer) {
      customerApi.get(value).then(setSelectedCustomer).catch(console.error);
    }
  }, [value, selectedCustomer]);

  // Debounced search function
  const searchCustomers = useCallback(async (query: string) => {
    if (!query.trim()) {
      setCustomers([]);
      return;
    }

    setIsLoading(true);
    try {
      const response = await customerApi.search(query);
      setCustomers(response.items);
    } catch (error) {
      console.error('Failed to search customers:', error);
      setCustomers([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle search input change with debouncing
  const handleSearchChange = (query: string) => {
    setSearchQuery(query);

    // Clear existing timeout
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }

    // Set new timeout for debounced search
    debounceTimeoutRef.current = setTimeout(() => {
      searchCustomers(query);
    }, 300);
  };

  // Handle customer selection
  const handleSelect = (customer: Customer) => {
    setSelectedCustomer(customer);
    onChange(customer.id);
    setOpen(false);
    setSearchQuery('');
    setCustomers([]);
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, []);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between border-slate-200 rounded-lg bg-white text-slate-700 text-sm hover:bg-slate-50 focus:ring-2 focus:ring-teal-100 focus:border-teal-500"
          disabled={disabled}
          data-testid="customer-dropdown"
        >
          {selectedCustomer ? (
            <span className="truncate font-medium text-slate-700">
              {selectedCustomer.first_name} {selectedCustomer.last_name} - {selectedCustomer.phone}
            </span>
          ) : (
            <span className="text-slate-400">Select customer...</span>
          )}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 text-slate-400" />
        </Button>
      </PopoverTrigger>
      <PopoverContent 
        className="w-[400px] p-0 bg-white rounded-lg shadow-lg border border-slate-100" 
        align="start"
        data-testid="customer-dropdown-content"
      >
        <div className="flex items-center gap-2 border-b border-slate-100 px-3 py-2">
          <Search className="h-4 w-4 text-slate-400" />
          <input
            placeholder="Search by name, phone, or email..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="flex-1 bg-transparent border-0 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-teal-100 rounded"
            data-testid="customer-search-input"
            autoFocus
          />
          {isLoading && <Loader2 className="h-4 w-4 animate-spin text-teal-500" />}
        </div>
        <div className="max-h-60 overflow-y-auto">
          {customers.length === 0 && searchQuery && !isLoading && (
            <div className="py-6 text-center text-sm text-slate-400 italic">
              No customers found
            </div>
          )}
          {customers.length === 0 && !searchQuery && (
            <div className="py-6 text-center text-sm text-slate-400">
              Start typing to search customers
            </div>
          )}
          {customers.map((customer) => (
            <button
              key={customer.id}
              onClick={() => handleSelect(customer)}
              className={cn(
                'relative flex w-full cursor-pointer select-none items-center gap-2 px-3 py-2 text-sm outline-none transition-colors',
                value === customer.id 
                  ? 'bg-teal-50 text-teal-700' 
                  : 'hover:bg-slate-50 text-slate-700'
              )}
              data-testid={`customer-option-${customer.id}`}
            >
              <Check
                className={cn(
                  'h-4 w-4 text-teal-600',
                  value === customer.id ? 'opacity-100' : 'opacity-0'
                )}
              />
              <div className="flex flex-col items-start">
                <span className="font-medium text-slate-700">
                  {customer.first_name} {customer.last_name}
                </span>
                <span className="text-xs text-slate-400">
                  {customer.phone}
                  {customer.email && ` • ${customer.email}`}
                </span>
              </div>
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}
