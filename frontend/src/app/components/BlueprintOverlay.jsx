import { useMemo } from 'react';
import * as THREE from 'three';
import { useLoader } from '@react-three/fiber';

const FLOOR_Y_SPACING = 3.5;

function BlueprintPlane({ imageUrl, floorNumber, width = 50, height = 50 }) {
  const texture = useLoader(THREE.TextureLoader, imageUrl);
  const yOffset = floorNumber * FLOOR_Y_SPACING + 0.01;

  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, yOffset, 0]}>
      <planeGeometry args={[width, height]} />
      <meshBasicMaterial map={texture} transparent opacity={0.85} side={THREE.DoubleSide} />
    </mesh>
  );
}

export default function BlueprintOverlay({ pages, activeFloor, floorHeight = FLOOR_Y_SPACING }) {
  if (!pages?.length) return null;

  const visiblePages = activeFloor != null
    ? pages.filter((_, i) => i === activeFloor - 1)
    : pages;

  return (
    <group>
      {visiblePages.map((page, i) => {
        const floorNum = activeFloor != null ? activeFloor : i + 1;
        if (!page?.url) return null;
        return (
          <BlueprintPlane
            key={`bp-${floorNum}`}
            imageUrl={page.url}
            floorNumber={floorNum}
          />
        );
      })}
    </group>
  );
}
