import { RouterProvider } from 'react-router-dom';
import { QueryProvider } from '@/core/providers';
import { router } from '@/core/router';
import { Toaster } from '@/components/ui/sonner';

function App() {
  return (
    <QueryProvider>
      <RouterProvider router={router} />
      <Toaster />
    </QueryProvider>
  );
}

export default App;
