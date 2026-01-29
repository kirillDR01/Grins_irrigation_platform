import { RouterProvider } from 'react-router-dom';
import { QueryProvider } from '@/core/providers';
import { router } from '@/core/router';
import { Toaster } from '@/components/ui/sonner';
import { AuthProvider } from '@/features/auth';

function App() {
  return (
    <QueryProvider>
      <AuthProvider>
        <RouterProvider router={router} />
        <Toaster />
      </AuthProvider>
    </QueryProvider>
  );
}

export default App;
