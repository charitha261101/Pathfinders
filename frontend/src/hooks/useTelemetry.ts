import { useState, useEffect, useCallback } from 'react';
import { telemetryApi, predictionApi } from '../services/api';
import { useNetworkStore } from '../store/networkStore';
import type { TelemetryPoint } from '../types';

/**
 * Hook for fetching telemetry data for a specific link.
 * Polls every `intervalMs` (default 1000ms).
 */
export function useTelemetry(linkId: string, intervalMs: number = 1000) {
  const [data, setData] = useState<TelemetryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const response = await telemetryApi.getTelemetry(linkId, '60s');
      setData(response.data.data_points);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch telemetry');
    } finally {
      setLoading(false);
    }
  }, [linkId]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, intervalMs);
    return () => clearInterval(interval);
  }, [fetchData, intervalMs]);

  return { data, loading, error, refetch: fetchData };
}

/**
 * Hook for fetching active links and their predictions.
 * Polls every 5 seconds.
 */
export function useActiveLinks() {
  const setActiveLinks = useNetworkStore((s) => s.setActiveLinks);
  const updatePredictions = useNetworkStore((s) => s.updatePredictions);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLinks = async () => {
      try {
        const [linksRes, predsRes] = await Promise.all([
          telemetryApi.getLinks(),
          predictionApi.getAll(),
        ]);
        setActiveLinks(linksRes.data.links);
        updatePredictions(predsRes.data.predictions);
      } catch (err) {
        console.error('Failed to fetch active links:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchLinks();
    const interval = setInterval(fetchLinks, 5000);
    return () => clearInterval(interval);
  }, [setActiveLinks, updatePredictions]);

  return { loading };
}
