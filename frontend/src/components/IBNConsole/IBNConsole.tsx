import React, { useState } from 'react';
import { apiClient } from '../../services/api';

interface PolicyResult {
  status: string;
  intent: string;
  rules_generated: Array<{
    name: string;
    traffic_class: string;
    priority: number;
    action: string;
    target_links: string[];
  }>;
  validation: Array<{ rule: string; validated: boolean }>;
}

const IBNConsole: React.FC = () => {
  const [intent, setIntent] = useState('');
  const [result, setResult] = useState<PolicyResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const exampleIntents = [
    'Prioritize VoIP over guest WiFi',
    'Guarantee 50 Mbps for video conferencing',
    'Block streaming on satellite-backup',
    'Set max latency for medical imaging to 20ms',
    'Redirect backup traffic to broadband-secondary',
  ];

  const submitIntent = async () => {
    if (!intent.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiClient.post('/api/v1/policies/intent', {
        intent: intent,
      });
      setResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to parse intent');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-md p-6">
      {/* Intent Input */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-600 mb-2">
          Enter network policy intent in natural language:
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submitIntent()}
            placeholder="e.g., Prioritize VoIP over guest WiFi"
            className="flex-1 border border-gray-300 rounded-md px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <button
            onClick={submitIntent}
            disabled={loading || !intent.trim()}
            className="bg-blue-600 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Parsing...' : 'Apply'}
          </button>
        </div>
      </div>

      {/* Example Intents */}
      <div className="mb-4">
        <p className="text-xs text-gray-400 mb-2">Try these examples:</p>
        <div className="flex flex-wrap gap-2">
          {exampleIntents.map((ex) => (
            <button
              key={ex}
              onClick={() => setIntent(ex)}
              className="text-xs bg-gray-100 text-gray-600 px-3 py-1 rounded-full hover:bg-gray-200 transition-colors"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm mb-4">
          {error}
        </div>
      )}

      {/* Result Display */}
      {result && (
        <div className="border-t pt-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            Generated Rules ({result.rules_generated.length})
          </h4>
          <div className="space-y-2">
            {result.rules_generated.map((rule, i) => (
              <div key={i} className="bg-gray-50 rounded-md p-3 text-sm">
                <div className="flex justify-between items-center">
                  <span className="font-medium text-gray-700">{rule.name}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    rule.action === 'prioritize' ? 'bg-green-100 text-green-700' :
                    rule.action === 'throttle' ? 'bg-yellow-100 text-yellow-700' :
                    rule.action === 'block' ? 'bg-red-100 text-red-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {rule.action}
                  </span>
                </div>
                <div className="text-gray-500 mt-1">
                  Traffic: {rule.traffic_class} | Priority: {rule.priority} | Links: {rule.target_links.join(', ')}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default IBNConsole;
