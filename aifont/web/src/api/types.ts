// ── Font & Glyph Types ──────────────────────────────────────────────────────

export interface GlyphPoint {
  x: number;
  y: number;
  type: 'on' | 'off'; // on-curve vs off-curve (control point)
}

export interface GlyphContour {
  points: GlyphPoint[];
  closed: boolean;
}

export interface Glyph {
  id: string;
  name: string;
  unicode: number;
  char: string;
  width: number;
  height: number;
  lsb: number; // left side bearing
  rsb: number; // right side bearing
  contours: GlyphContour[];
}

export interface FontMetrics {
  unitsPerEm: number;
  ascender: number;
  descender: number;
  capHeight: number;
  xHeight: number;
  lineGap: number;
}

export interface FontProject {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  updatedAt: string;
  glyphCount: number;
  metrics: FontMetrics;
  glyphs: Glyph[];
  thumbnail?: string;
  tags: string[];
}

// ── API Request/Response Types ───────────────────────────────────────────────

export interface CreateFontRequest {
  name: string;
  description?: string;
  metrics?: Partial<FontMetrics>;
}

export interface AgentRunRequest {
  prompt: string;
  fontId?: string;
  glyphId?: string;
  context?: Record<string, unknown>;
}

export interface AgentRunResponse {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  prompt: string;
  result?: {
    glyphs?: Glyph[];
    message: string;
    confidence: number;
  };
  error?: string;
  createdAt: string;
}

export interface ExportRequest {
  fontId: string;
  format: ExportFormat;
  options?: ExportOptions;
}

export type ExportFormat = 'otf' | 'ttf' | 'woff2' | 'svg';

export interface ExportOptions {
  subset?: string;
  hinting?: boolean;
  optimize?: boolean;
  includeMetadata?: boolean;
}

export interface ExportResult {
  id: string;
  fontId: string;
  format: ExportFormat;
  url: string;
  size: number;
  createdAt: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
}

// ── UI State Types ───────────────────────────────────────────────────────────

export type Tool = 'pen' | 'select' | 'zoom';

export type PreviewMode = 'waterfall' | 'sentence' | 'alphabet';

export interface PromptHistoryItem {
  id: string;
  prompt: string;
  response?: AgentRunResponse;
  timestamp: string;
}
