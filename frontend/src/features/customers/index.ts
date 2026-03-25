// Components
export {
  CustomerList,
  CustomerDetail,
  CustomerForm,
  CustomerSearch,
  PhotoGallery,
  InvoiceHistory,
  PaymentMethods,
  CustomerMessages,
  DuplicateReview,
} from './components';

// Hooks
export {
  useCustomers,
  useCustomer,
  useCustomerSearch,
  useCustomerPhotos,
  useCustomerInvoices,
  useCustomerPaymentMethods,
  useCustomerDuplicates,
  useCustomerSentMessages,
  customerKeys,
  useCreateCustomer,
  useUpdateCustomer,
  useDeleteCustomer,
  useUpdateCustomerFlags,
  useUploadCustomerPhotos,
  useUpdatePhotoCaption,
  useDeleteCustomerPhoto,
  useChargeCustomer,
  useMergeCustomers,
} from './hooks';

// Types
export type {
  Customer,
  CustomerCreate,
  CustomerUpdate,
  CustomerListParams,
  CustomerFlag,
  CustomerPhoto,
  CustomerInvoice,
  InvoiceStatus,
  PaymentMethod,
  ChargeRequest,
  DuplicateGroup,
  MergeRequest,
  SentMessage,
} from './types';
export { getCustomerFlags, getCustomerFullName, invoiceStatusColors } from './types';

// API
export { customerApi } from './api/customerApi';
