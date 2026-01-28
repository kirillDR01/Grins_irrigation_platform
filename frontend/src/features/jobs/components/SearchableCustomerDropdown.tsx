import { useState, useEffect, useCallback } from 'react';
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
  const [debounceTimeout, setDebounceTimeout] = useState<NodeJS.Timeout | null>(null);

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
    if (debounceTimeout) {
      clearTimeout(debounceTimeout);
    }

    // Set new timeout for debounced search
    const timeout = setTimeout(() => {
      searchCustomers(query);
    }, 300);

    setDebounceTimeout(timeout);
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
      if (debounceTimeout) {
        clearTimeout(debounceTimeout);
      }
    };
  }, [debounceTimeout]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between"
          disabled={disabled}
          data-testid="customer-dropdown"
        >
          {selectedCustomer ? (
            <span className="truncate">
              {selectedCustomer.first_name} {selectedCustomer.last_name} - {selectedCustomer.phone}
            </span>
          ) : (
            <span className="text-muted-foreground">Select customer...</span>
          )}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[400px] p-0" align="start">
        <div className="flex items-center border-b px-3">
          <Input
            placeholder="Search by name, phone, or email..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="border-0 focus-visible:ring-0 focus-visible:ring-offset-0"
            data-testid="customer-search-input"
            autoFocus
          />
          {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
        </div>
        <div className="max-h-[300px] overflow-y-auto">
          {customers.length === 0 && searchQuery && !isLoading && (
            <div className="py-6 text-center text-sm text-muted-foreground">
              No customers found
            </div>
          )}
          {customers.length === 0 && !searchQuery && (
            <div className="py-6 text-center text-sm text-muted-foreground">
              Start typing to search customers
            </div>
          )}
          {customers.map((customer) => (
            <button
              key={customer.id}
              onClick={() => handleSelect(customer)}
              className={cn(
                'relative flex w-full cursor-pointer select-none items-center gap-2 px-3 py-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground',
                value === customer.id && 'bg-accent'
              )}
              data-testid={`customer-option-${customer.id}`}
            >
              <Check
                className={cn(
                  'h-4 w-4',
                  value === customer.id ? 'opacity-100' : 'opacity-0'
                )}
              />
              <div className="flex flex-col items-start">
                <span className="font-medium">
                  {customer.first_name} {customer.last_name}
                </span>
                <span className="text-xs text-muted-foreground">
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
