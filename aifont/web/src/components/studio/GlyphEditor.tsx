import { useRef, useState, useCallback, useEffect } from 'react';
import type { Glyph, GlyphPoint, GlyphContour, Tool } from '../../api/types';

interface GlyphEditorProps {
  glyph: Glyph | null;
  tool: Tool;
  onChange?: (glyph: Glyph) => void;
}

const CANVAS_W = 600;
const CANVAS_H = 800;
const GRID_SIZE = 50;
const UNITS = 1000;
const SCALE = CANVAS_H / UNITS;

function unitToCanvas(y: number): number {
  return CANVAS_H - (y + 200) * SCALE;
}

function canvasToUnit(cy: number): number {
  return (CANVAS_H - cy) / SCALE - 200;
}

function xUnitToCanvas(x: number): number {
  return (x + 80) * SCALE;
}

function xCanvasToUnit(cx: number): number {
  return cx / SCALE - 80;
}

export function GlyphEditor({ glyph, tool, onChange }: GlyphEditorProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [contours, setContours] = useState<GlyphContour[]>(glyph?.contours ?? []);
  const [activeContourIdx, setActiveContourIdx] = useState<number>(-1);
  const [selectedPointIdx, setSelectedPointIdx] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    if (glyph) setContours(glyph.contours);
  }, [glyph]);

  const getSVGPoint = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const rect = svg.getBoundingClientRect();
    const scaleX = CANVAS_W / rect.width;
    const scaleY = CANVAS_H / rect.height;
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  }, []);

  const handleClick = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (tool !== 'pen') return;
      const pt = getSVGPoint(e);
      const newPoint: GlyphPoint = {
        x: xCanvasToUnit(pt.x),
        y: canvasToUnit(pt.y),
        type: 'on',
      };

      setContours((prev) => {
        const updated = [...prev];
        if (activeContourIdx < 0 || activeContourIdx >= updated.length) {
          const newContour: GlyphContour = { points: [newPoint], closed: false };
          setActiveContourIdx(updated.length);
          return [...updated, newContour];
        }
        updated[activeContourIdx] = {
          ...updated[activeContourIdx],
          points: [...updated[activeContourIdx].points, newPoint],
        };
        return updated;
      });
    },
    [tool, getSVGPoint, activeContourIdx]
  );

  const handlePointMouseDown = useCallback(
    (e: React.MouseEvent, contourIdx: number, pointIdx: number) => {
      if (tool !== 'select') return;
      e.stopPropagation();
      setActiveContourIdx(contourIdx);
      setSelectedPointIdx(pointIdx);
      setIsDragging(true);
    },
    [tool]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!isDragging || selectedPointIdx === null || activeContourIdx < 0) return;
      const pt = getSVGPoint(e);
      setContours((prev) => {
        const updated = prev.map((c, ci) => {
          if (ci !== activeContourIdx) return c;
          const pts = c.points.map((p, pi) => {
            if (pi !== selectedPointIdx) return p;
            return { ...p, x: xCanvasToUnit(pt.x), y: canvasToUnit(pt.y) };
          });
          return { ...c, points: pts };
        });
        return updated;
      });
    },
    [isDragging, selectedPointIdx, activeContourIdx, getSVGPoint]
  );

  const handleMouseUp = useCallback(() => {
    if (isDragging && glyph && onChange) {
      onChange({ ...glyph, contours });
    }
    setIsDragging(false);
  }, [isDragging, glyph, contours, onChange]);

  // Build SVG path from contour
  const buildPath = (contour: GlyphContour): string => {
    const pts = contour.points;
    if (pts.length === 0) return '';
    let d = `M ${xUnitToCanvas(pts[0].x)} ${unitToCanvas(pts[0].y)}`;
    for (let i = 1; i < pts.length; i++) {
      const p = pts[i];
      const prev = pts[i - 1];
      if (prev.type === 'off') {
        d += ` Q ${xUnitToCanvas(prev.x)} ${unitToCanvas(prev.y)} ${xUnitToCanvas(p.x)} ${unitToCanvas(p.y)}`;
      } else {
        d += ` L ${xUnitToCanvas(p.x)} ${unitToCanvas(p.y)}`;
      }
    }
    if (contour.closed && pts.length > 1) d += ' Z';
    return d;
  };

  // Guidelines
  const baseline = unitToCanvas(0);
  const xheight = unitToCanvas(500);
  const capheight = unitToCanvas(700);
  const descender = unitToCanvas(-200);
  const ascender = unitToCanvas(800);

  return (
    <div className="relative flex h-full w-full items-center justify-center bg-gray-950">
      <div className="absolute top-3 right-3 flex gap-2 z-10">
        <button
          onClick={() => setZoom((z) => Math.min(z + 0.25, 3))}
          className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-300 hover:bg-gray-700"
        >+</button>
        <span className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-400">
          {Math.round(zoom * 100)}%
        </span>
        <button
          onClick={() => setZoom((z) => Math.max(z - 0.25, 0.25))}
          className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-300 hover:bg-gray-700"
        >−</button>
      </div>

      {!glyph ? (
        <div className="flex flex-col items-center gap-3 text-gray-600">
          <svg className="h-16 w-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p className="text-sm">Select a glyph to edit</p>
        </div>
      ) : (
        <svg
          ref={svgRef}
          viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
          width={CANVAS_W * zoom}
          height={CANVAS_H * zoom}
          className={`glyph-canvas ${tool === 'select' ? 'select-mode' : ''}`}
          onClick={handleClick}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          style={{ maxWidth: '100%', maxHeight: '100%' }}
          data-testid="glyph-canvas"
        >
          {/* Grid */}
          <defs>
            <pattern id="grid" width={GRID_SIZE} height={GRID_SIZE} patternUnits="userSpaceOnUse">
              <path d={`M ${GRID_SIZE} 0 L 0 0 0 ${GRID_SIZE}`} fill="none" stroke="#1f2937" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width={CANVAS_W} height={CANVAS_H} fill="#0d1117" />
          <rect width={CANVAS_W} height={CANVAS_H} fill="url(#grid)" />

          {/* Guidelines */}
          <line x1={0} y1={ascender} x2={CANVAS_W} y2={ascender} stroke="#1e3a5f" strokeWidth={1} strokeDasharray="4 4" />
          <line x1={0} y1={capheight} x2={CANVAS_W} y2={capheight} stroke="#1e3a5f" strokeWidth={1} strokeDasharray="4 4" />
          <line x1={0} y1={xheight} x2={CANVAS_W} y2={xheight} stroke="#1e3a5f" strokeWidth={1} strokeDasharray="4 4" />
          <line x1={0} y1={baseline} x2={CANVAS_W} y2={baseline} stroke="#2563eb" strokeWidth={1.5} />
          <line x1={0} y1={descender} x2={CANVAS_W} y2={descender} stroke="#1e3a5f" strokeWidth={1} strokeDasharray="4 4" />

          {/* Guideline labels */}
          <text x={4} y={ascender - 3} fontSize={9} fill="#374151">ascender</text>
          <text x={4} y={capheight - 3} fontSize={9} fill="#374151">cap height</text>
          <text x={4} y={xheight - 3} fontSize={9} fill="#374151">x-height</text>
          <text x={4} y={baseline - 3} fontSize={9} fill="#3b82f6">baseline</text>
          <text x={4} y={descender - 3} fontSize={9} fill="#374151">descender</text>

          {/* Glyph paths */}
          {contours.map((contour, ci) => (
            <g key={ci}>
              <path
                d={buildPath(contour)}
                fill={contour.closed ? 'rgba(99,102,241,0.15)' : 'none'}
                stroke={ci === activeContourIdx ? '#818cf8' : '#4f46e5'}
                strokeWidth={1.5}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {/* Control points */}
              {contour.points.map((pt, pi) => {
                const cx = xUnitToCanvas(pt.x);
                const cy = unitToCanvas(pt.y);
                const isSelected = ci === activeContourIdx && pi === selectedPointIdx;
                return pt.type === 'on' ? (
                  <rect
                    key={pi}
                    x={cx - 4}
                    y={cy - 4}
                    width={8}
                    height={8}
                    fill={isSelected ? '#818cf8' : '#374151'}
                    stroke={isSelected ? '#c7d2fe' : '#6366f1'}
                    strokeWidth={1.5}
                    style={{ cursor: tool === 'select' ? 'move' : 'default' }}
                    onMouseDown={(e) => handlePointMouseDown(e as unknown as React.MouseEvent, ci, pi)}
                  />
                ) : (
                  <circle
                    key={pi}
                    cx={cx}
                    cy={cy}
                    r={3}
                    fill={isSelected ? '#f59e0b' : '#92400e'}
                    stroke={isSelected ? '#fcd34d' : '#d97706'}
                    strokeWidth={1}
                    style={{ cursor: tool === 'select' ? 'move' : 'default' }}
                    onMouseDown={(e) => handlePointMouseDown(e as unknown as React.MouseEvent, ci, pi)}
                  />
                );
              })}
            </g>
          ))}
        </svg>
      )}
    </div>
  );
}
