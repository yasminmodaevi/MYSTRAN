import React from 'react';
import { CheckCircle, Clock, AlertTriangle } from 'lucide-react';

interface Task {
  id: string;
  name: string;
  status: string;
  assigned_to: string;
}

export const WorkflowTasks = ({ tasks }: { tasks: Task[] }) => {
  return (
    <div className="bg-white border rounded shadow-sm">
      <div className="p-4 border-b bg-slate-50 flex justify-between items-center">
        <h3 className="font-bold text-slate-800">My Action Items</h3>
        <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full font-bold">
          {tasks.length} Pending
        </span>
      </div>

      <div className="divide-y">
        {tasks.map((task) => (
          <div key={task.id} className="p-4 flex items-center justify-between hover:bg-slate-50">
            <div className="flex items-center gap-3">
              {task.status === 'READY' ? (
                <Clock className="text-blue-500" size={20} />
              ) : (
                <AlertTriangle className="text-amber-500" size={20} />
              )}
              <div>
                <div className="text-sm font-bold text-gray-900">{task.name}</div>
                <div className="text-xs text-gray-500">ID: {task.id} | Assigned to: {task.assigned_to}</div>
              </div>
            </div>

            <button className="flex items-center gap-1 bg-green-600 text-white px-3 py-1 rounded text-xs font-bold hover:bg-green-700 transition-colors">
              <CheckCircle size={14} />
              Complete
            </button>
          </div>
        ))}
        {tasks.length === 0 && (
          <div className="p-8 text-center text-gray-400 italic">No pending tasks for you.</div>
        )}
      </div>
    </div>
  );
};
