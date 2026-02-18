import { ApiError, Run, Turn, Feed, AgentAction } from '@/types';

const DEFAULT_SIMULATION_API_BASE_URL: string = 'http://localhost:8000/v1';
const SIMULATION_API_BASE_URL: string = (
  process.env.NEXT_PUBLIC_SIMULATION_API_URL || DEFAULT_SIMULATION_API_BASE_URL
).replace(/\/$/, '');

interface ApiRunListItem {
  run_id: string;
  created_at: string;
  total_turns: number;
  total_agents: number;
  status: Run['status'];
}

interface ApiFeed {
  feed_id: string;
  run_id: string;
  turn_number: number;
  agent_handle: string;
  post_uris: string[];
  created_at: string;
}

interface ApiAgentAction {
  action_id: string;
  agent_handle: string;
  post_uri?: string;
  user_id?: string;
  type: AgentAction['type'];
  created_at: string;
}

interface ApiTurn {
  turn_number: number;
  agent_feeds: Record<string, ApiFeed>;
  agent_actions: Record<string, ApiAgentAction[]>;
}

function buildApiUrl(path: string): string {
  return `${SIMULATION_API_BASE_URL}${path}`;
}

/**
 * Fetches JSON from a URL. Throws ApiError on non-2xx responses.
 * Backend uses { error: { code, message, detail } } for error payloads.
 * On non-JSON or missing error shape, falls back to UNKNOWN_ERROR with raw text in message.
 */
async function fetchJson<T>(url: string): Promise<T> {
  const response: Response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const responseText: string = await response.text();
    let code: string = 'UNKNOWN_ERROR';
    let message: string = responseText || `Request failed (${response.status})`;
    let detail: string | null = null;

    try {
      const data: unknown = JSON.parse(responseText);
      const err =
        data && typeof data === 'object' && data !== null && 'error' in data
          ? (data as { error?: { code?: string; message?: string; detail?: string | null } })
              .error
          : null;
      if (err && typeof err === 'object' && err !== null) {
        code = (typeof err.code === 'string' && err.code) || code;
        message = (typeof err.message === 'string' && err.message) || message;
        detail = typeof err.detail === 'string' ? err.detail : err.detail === null ? null : null;
      }
    } catch {
      // Non-JSON body: use fallback
    }

    throw new ApiError(code, message, detail, response.status);
  }

  return response.json() as Promise<T>;
}

function mapFeed(apiFeed: ApiFeed): Feed {
  return {
    feedId: apiFeed.feed_id,
    runId: apiFeed.run_id,
    turnNumber: apiFeed.turn_number,
    agentHandle: apiFeed.agent_handle,
    postUris: apiFeed.post_uris,
    createdAt: apiFeed.created_at,
  };
}

function mapAction(apiAction: ApiAgentAction): AgentAction {
  return {
    actionId: apiAction.action_id,
    agentHandle: apiAction.agent_handle,
    postUri: apiAction.post_uri,
    userId: apiAction.user_id,
    type: apiAction.type,
    createdAt: apiAction.created_at,
  };
}

function mapTurn(apiTurn: ApiTurn): Turn {
  const agentFeeds: Record<string, Feed> = {};
  const agentActions: Record<string, AgentAction[]> = {};

  Object.entries(apiTurn.agent_feeds).forEach(([agentHandle, apiFeed]) => {
    agentFeeds[agentHandle] = mapFeed(apiFeed);
  });

  Object.entries(apiTurn.agent_actions).forEach(([agentHandle, apiActions]) => {
    agentActions[agentHandle] = apiActions.map(mapAction);
  });

  return {
    turnNumber: apiTurn.turn_number,
    agentFeeds,
    agentActions,
  };
}

export async function getRuns(): Promise<Run[]> {
  const apiRuns: ApiRunListItem[] = await fetchJson<ApiRunListItem[]>(
    buildApiUrl('/simulations/runs'),
  );

  return apiRuns.map((run) => ({
    runId: run.run_id,
    createdAt: run.created_at,
    totalTurns: run.total_turns,
    totalAgents: run.total_agents,
    status: run.status,
  }));
}

export async function getTurnsForRun(runId: string): Promise<Record<string, Turn>> {
  const apiTurnsById: Record<string, ApiTurn> = await fetchJson<Record<string, ApiTurn>>(
    buildApiUrl(`/simulations/runs/${encodeURIComponent(runId)}/turns`),
  );

  const turnsById: Record<string, Turn> = {};
  Object.entries(apiTurnsById).forEach(([turnId, apiTurn]) => {
    turnsById[turnId] = mapTurn(apiTurn);
  });

  return turnsById;
}
