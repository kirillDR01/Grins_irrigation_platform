// Components
export { CustomerList, CustomerDetail, CustomerForm, CustomerSearch } from './components';

// Hooks
export {
  useCustomers,
  useCustomer,
  useCustomerSearch,
  customerKeys,
  useCreateCustomer,
  useUpdateCustomer,
  useDeleteCustomer,
  useUpdateCustomerFlags,
} from './hooks';

// Types
export type {
  Customer,
  CustomerCreate,
  CustomerUpdate,
  CustomerListParams,
  CustomerFlag,
} from './types';
export { getCustomerFlags, getCustomerFullName } from './types';

// API
export { customerApi } from './api/customerApi';
