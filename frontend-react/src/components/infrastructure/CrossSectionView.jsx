import { useRef, useEffect, useState, useMemo } from 'react';

const BRIDGE_COLORS = {
  deck: '#888888',
  girder: '#666666',
  barrier: '#bbbbbb',
  ground: '#4a3a2a',
};

export default function CrossSectionView({ bridgeParams, stationPercent: initialStation }) {
  const canvasRef = useRef(null);
  const [station, setStation] = useState(initialStation ?? 50);

  const params = useMemo(() => ({
    deck_width_m: bridgeParams?.deck_width_m || 12,
    deck_depth_m: bridgeParams?.deck_depth_m || 0.3,
    girder_depth_m: bridgeParams?.girder_depth_m || 1.2,
    girder_count: bridgeParams?.girder_count || 4,
    barrier_height_m: bridgeParams?.barrier_height_m || 1.1,
    barrier_type: bridgeParams?.barrier_type || 'jersey',
    pier_height_m: bridgeParams?.pier_height_m || 8,
  }), [bridgeParams]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const w = rect.width;
    const h = rect.height;

    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, w, h);

    // Scale: 1m = pixels
    const totalH = params.pier_height_m + params.deck_depth_m + params.barrier_height_m + 2;
    const totalW = params.deck_width_m + 4;
    const scale = Math.min((w - 80) / totalW, (h - 80) / totalH);

    const cx = w / 2;
    const groundY = h * 0.75;
    const deckTopY = groundY - params.pier_height_m * scale;

    // Ground
    ctx.fillStyle = BRIDGE_COLORS.ground;
    ctx.fillRect(0, groundY, w, h - groundY);
    ctx.strokeStyle = '#5a4a3a';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, groundY);
    ctx.lineTo(w, groundY);
    ctx.stroke();

    // Pier (at station midpoint)
    const pierW = 0.8 * scale;
    const pierH = params.pier_height_m * scale;
    ctx.fillStyle = '#999999';
    ctx.fillRect(cx - pierW / 2, deckTopY, pierW, pierH);
    ctx.strokeStyle = '#777';
    ctx.strokeRect(cx - pierW / 2, deckTopY, pierW, pierH);

    // Deck slab
    const deckW = params.deck_width_m * scale;
    const deckH = params.deck_depth_m * scale;
    ctx.fillStyle = BRIDGE_COLORS.deck;
    ctx.fillRect(cx - deckW / 2, deckTopY - deckH, deckW, deckH);
    ctx.strokeStyle = '#aaa';
    ctx.lineWidth = 1;
    ctx.strokeRect(cx - deckW / 2, deckTopY - deckH, deckW, deckH);

    // Girders
    const girderH = params.girder_depth_m * scale;
    const girderW = 0.3 * scale;
    const gCount = params.girder_count;
    for (let g = 0; g < gCount; g++) {
      const gx = cx - deckW / 2 + (g + 0.5) * (deckW / gCount);
      ctx.fillStyle = BRIDGE_COLORS.girder;
      ctx.fillRect(gx - girderW / 2, deckTopY, girderW, girderH);
      ctx.strokeStyle = '#555';
      ctx.strokeRect(gx - girderW / 2, deckTopY, girderW, girderH);
    }

    // Barriers
    const barrierH = params.barrier_height_m * scale;
    const barrierW = (params.barrier_type === 'jersey' ? 0.4 : 0.15) * scale;
    ctx.fillStyle = BRIDGE_COLORS.barrier;
    // Left
    ctx.fillRect(cx - deckW / 2, deckTopY - deckH - barrierH, barrierW, barrierH);
    // Right
    ctx.fillRect(cx + deckW / 2 - barrierW, deckTopY - deckH - barrierH, barrierW, barrierH);

    // Dimensions
    ctx.fillStyle = '#888';
    ctx.font = '11px Inter, sans-serif';
    ctx.textAlign = 'center';

    // Deck width
    const dimY = deckTopY - deckH - barrierH - 20;
    ctx.beginPath();
    ctx.moveTo(cx - deckW / 2, dimY);
    ctx.lineTo(cx + deckW / 2, dimY);
    ctx.strokeStyle = '#c8a55c';
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillStyle = '#c8a55c';
    ctx.fillText(`${params.deck_width_m.toFixed(1)}m`, cx, dimY - 4);

    // Pier height
    const dimX = cx + deckW / 2 + 20;
    ctx.beginPath();
    ctx.moveTo(dimX, deckTopY);
    ctx.lineTo(dimX, groundY);
    ctx.stroke();
    ctx.save();
    ctx.translate(dimX + 14, (deckTopY + groundY) / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(`${params.pier_height_m.toFixed(1)}m`, 0, 0);
    ctx.restore();

    // Station label
    ctx.fillStyle = '#666';
    ctx.font = '10px Inter, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(`Station: ${station}%`, 12, 20);

  }, [params, station]);

  return (
    <div className="cross-section-view">
      <canvas ref={canvasRef} className="cross-section-canvas" />
      <div className="cross-section-controls">
        <span className="cross-section-label">Station</span>
        <input
          type="range"
          className="cross-section-slider"
          min={0}
          max={100}
          value={station}
          onChange={(e) => setStation(Number(e.target.value))}
        />
        <span className="cross-section-label">{station}%</span>
      </div>
    </div>
  );
}
