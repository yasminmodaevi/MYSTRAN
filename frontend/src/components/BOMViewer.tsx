import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Box } from 'lucide-react';

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

export const BOMViewer = ({ data }: { data: BOMNode }) => {
  return (
    <div className="bg-white border rounded shadow-sm p-4 overflow-auto max-h-[600px]">
      <h3 className="text-lg font-bold mb-4 text-blue-900 border-b pb-2">BOM Hierarchy</h3>
      <BOMTreeNode node={data} />
    </div>
  );
};
