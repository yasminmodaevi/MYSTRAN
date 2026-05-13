import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stage, PerspectiveCamera, Grid } from '@react-three/drei';

const Model = ({ url }: { url?: string }) => {
  // In a real implementation, we would use useGLTF(url) here.
  // For this scaffold, we show a placeholder box representing the aerospace part.
  return (
    <mesh castShadow receiveShadow>
      <boxGeometry args={[2, 0.5, 4]} />
      <meshStandardMaterial color="#3b82f6" />
    </mesh>
  );
};

export const AeroViewer3D = ({ fileUrl }: { fileUrl?: string }) => {
  return (
    <div className="w-full h-[500px] bg-slate-900 rounded-lg overflow-hidden relative border-4 border-slate-800">
      <div className="absolute top-4 left-4 z-10 bg-black/50 text-white p-2 rounded text-xs">
        3D PREVIEW | {fileUrl || "SCAFFOLD_PART_001.GLB"}
      </div>

      <Canvas shadows dpr={[1, 2]}>
        <Suspense fallback={null}>
          <PerspectiveCamera makeDefault position={[5, 5, 5]} fov={50} />
          <Stage environment="city" intensity={0.6}>
            <Model url={fileUrl} />
          </Stage>
          <Grid
            infiniteGrid
            fadeDistance={20}
            cellColor="#475569"
            sectionColor="#1e293b"
          />
          <OrbitControls makeDefault minPolarAngle={0} maxPolarAngle={Math.PI / 1.75} />
        </Suspense>
      </Canvas>

      <div className="absolute bottom-4 right-4 flex gap-2">
        <button className="bg-slate-700 text-white px-3 py-1 rounded text-xs hover:bg-slate-600">Front</button>
        <button className="bg-slate-700 text-white px-3 py-1 rounded text-xs hover:bg-slate-600">Top</button>
        <button className="bg-slate-700 text-white px-3 py-1 rounded text-xs hover:bg-slate-600">Iso</button>
      </div>
    </div>
  );
};
