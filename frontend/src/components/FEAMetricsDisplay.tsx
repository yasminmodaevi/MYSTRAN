import React from 'react';
import { Activity, Thermometer, Maximize } from 'lucide-react';

interface FEAMetrics {
  max_displacement: number | null;
  max_stress: number | null;
  margin_of_safety: number | null;
}

export const FEAMetricsDisplay = ({ metrics }: { metrics?: FEAMetrics }) => {
  if (!metrics) return <div className="text-gray-400 italic text-sm">No simulation data available.</div>;

  return (
    <div className="bg-slate-50 border rounded-lg p-4 space-y-4">
      <div className="flex items-center gap-2 text-slate-800 font-bold border-b pb-2">
        <Activity size={18} />
        <span>Simulation Results (Nastran)</span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col">
          <span className="text-xs text-gray-500 uppercase">Max Displacement</span>
          <div className="flex items-center gap-2 font-mono text-lg text-blue-700">
            <Maximize size={16} />
            {metrics.max_displacement?.toFixed(4) || "N/A"} mm
          </div>
        </div>

        <div className="flex flex-col">
          <span className="text-xs text-gray-500 uppercase">Max Stress (Von Mises)</span>
          <div className="flex items-center gap-2 font-mono text-lg text-red-600">
            <Thermometer size={16} />
            {metrics.max_stress?.toFixed(2) || "N/A"} MPa
          </div>
        </div>
      </div>

      {metrics.margin_of_safety !== null && (
        <div className="pt-2 border-t text-sm">
          <span className="text-gray-600">Margin of Safety: </span>
          <span className={`font-bold ${metrics.margin_of_safety > 0 ? 'text-green-600' : 'text-red-600'}`}>
            {metrics.margin_of_safety.toFixed(2)}
          </span>
        </div>
      )}
    </div>
  );
};
