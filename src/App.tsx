import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { getCurrentUser } from 'aws-amplify/auth';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Stock from './pages/Stock';
import Evasione from './pages/Evasione';
import Rifiuti from './pages/Rifiuti';
import GLSParcelShop from './pages/GLSParcelShop';
import GLSAlmacenado from './pages/GLSAlmacenado';
import Rimborsi from './pages/Rimborsi';
import Login from './components/Login';
import './aws-config';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 10 * 60 * 1000, // 10 minuti
        gcTime: 30 * 60 * 1000, // 30 minuti in memoria
        refetchOnWindowFocus: false,
        refetchOnMount: false,
      },
    },
  });

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const user = await getCurrentUser();
      console.log('User authenticated:', user);
      setIsAuthenticated(true);
    } catch (error) {
      console.log('Not authenticated:', error);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-base-200">
        <div className="text-center">
          <div className="loading loading-spinner loading-lg text-primary"></div>
          <p className="mt-4 text-base-content/70">Loading...</p>
        </div>
      </div>
    );
  }

  // Show main app with routing
  console.log('App rendering - isAuthenticated:', isAuthenticated, 'isLoading:', isLoading);
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        {!isAuthenticated ? (
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        ) : (
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/stock" element={<Stock />} />
              <Route path="/evasione" element={<Evasione />} />
              <Route path="/rifiuti" element={<Rifiuti />} />
              <Route path="/gls-parcel-shop" element={<GLSParcelShop />} />
              <Route path="/gls-almacenado" element={<GLSAlmacenado />} />
              <Route path="/rimborsi" element={<Rimborsi />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Route>
          </Routes>
        )}
      </Router>
    </QueryClientProvider>
  );
}

export default App;
