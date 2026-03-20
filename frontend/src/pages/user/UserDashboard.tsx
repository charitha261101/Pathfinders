import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../utils/apiClient';
import { healthColor } from '../../utils/theme';
import UserLayout from '../../components/layout/UserLayout';

export default function UserDashboard() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<any>(null);
  const [telemetry, setTelemetry] = useState<Record<string, any>>({});
  const [selectedSite, setSelectedSite] = useState('');
  const [lstmOn, setLstmOn] = useState<boolean>(false);
  const [lstmToggling, setLstmToggling] = useState<boolean>(false);
  const [lstmMsg, setLstmMsg] = useState<string>('');

  useEffect(() => {
    api.get<any>('/profile/').then(d => {
      setProfile(d);
      if (d.sites?.length > 0) setSelectedSite(d.sites[0].id);
    }).catch(() => {});
    api.get<{ lstm_enabled: boolean }>('/admin/lstm-status')
      .then(d => setLstmOn(!!d.lstm_enabled))
      .catch(() => {});
  }, []);

  const toggleLstm = async () => {
    setLstmToggling(true);
    try {
      const next = !lstmOn;
      const res = await api.post<{ lstm_enabled: boolean }>('/admin/lstm-toggle', { enabled: next });
      setLstmOn(!!res.lstm_enabled);
      setLstmMsg(`Predictive engine ${res.lstm_enabled ? 'enabled' : 'disabled'}.`);
      setTimeout(() => setLstmMsg(''), 2500);
    } catch {
      setLstmMsg('Could not toggle LSTM. Please try again.');
      setTimeout(() => setLstmMsg(''), 2500);
    } finally {
      setLstmToggling(false);
    }
  };

  useEffect(() => {
    if (!selectedSite) return;
    api.get<any>(`/telemetry/site/${selectedSite.split('-').pop() || 1}`).then(d => {
      setTelemetry(prev => ({ ...prev, [selectedSite]: d }));
    }).catch(() => {});
    const iv = setInterval(() => {
      api.get<any>(`/telemetry/site/${selectedSite.split('-').pop() || 1}`).then(d => {
        setTelemetry(prev => ({ ...prev, [selectedSite]: d }));
      }).catch(() => {});
    }, 5000);
    return () => clearInterval(iv);
  }, [selectedSite]);

  const sites = profile?.sites ?? [];
  const sub = profile?.subscription;
  const siteData = telemetry[selectedSite];
  const links = siteData?.links ?? [];
  const avgHealth = links.length > 0 ? links.reduce((s: number, l: any) => s + l.health_score, 0) / links.length : 0;

  const greeting = new Date().getHours() < 12 ? 'Good morning' : new Date().getHours() < 17 ? 'Good afternoon' : 'Good evening';

  return (
    <UserLayout>
      <div className="p-6 space-y-6">
        {/* Welcome */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 text-white">
          <h1 className="text-xl font-bold">{greeting}, {user?.name?.split(' ')[0]}</h1>
          <p className="text-blue-100 text-sm mt-1">{user?.company} — {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}</p>
        </div>

        {/* LSTM Prediction Engine toggle (user-visible kill switch) */}
        <div
          className={`rounded-xl border shadow-sm p-5 flex items-center justify-between transition-colors ${
            lstmOn ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50 border-slate-200'
          }`}
        >
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`inline-block w-3 h-3 rounded-full ${
                  lstmOn ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'
                }`}
              />
              <div className="text-sm uppercase tracking-wide font-semibold text-slate-600">
                Predictive AI Engine
              </div>
            </div>
            <div className={`text-2xl font-bold mt-1 ${lstmOn ? 'text-emerald-700' : 'text-slate-700'}`}>
              {lstmOn ? 'ACTIVE' : 'OFF'}
            </div>
            <div className="text-sm text-slate-600 mt-1">
              {lstmOn
                ? 'LSTM is forecasting link degradation 30-60 seconds ahead and pre-emptively steering traffic.'
                : 'LSTM is disabled. Your sites fall back to reactive threshold-based failover only.'}
            </div>
            {lstmMsg && (
              <div className="text-xs text-emerald-600 mt-2">{lstmMsg}</div>
            )}
          </div>
          <button
            onClick={toggleLstm}
            disabled={lstmToggling}
            className={`relative inline-flex h-10 w-20 items-center rounded-full transition-colors ${
              lstmOn ? 'bg-emerald-500' : 'bg-slate-300'
            } ${lstmToggling ? 'opacity-60 cursor-wait' : 'cursor-pointer'}`}
            aria-label="Toggle predictive AI engine"
          >
            <span
              className={`inline-block h-8 w-8 transform rounded-full bg-white shadow transition-transform ${
                lstmOn ? 'translate-x-11' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4">
          {[
            { label: 'Total Sites', value: sites.length, color: '#3b82f6' },
            { label: 'Active WAN Links', value: links.length, color: '#0ea5e9' },
            { label: 'Avg Health Score', value: avgHealth.toFixed(0), color: healthColor(avgHealth) },
            { label: 'Plan', value: sub?.plan_name ?? '—', color: '#8b5cf6' },
          ].map(c => (
            <div key={c.label} className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm">
              <p className="text-xs text-slate-500">{c.label}</p>
              <p className="text-xl font-bold mt-1" style={{ color: c.color }}>{c.value}</p>
            </div>
          ))}
        </div>

        {/* Site Tabs + Health Cards */}
        {sites.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
            <div className="border-b border-slate-200 px-4 flex gap-1 overflow-x-auto">
              {sites.map((s: any) => (
                <button key={s.id} onClick={() => setSelectedSite(s.id)}
                  className={`px-4 py-3 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                    selectedSite === s.id ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700'
                  }`}>{s.name}</button>
              ))}
            </div>
            <div className="p-4">
              {links.length > 0 ? (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  {links.map((l: any) => {
                    const sc = l.health_score;
                    return (
                      <div key={l.link_id} className="bg-slate-50 rounded-lg p-4 border border-slate-200">
                        <div className="flex justify-between items-start mb-3">
                          <div>
                            <p className="font-medium text-sm text-slate-900 capitalize">{l.link_id.replace(/-/g, ' ')}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-2xl font-bold" style={{ color: healthColor(sc) }}>{sc}</p>
                            <p className="text-[10px] text-slate-400">health</p>
                          </div>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          <div><p className="text-slate-400">Latency</p><p className="font-semibold">{l.latency_ms}ms</p></div>
                          <div><p className="text-slate-400">Jitter</p><p className="font-semibold">{l.jitter_ms}ms</p></div>
                          <div><p className="text-slate-400">Loss</p><p className="font-semibold">{l.packet_loss_pct}%</p></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-center py-8 text-slate-400 text-sm">
                  Loading telemetry data... Data refreshes every 5 seconds.
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </UserLayout>
  );
}
