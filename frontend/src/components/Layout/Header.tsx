import React from 'react';
import { useNetworkStore } from '../../store/networkStore';

const Header: React.FC = () => {
  const wsConnected = useNetworkStore((s) => s.wsConnected);
  const linkCount = useNetworkStore((s) => Object.keys(s.scoreboard).length);

  return (
    <header className="bg-slate-800 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-2">
            <span className="text-xl font-bold text-blue-400">PathWise</span>
            <span className="text-sm text-gray-400">AI-Powered SD-WAN</span>
          </div>

          {/* Status indicators */}
          <div className="flex items-center space-x-4">
            {/* Link count */}
            <div className="text-sm text-gray-300">
              <span className="font-medium">{linkCount}</span> active links
            </div>

            {/* WebSocket status */}
            <div className="flex items-center space-x-1.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  wsConnected ? 'bg-green-400 animate-pulse-slow' : 'bg-red-400'
                }`}
              />
              <span className="text-xs text-gray-400">
                {wsConnected ? 'Live' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
