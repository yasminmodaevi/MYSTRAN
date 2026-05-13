import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Box, RefreshCw } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { plmApi } from '../services/api';

export interface BOMNode {
  item_id: string;
  name: string;
  revision: string;
  quantity: number;
  children: BOMNode[];
}

const BOMTreeNode = ({ node, depth = 0 }: { node: BOMNode; depth?: number }) => {
  const [isOpen, setIsOpen] = useState(true);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div className="select-none">
      <div
        className="flex items-center gap-2 py-1 px-2 hover:bg-blue-50 rounded cursor-pointer transition-colors"
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
        onClick={() => setIsOpen(!isOpen)}
      >
        {hasChildren ? (
          isOpen ? <ChevronDown size={16} className="text-gray-500" /> : <ChevronRight size={16} className="text-gray-500" />
        ) : (
          <div className="w-4" />
        )}
        <Box size={16} className="text-blue-700" />
        <span className="font-mono text-sm font-medium text-gray-700">{node.item_id}</span>
        <span className="text-sm text-gray-900">{node.name}</span>
        <span className="text-xs bg-gray-200 px-1 rounded text-gray-600">Rev {node.revision}</span>
        {node.quantity > 1 && <span className="text-xs text-blue-600 font-bold">x{node.quantity}</span>}
      </div>

      {isOpen && hasChildren && (
        <div className="border-l border-gray-200 ml-4">
          {node.children.map((child, idx) => (
            <BOMTreeNode key={`${child.item_id}-${idx}`} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

export const BOMViewer = ({ revId, type = "EBOM" }: { revId: string, type?: string }) => {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['bom', revId, type],
    queryFn: () => plmApi.getBOM(revId, type),
    enabled: !!revId,
  });

  if (isLoading) return <div className="p-4 flex items-center gap-2 text-blue-600"><RefreshCw className="animate-spin" /> Loading BOM...</div>;
  if (error) return <div className="p-4 text-red-500 font-medium">Error loading BOM structure</div>;
  if (!data) return <div className="p-4 text-gray-500 italic">No structure defined for this revision.</div>;

  return (
    <div className="bg-white border rounded shadow-sm p-4 overflow-auto max-h-[600px]">
      <div className="flex justify-between items-center mb-4 border-b pb-2">
        <h3 className="text-lg font-bold text-blue-900">BOM Hierarchy ({type})</h3>
        <button onClick={() => refetch()} className="p-1 hover:bg-gray-100 rounded">
           <RefreshCw size={16} className="text-gray-400" />
        </button>
      </div>
      <BOMTreeNode node={data} />
    </div>
  );
};
