import { Link, useLocation } from 'react-router-dom';

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (isOpen: boolean) => void;
}

const Sidebar = ({ isOpen, setIsOpen }: SidebarProps) => {
  const location = useLocation();

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: '📊' },
    { name: 'Stock', href: '/stock', icon: '📦' },
    { name: 'Evasione', href: '/evasione', icon: '🚚' },
    { name: 'Rifiuti', href: '/rifiuti', icon: '♻️' },
  ];

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex flex-col flex-grow bg-base-100 border-r border-base-300">
          <div className="flex items-center justify-center h-16 px-4 bg-primary">
            <h1 className="text-xl font-bold text-white">AdiBody ES</h1>
          </div>
          <nav className="flex-1 px-4 py-4 space-y-2">
            {navigation.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-4 py-3 text-base font-semibold rounded-lg transition-colors ${
                  location.pathname === item.href
                    ? 'bg-primary text-white'
                    : 'text-base-content hover:bg-base-200'
                }`}
              >
                <span className="mr-3 text-xl">{item.icon}</span>
                {item.name}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      {/* Mobile sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-base-100 border-r border-base-300 transform transition-transform lg:hidden ${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="flex items-center justify-between h-16 px-4 bg-primary">
          <h1 className="text-xl font-bold text-white">AdiBody ES</h1>
          <button
            onClick={() => setIsOpen(false)}
            className="btn btn-ghost btn-sm text-white hover:bg-white/20"
          >
            ✕
          </button>
        </div>
        <nav className="px-4 py-4 space-y-2">
          {navigation.map((item) => (
            <Link
              key={item.name}
              to={item.href}
              onClick={() => setIsOpen(false)}
              className={`flex items-center px-4 py-3 text-base font-semibold rounded-lg transition-colors ${
                location.pathname === item.href
                  ? 'bg-primary text-white'
                  : 'text-base-content hover:bg-base-200'
              }`}
            >
              <span className="mr-3 text-xl">{item.icon}</span>
              {item.name}
            </Link>
          ))}
        </nav>
      </div>
    </>
  );
};

export default Sidebar;