import React from 'react';
import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard', icon: '\u2302' },
  { to: '/policies', label: 'Policy Manager', icon: '\u2699' },
  { to: '/sandbox', label: 'Sandbox', icon: '\u29C9' },
];

const Sidebar: React.FC = () => {
  return (
    <aside className="w-56 bg-slate-900 text-gray-300 min-h-screen hidden lg:block">
      <div className="p-4">
        <h2 className="text-xs uppercase tracking-wider text-gray-500 font-semibold mb-4">
          Navigation
        </h2>
        <nav className="space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-slate-700 text-white font-medium'
                    : 'text-gray-400 hover:bg-slate-800 hover:text-gray-200'
                }`
              }
            >
              <span className="text-lg">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      {/* System status */}
      <div className="absolute bottom-0 w-56 p-4 border-t border-slate-700">
        <div className="text-xs text-gray-500">
          <p>PathWise AI v1.0.0</p>
          <p className="mt-1">Team Pathfinders</p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
