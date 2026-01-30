import { RouterProvider } from 'react-router-dom';
import { QueryProvider, ThemeProvider } from '@/core/providers';
import { router } from '@/core/router';
import { Toaster } from '@/components/ui/sonner';
import { AuthProvider } from '@/features/auth';

function App() {
  return (
    <ThemeProvider defaultTheme="system">
      <QueryProvider>
        <AuthProvider>
          <RouterProvider router={router} />
          <Toaster />
        </AuthProvider>
      </QueryProvider>
    </ThemeProvider>
  );
}

export default App;
