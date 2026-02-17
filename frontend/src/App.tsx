import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import PolicyManager from './pages/PolicyManager';
import SandboxViewer from './pages/SandboxViewer';

const App: React.FC = () => {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="bg-slate-800 text-white shadow-lg">
          <div className="max-w-7xl mx-auto px-4">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold text-blue-400">PathWise</span>
                <span className="text-sm text-gray-400">AI-Powered SD-WAN</span>
              </div>
              <div className="flex space-x-4">
                <NavLink
                  to="/"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive ? 'bg-slate-700 text-white' : 'text-gray-300 hover:text-white'
                    }`
                  }
                >
                  Dashboard
                </NavLink>
                <NavLink
                  to="/policies"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive ? 'bg-slate-700 text-white' : 'text-gray-300 hover:text-white'
                    }`
                  }
                >
                  Policy Manager
                </NavLink>
                <NavLink
                  to="/sandbox"
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive ? 'bg-slate-700 text-white' : 'text-gray-300 hover:text-white'
                    }`
                  }
                >
                  Sandbox
                </NavLink>
              </div>
            </div>
          </div>
        </nav>

        {/* Page Content */}
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/policies" element={<PolicyManager />} />
            <Route path="/sandbox" element={<SandboxViewer />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;
