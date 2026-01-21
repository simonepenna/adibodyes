import { signOut, getCurrentUser } from 'aws-amplify/auth';
import { useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';

interface HeaderProps {
  onMenuClick: () => void;
}

const Header = ({ onMenuClick }: HeaderProps) => {
  const location = useLocation();
  const [userInitial, setUserInitial] = useState('U');
  const [userName, setUserName] = useState('Utente');

  useEffect(() => {
    const getUserInfo = async () => {
      try {
        const user = await getCurrentUser();
        const name = user.signInDetails?.loginId || user.username || '';
        const initial = name.charAt(0).toUpperCase();
        setUserInitial(initial || 'U');
        
        // Estrai il nome prima della @ per gli email, altrimenti usa il nome completo
        const displayName = name.includes('@') ? name.split('@')[0] : name;
        setUserName(displayName || 'Utente');
      } catch (error) {
        console.error('Errore nel recupero utente:', error);
        setUserInitial('U');
        setUserName('Utente');
      }
    };

    getUserInfo();
  }, []);

  const getPageTitle = (pathname: string) => {
    switch (pathname) {
      case '/dashboard':
        return 'Dashboard';
      case '/stock':
        return 'Stock';
      case '/evasione':
        return 'Evasione';
      case '/rifiuti':
        return 'Rifiuti';
      case '/gls-parcel-shop':
        return 'GLS Parcel Shop';
      default:
        return 'Dashboard';
    }
  };

  const handleLogout = async () => {
    try {
      await signOut();
      // Ricarica la pagina per forzare il controllo dell'autenticazione
      window.location.reload();
    } catch (error) {
      console.error('Errore durante il logout:', error);
    }
  };

  return (
    <header className="bg-base-100 border-b border-base-300 px-4 py-3 lg:px-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <button
            onClick={onMenuClick}
            className="btn btn-ghost btn-sm lg:hidden"
          >
            ☰
          </button>
          <h2 className="ml-4 text-lg font-semibold text-base-content lg:ml-0">
            {getPageTitle(location.pathname)}
          </h2>
        </div>

        <div className="flex items-center space-x-4">
          <div className="dropdown dropdown-end">
            <div tabIndex={0} role="button" className="btn btn-circle avatar hover:bg-base-200 active:bg-base-200 focus:bg-base-200">
              <div className="w-8 rounded-full bg-base-300 border-2 border-base-content/20 flex items-center justify-center">
                <span className="text-xs text-base-content font-semibold">
                  {userInitial}
                </span>
              </div>
            </div>
            <ul tabIndex={0} className="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
              <li className="menu-title pointer-events-none">
                <span className="text-base-content font-medium">{userName}</span>
              </li>
              <li>
                <a onClick={handleLogout} className="text-error hover:bg-error hover:text-error-content">
                  Logout
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;