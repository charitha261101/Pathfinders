import React, { useState, useEffect } from 'react';
import { steeringApi } from '../../services/api';
import type { SteeringEvent } from '../../types';

const SteeringLog: React.FC = () => {
  const [history, setHistory] = useState<SteeringEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await steeringApi.getHistory(20);
        setHistory(response.data.history);
      } catch (err) {
        console.error('Failed to fetch steering history:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
    const interval = setInterval(fetchHistory, 5000);
    return () => clearInterval(interval);
  }, []);

  const actionColor = (action: string) => {
    switch (action) {
      case 'failover': return 'bg-red-100 text-red-700';
      case 'shift': return 'bg-yellow-100 text-yellow-700';
      case 'rebalance': return 'bg-blue-100 text-blue-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case 'executed': return '\u2713';
      case 'blocked_by_sandbox': return '\u2717';
      case 'failed': return '\u26A0';
      default: return '\u2022';
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-md p-6">
        <div className="animate-pulse space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-gray-100 rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-md p-6">
      <h3 className="font-semibold text-gray-700 mb-4">Steering Audit Log</h3>
      {history.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-4">
          No steering events recorded yet.
        </p>
      ) : (
        <div className="space-y-2">
          {history.map((event, i) => (
            <div key={event.id || i} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <span className="text-lg w-6 text-center">{statusIcon(event.status)}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${actionColor(event.action)}`}>
                    {event.action}
                  </span>
                  <span className="text-sm text-gray-700 truncate">
                    {event.source_link} &rarr; {event.target_link}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-0.5 truncate">{event.reason}</p>
              </div>
              <div className="text-right text-xs text-gray-400">
                <div>{(event.confidence * 100).toFixed(0)}%</div>
                <div>{event.sandbox_validated === 'true' ? 'validated' : 'unvalidated'}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SteeringLog;
