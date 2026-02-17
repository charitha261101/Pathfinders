import React from 'react';
import HealthScoreboard from '../components/HealthScoreboard/HealthScoreboard';
import PredictionChart from '../components/PredictionChart/PredictionChart';
import TopologyMap from '../components/TopologyMap/TopologyMap';
import SteeringLog from '../components/SteeringLog/SteeringLog';
import { useScoreboardWebSocket } from '../hooks/useWebSocket';
import { useActiveLinks } from '../hooks/useTelemetry';

const Dashboard: React.FC = () => {
  useScoreboardWebSocket();
  useActiveLinks();

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Network Dashboard</h1>
          <p className="text-sm text-gray-500">
            Real-time multi-link health monitoring with predictive analytics
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
            Live
          </span>
          <span className="text-sm text-gray-400">Updated every 1s</span>
        </div>
      </div>

      {/* Health Scoreboard — Primary Feature */}
      <section>
        <h2 className="text-lg font-semibold text-gray-700 mb-3">Link Health Scoreboard</h2>
        <HealthScoreboard />
      </section>

      {/* Prediction Chart + Steering Log side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section>
          <h2 className="text-lg font-semibold text-gray-700 mb-3">Telemetry Predictions</h2>
          <div className="bg-white rounded-xl shadow-md p-6">
            <PredictionChart />
          </div>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700 mb-3">Steering Activity</h2>
          <SteeringLog />
        </section>
      </div>

      {/* Topology Map */}
      <section>
        <h2 className="text-lg font-semibold text-gray-700 mb-3">Network Topology</h2>
        <div className="bg-white rounded-xl shadow-md p-6">
          <TopologyMap />
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
