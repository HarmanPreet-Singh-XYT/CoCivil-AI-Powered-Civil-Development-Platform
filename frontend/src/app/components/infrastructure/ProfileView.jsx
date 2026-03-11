import { useRef, useEffect, useMemo } from 'react';

const PIPE_COLORS = {
  water: '#2277bb',
  sanitary: '#886644',
  storm: '#44aa66',
  gas: '#ddaa22',
};

export default function ProfileView({ segments, alignment }) {
  const canvasRef = useRef(null);

  const profileData = useMemo(() => {
    if (!segments?.length) return null;

    // Compute chainage (cumulative horizontal distance) and invert elevations
    let chainage = 0;
    const points = [];

    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      const startElev = seg.invert_elevation ?? (seg.start?.[2] || 0);
      const endElev = seg.end_invert_elevation ?? startElev - (seg.length_m || 10) * (seg.slope_pct || 1) / 100;

      if (i === 0) {
        points.push({ chainage: 0, elevation: startElev, type: seg.pipe_type || 'water' });
      }

      chainage += seg.length_m || 10;
      points.push({ chainage, elevation: endElev, type: seg.pipe_type || 'water' });
    }

    return points;
  }, [segments]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !profileData?.length) return;

    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const w = rect.width;
    const h = rect.height;
    const pad = { top: 30, right: 40, bottom: 40, left: 60 };

    // Clear
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, w, h);

    if (profileData.length < 2) return;

    // Ranges
    const chainages = profileData.map((p) => p.chainage);
    const elevations = profileData.map((p) => p.elevation);
    const minCh = Math.min(...chainages);
    const maxCh = Math.max(...chainages);
    const minEl = Math.min(...elevations) - 1;
    const maxEl = Math.max(...elevations) + 1;

    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    const toX = (ch) => pad.left + ((ch - minCh) / (maxCh - minCh || 1)) * plotW;
    const toY = (el) => pad.top + plotH - ((el - minEl) / (maxEl - minEl || 1)) * plotH;

    // Grid
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 0.5;
    const gridSteps = 5;
    for (let i = 0; i <= gridSteps; i++) {
      const y = pad.top + (i / gridSteps) * plotH;
      ctx.beginPath();
      ctx.moveTo(pad.left, y);
      ctx.lineTo(w - pad.right, y);
      ctx.stroke();

      const elev = maxEl - (i / gridSteps) * (maxEl - minEl);
      ctx.fillStyle = '#666';
      ctx.font = '10px Inter, sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(elev.toFixed(1), pad.left - 6, y + 4);
    }

    // X-axis labels
    for (let i = 0; i <= gridSteps; i++) {
      const ch = minCh + (i / gridSteps) * (maxCh - minCh);
      const x = toX(ch);
      ctx.fillStyle = '#666';
      ctx.textAlign = 'center';
      ctx.fillText(ch.toFixed(0) + 'm', x, h - pad.bottom + 16);
    }

    // Axis labels
    ctx.save();
    ctx.fillStyle = '#888';
    ctx.font = '11px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Chainage (m)', w / 2, h - 6);
    ctx.translate(14, h / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText('Elevation (m)', 0, 0);
    ctx.restore();

    // Profile line
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < profileData.length; i++) {
      const p = profileData[i];
      const x = toX(p.chainage);
      const y = toY(p.elevation);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = PIPE_COLORS[profileData[0]?.type] || PIPE_COLORS.water;
    ctx.stroke();

    // Points
    for (const p of profileData) {
      ctx.beginPath();
      ctx.arc(toX(p.chainage), toY(p.elevation), 4, 0, Math.PI * 2);
      ctx.fillStyle = PIPE_COLORS[p.type] || PIPE_COLORS.water;
      ctx.fill();
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Ground line (simplified — flat at max elevation + 1)
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = '#555';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad.left, toY(maxEl));
    ctx.lineTo(w - pad.right, toY(maxEl));
    ctx.stroke();
    ctx.setLineDash([]);

  }, [profileData]);

  return (
    <div className="profile-view">
      <canvas ref={canvasRef} className="profile-canvas" />
      <div className="profile-legend">
        {Object.entries(PIPE_COLORS).map(([type, color]) => (
          <div key={type} className="profile-legend-item">
            <div className="profile-legend-swatch" style={{ backgroundColor: color }} />
            <span>{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
