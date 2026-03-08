const PLAN_FROM_UPLOAD_RE = /^(generate|create|build)\s+(?:a\s+)?plan\s+from\s+upload\s*$/i;
const RESPONSE_FROM_UPLOAD_RE = /^(generate|create|build)\s+(?:a\s+)?response\s+from\s+upload\s*$/i;
const PLAN_RE = /^(generate|create|build)\s+(?:a\s+)?plan\s+(?:for\s+)?(.+)$/i;
const EDIT_FLOOR_RE = /^edit\s+floor\s*(?:plan)?$/i;

// Only matches explicit "build/make/create a ..." commands to open the model viewer.
// Once a model is visible, the AI agent decides when to update it — no regex needed.
export const MODEL_RE = /^(build|model|show|make|create)\s+(me\s+)?(?:a\s+)?(.+)$/i;

const FLOOR_RE = /^(?:show|view|go to)\s+floor\s+(\d+)/i;
const VIEW_MODE_RE = /^(?:view|show|switch to)\s+(interior|massing|blueprint|floorplan)/i;
const COMMIT_RE = /^commit(?:\s+(.+))?$/i;
const BRANCH_RE = /^(?:create\s+)?branch\s+(.+)$/i;
const HISTORY_RE = /^(?:show\s+)?history$/i;

// Infrastructure model commands — matched before the generic MODEL_RE
const INFRA_MODEL_RE = /^(design|create|build)\s+.*(\d+)\s*mm\s*(storm|sanitary|water|gas).*/i;
const BRIDGE_MODEL_RE = /^(design|create|build)\s+.*bridge\s*(over|across|spanning)\s+.*/i;

export function parseChatCommand(input) {
  const text = input.trim();
  if (!text) return { type: 'none' };

  // Infrastructure commands — check before generic model match
  const infraMatch = text.match(INFRA_MODEL_RE);
  if (infraMatch) {
    return {
      type: 'infra_model',
      query: text,
      diameter_mm: parseInt(infraMatch[2], 10),
      infraType: infraMatch[3].toLowerCase(),
    };
  }

  const bridgeMatch = text.match(BRIDGE_MODEL_RE);
  if (bridgeMatch) {
    return {
      type: 'bridge_model',
      query: text,
      crossing: bridgeMatch[2].toLowerCase(),
    };
  }

  const floorMatch = text.match(FLOOR_RE);
  if (floorMatch) return { type: 'show_floor', floor: parseInt(floorMatch[1], 10) };

  const viewMatch = text.match(VIEW_MODE_RE);
  if (viewMatch) return { type: 'view_mode', mode: viewMatch[1].toLowerCase() };

  if (COMMIT_RE.test(text)) {
    const m = text.match(COMMIT_RE);
    return { type: 'commit', message: m[1] || null };
  }

  const branchMatchResult = text.match(BRANCH_RE);
  if (branchMatchResult) return { type: 'branch', name: branchMatchResult[1].trim() };

  if (HISTORY_RE.test(text)) return { type: 'show_history' };

  if (EDIT_FLOOR_RE.test(text)) return { type: 'edit_floorplan' };

  if (PLAN_FROM_UPLOAD_RE.test(text)) return { type: 'plan_from_upload' };
  if (RESPONSE_FROM_UPLOAD_RE.test(text)) return { type: 'response_from_upload' };

  const planMatch = text.match(PLAN_RE);
  if (planMatch) {
    return {
      type: 'plan',
      query: (planMatch[2] || text).trim(),
    };
  }

  const modelMatch = text.match(MODEL_RE);
  if (modelMatch) {
    return {
      type: 'model',
      query: text,
    };
  }

  return { type: 'none' };
}
