import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  NavLink,
  Navigate,
} from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  ShieldCheck,
  Network,
  Activity,
  Wifi,
  FlaskConical,
} from "lucide-react";

import Dashboard from "./pages/Dashboard";
import AdminPanel from "./pages/AdminPanel";
import NetworkSimulation from "./pages/NetworkSimulation";
import SandboxViewer from "./pages/SandboxViewer";
import { useScoreboardWebSocket } from "./hooks/useWebSocket";
import { useNetworkStore } from "./store/networkStore";

const NAV_ITEMS = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/simulation", icon: Network, label: "Network Simulation" },
  { to: "/sandbox", icon: FlaskConical, label: "Sandbox" },
  { to: "/admin", icon: ShieldCheck, label: "Admin Panel" },
];

const App: React.FC = () => {
  useScoreboardWebSocket();
  const wsConnected = useNetworkStore((s) => s.wsConnected);
  const lstmEnabled = useNetworkStore((s) => s.lstmEnabled);

  return (
    <Router>
      <div className="flex h-screen bg-pw-bg overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 flex-shrink-0 bg-pw-surface/50 border-r border-pw-border flex flex-col">
          {/* Brand */}
          <div className="p-6 border-b border-pw-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pw-accent to-pw-cyan flex items-center justify-center">
                <Activity className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white tracking-tight">
                  PathWise
                </h1>
                <p className="text-[10px] uppercase tracking-[0.2em] text-pw-accent-light">
                  AI-Powered SD-WAN
                </p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  isActive ? "nav-item-active" : "nav-item"
                }
              >
                <Icon className="w-4 h-4" />
                {label}
              </NavLink>
            ))}
          </nav>

          {/* Status Footer */}
          <div className="p-4 border-t border-pw-border space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-pw-muted">Server</span>
              <div className="flex items-center gap-1.5">
                <div
                  className={
                    wsConnected ? "status-dot-green" : "status-dot-red"
                  }
                />
                <span
                  className={wsConnected ? "text-pw-emerald" : "text-pw-rose"}
                >
                  {wsConnected ? "Connected" : "Offline"}
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-pw-muted">LSTM Model</span>
              <div className="flex items-center gap-1.5">
                <div
                  className={
                    lstmEnabled ? "status-dot-green" : "status-dot-amber"
                  }
                />
                <span
                  className={
                    lstmEnabled ? "text-pw-emerald" : "text-pw-amber"
                  }
                >
                  {lstmEnabled ? "Active" : "Inactive"}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-pw-muted/60">
              <Wifi className="w-3 h-3" />
              <span>Offline Mode — No Docker Required</span>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="h-full"
          >
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/simulation" element={<NetworkSimulation />} />
              <Route path="/sandbox" element={<SandboxViewer />} />
              <Route path="/admin" element={<AdminPanel />} />
            </Routes>
          </motion.div>
        </main>
      </div>
    </Router>
  );
};

export default App;
