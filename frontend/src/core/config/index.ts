export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  apiVersion: 'v1',
  stripeCustomerPortalUrl: import.meta.env.VITE_STRIPE_CUSTOMER_PORTAL_URL || '',
} as const;

export const getApiUrl = (path: string): string => {
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;
  return `${config.apiBaseUrl}/api/${config.apiVersion}/${cleanPath}`;
};
