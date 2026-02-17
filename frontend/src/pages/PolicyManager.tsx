import React from 'react';
import IBNConsole from '../components/IBNConsole/IBNConsole';

const PolicyManager: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Policy Manager</h1>
        <p className="text-sm text-gray-500">
          Intent-Based Network management — define policies in natural language
        </p>
      </div>

      {/* IBN Console */}
      <section>
        <h2 className="text-lg font-semibold text-gray-700 mb-3">Intent Console</h2>
        <IBNConsole />
      </section>

      {/* Active Policies */}
      <section>
        <h2 className="text-lg font-semibold text-gray-700 mb-3">Active Policies</h2>
        <div className="bg-white rounded-xl shadow-md p-6">
          <div className="text-sm text-gray-400 text-center py-8">
            No active policies. Use the Intent Console above to create one.
          </div>
        </div>
      </section>
    </div>
  );
};

export default PolicyManager;
