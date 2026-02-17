import React, { useState } from 'react';
import { apiClient } from '../services/api';

interface SandboxReport {
  id: string;
  result: string;
  details: string;
  loop_free: boolean;
  policy_compliant: boolean;
  reachability_verified: boolean;
  execution_time_ms: number;
}

const SandboxViewer: React.FC = () => {
  const [report, setReport] = useState<SandboxReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [sourceLink, setSourceLink] = useState('broadband-secondary');
  const [targetLink, setTargetLink] = useState('fiber-primary');

  const runValidation = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post('/api/v1/sandbox/validate', {
        source_link: sourceLink,
        target_link: targetLink,
        traffic_classes: ['voip', 'video', 'critical'],
      });
      setReport(response.data);
    } catch (err) {
      console.error('Sandbox validation failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Digital Twin Sandbox</h1>
        <p className="text-sm text-gray-500">
          Validate routing changes before deployment using Mininet + Batfish
        </p>
      </div>

      {/* Validation Form */}
      <div className="bg-white rounded-xl shadow-md p-6">
        <h3 className="font-semibold text-gray-700 mb-4">Run Validation</h3>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Source Link</label>
            <select
              value={sourceLink}
              onChange={(e) => setSourceLink(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="fiber-primary">Fiber Primary</option>
              <option value="broadband-secondary">Broadband Secondary</option>
              <option value="satellite-backup">Satellite Backup</option>
              <option value="5g-mobile">5G Mobile</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Target Link</label>
            <select
              value={targetLink}
              onChange={(e) => setTargetLink(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              <option value="fiber-primary">Fiber Primary</option>
              <option value="broadband-secondary">Broadband Secondary</option>
              <option value="satellite-backup">Satellite Backup</option>
              <option value="5g-mobile">5G Mobile</option>
            </select>
          </div>
        </div>
        <button
          onClick={runValidation}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Validating...' : 'Run Sandbox Validation'}
        </button>
      </div>

      {/* Validation Report */}
      {report && (
        <div className="bg-white rounded-xl shadow-md p-6">
          <h3 className="font-semibold text-gray-700 mb-4">Validation Report</h3>
          <div className="grid grid-cols-3 gap-4">
            <StatusBadge label="Loop Free" passed={report.loop_free} />
            <StatusBadge label="Policy Compliant" passed={report.policy_compliant} />
            <StatusBadge label="Reachability" passed={report.reachability_verified} />
          </div>
          <div className="mt-4 text-sm">
            <p className="text-gray-600"><strong>Result:</strong> {report.result}</p>
            <p className="text-gray-600"><strong>Details:</strong> {report.details}</p>
            <p className="text-gray-600">
              <strong>Execution Time:</strong> {report.execution_time_ms.toFixed(1)}ms
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

const StatusBadge: React.FC<{ label: string; passed: boolean }> = ({ label, passed }) => (
  <div className={`rounded-lg p-3 text-center ${passed ? 'bg-green-50' : 'bg-red-50'}`}>
    <div className={`text-2xl ${passed ? 'text-green-500' : 'text-red-500'}`}>
      {passed ? '\u2713' : '\u2717'}
    </div>
    <div className="text-sm font-medium text-gray-700 mt-1">{label}</div>
  </div>
);

export default SandboxViewer;
