import axios from 'axios';
import type {
  FontProject,
  CreateFontRequest,
  AgentRunRequest,
  AgentRunResponse,
  ExportRequest,
  ExportResult,
  Glyph,
  FontMetrics,
} from './types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const http = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Mock Data ────────────────────────────────────────────────────────────────

const DEFAULT_METRICS: FontMetrics = {
  unitsPerEm: 1000,
  ascender: 800,
  descender: -200,
  capHeight: 700,
  xHeight: 500,
  lineGap: 0,
};

function makeGlyph(char: string, unicode: number): Glyph {
  return {
    id: `glyph-${unicode}`,
    name: `uni${unicode.toString(16).toUpperCase().padStart(4, '0')}`,
    unicode,
    char,
    width: 600,
    height: 700,
    lsb: 80,
    rsb: 80,
    contours: [],
  };
}

const MOCK_PROJECTS: FontProject[] = [
  {
    id: 'proj-1',
    name: 'Geometric Sans',
    description: 'A clean, geometric sans-serif typeface',
    createdAt: '2024-01-15T10:00:00Z',
    updatedAt: '2024-02-20T15:30:00Z',
    glyphCount: 52,
    metrics: DEFAULT_METRICS,
    glyphs: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').map((c, i) =>
      makeGlyph(c, 65 + i)
    ),
    tags: ['sans-serif', 'geometric'],
  },
  {
    id: 'proj-2',
    name: 'Humanist Serif',
    description: 'Elegant humanist serif with optical corrections',
    createdAt: '2024-02-01T09:00:00Z',
    updatedAt: '2024-03-01T11:00:00Z',
    glyphCount: 78,
    metrics: { ...DEFAULT_METRICS, ascender: 850, descender: -250 },
    glyphs: 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'.split('').map((c) =>
      makeGlyph(c, c.charCodeAt(0))
    ),
    tags: ['serif', 'humanist'],
  },
  {
    id: 'proj-3',
    name: 'Mono Code',
    description: 'Monospaced font for developers',
    createdAt: '2024-03-01T08:00:00Z',
    updatedAt: '2024-03-05T17:00:00Z',
    glyphCount: 95,
    metrics: DEFAULT_METRICS,
    glyphs: [],
    tags: ['monospace', 'code'],
  },
];

// ── API Client ───────────────────────────────────────────────────────────────

async function withMockFallback<T>(
  apiCall: () => Promise<T>,
  mockData: T
): Promise<T> {
  try {
    return await apiCall();
  } catch {
    console.warn('[API] Request failed, using mock data');
    return mockData;
  }
}

export const fontApi = {
  listFonts: (): Promise<FontProject[]> =>
    withMockFallback(
      async () => {
        const res = await http.get<FontProject[]>('/api/fonts');
        return res.data;
      },
      MOCK_PROJECTS
    ),

  getFont: (id: string): Promise<FontProject> =>
    withMockFallback(
      async () => {
        const res = await http.get<FontProject>(`/api/fonts/${id}`);
        return res.data;
      },
      MOCK_PROJECTS.find((p) => p.id === id) ?? MOCK_PROJECTS[0]
    ),

  createFont: (data: CreateFontRequest): Promise<FontProject> =>
    withMockFallback(
      async () => {
        const res = await http.post<FontProject>('/api/fonts', data);
        return res.data;
      },
      {
        id: `proj-${Date.now()}`,
        name: data.name,
        description: data.description ?? '',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        glyphCount: 0,
        metrics: { ...DEFAULT_METRICS, ...data.metrics },
        glyphs: [],
        tags: [],
      }
    ),

  deleteFont: (id: string): Promise<void> =>
    withMockFallback(
      async () => {
        await http.delete(`/api/fonts/${id}`);
      },
      undefined
    ),
};

export const agentApi = {
  runAgent: (data: AgentRunRequest): Promise<AgentRunResponse> =>
    withMockFallback(
      async () => {
        const res = await http.post<AgentRunResponse>('/api/agents/run', data);
        return res.data;
      },
      {
        id: `agent-${Date.now()}`,
        status: 'completed' as const,
        prompt: data.prompt,
        result: {
          glyphs: [],
          message: `Mock result for: "${data.prompt}". In production this would generate actual glyph data.`,
          confidence: 0.87,
        },
        createdAt: new Date().toISOString(),
      }
    ),
};

export const exportApi = {
  exportFont: (data: ExportRequest): Promise<ExportResult> =>
    withMockFallback(
      async () => {
        const res = await http.post<ExportResult>(
          `/api/fonts/${data.fontId}/export`,
          data
        );
        return res.data;
      },
      {
        id: `export-${Date.now()}`,
        fontId: data.fontId,
        format: data.format,
        url: `/downloads/mock-font.${data.format}`,
        size: Math.floor(Math.random() * 500000) + 50000,
        createdAt: new Date().toISOString(),
        status: 'completed' as const,
        progress: 100,
      }
    ),
};
