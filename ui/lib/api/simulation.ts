import {
  Agent,
  AgentAction,
  ApiError,
  Feed,
  FeedAlgorithm,
  Post,
  Run,
  RunConfig,
  Turn,
} from '@/types';

const DEFAULT_SIMULATION_API_BASE_URL: string = 'http://localhost:8000/v1';
const SIMULATION_API_BASE_URL: string = (
  process.env.NEXT_PUBLIC_SIMULATION_API_URL || DEFAULT_SIMULATION_API_BASE_URL
).replace(/\/$/, '');

interface ApiAgent {
  handle: string;
  name: string;
  bio: string;
  generated_bio: string;
  followers: number;
  following: number;
  posts_count: number;
}

function mapAgent(apiAgent: ApiAgent): Agent {
  return {
    handle: apiAgent.handle,
    name: apiAgent.name,
    bio: apiAgent.bio,
    generatedBio: apiAgent.generated_bio,
    followers: apiAgent.followers,
    following: apiAgent.following,
    postsCount: apiAgent.posts_count,
  };
}

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

/** API response shape for default config. Matches DefaultConfigSchema. */
interface ApiDefaultConfig {
  num_agents: number;
  num_turns: number;
}

/** API response shape for feed algorithm. Matches FeedAlgorithmSchema. */
interface ApiFeedAlgorithm {
  id: string;
  display_name: string;
  description: string;
  config_schema: Record<string, unknown> | null;
}

/** API response shape for POST /simulations/run. Matches RunResponse. */
interface ApiRunResponse {
  run_id: string;
  status: 'completed' | 'failed';
  num_agents: number;
  num_turns: number;
  turns: unknown[];
  run_metrics?: unknown;
  error?: { code: string; message: string; detail?: string | null };
}

/** API response shape for a post. Matches PostSchema in simulation/api/schemas/simulation.py */
interface ApiPost {
  uri: string;
  author_display_name: string;
  author_handle: string;
  text: string;
  bookmark_count: number;
  like_count: number;
  quote_count: number;
  reply_count: number;
  repost_count: number;
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

/** Token getter for authenticated requests. Set by AuthProvider. */
let authTokenGetter: (() => Promise<string | null>) | null = null;

export function setAuthTokenGetter(
  getter: (() => Promise<string | null>) | null,
): void {
  authTokenGetter = getter;
}

/** Called when a request returns 401. Set by AuthProvider to trigger signOut. */
let onUnauthorized: (() => void) | null = null;

export function setOnUnauthorized(callback: (() => void) | null): void {
  onUnauthorized = callback;
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const token = authTokenGetter ? await authTokenGetter() : null;
  if (token != null && token !== '') {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Handles non-ok response: parses error payload and throws ApiError.
 */
async function handleErrorResponse(response: Response): Promise<never> {
  if (response.status === 401 && onUnauthorized) {
    onUnauthorized();
  }
  const responseText: string = await response.text();
  let code: string = 'UNKNOWN_ERROR';
  let message: string = responseText || `Request failed (${response.status})`;
  let detail: string | null = null;

  try {
    const data: unknown = JSON.parse(responseText);
    const err =
      data && typeof data === 'object' && data !== null && 'error' in data
        ? (data as { error?: { code?: string; message?: string; detail?: string | null } }).error
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

/**
 * Fetches JSON from a URL with GET. Throws ApiError on non-2xx responses.
 * Includes Authorization Bearer token when authTokenGetter is set.
 */
async function fetchJson<T>(url: string): Promise<T> {
  const headers = await getAuthHeaders();
  const response: Response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    await handleErrorResponse(response);
  }

  return response.json() as Promise<T>;
}

/**
 * POSTs JSON to a URL. Throws ApiError on non-2xx responses.
 */
async function fetchPost<TReq, TRes>(url: string, body: TReq): Promise<TRes> {
  const headers = await getAuthHeaders();
  const response: Response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    await handleErrorResponse(response);
  }

  return response.json() as Promise<TRes>;
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

function mapPost(apiPost: ApiPost): Post {
  return {
    uri: apiPost.uri,
    authorDisplayName: apiPost.author_display_name,
    authorHandle: apiPost.author_handle,
    text: apiPost.text,
    bookmarkCount: apiPost.bookmark_count,
    likeCount: apiPost.like_count,
    quoteCount: apiPost.quote_count,
    replyCount: apiPost.reply_count,
    repostCount: apiPost.repost_count,
    createdAt: apiPost.created_at,
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

export async function getDefaultConfig(): Promise<RunConfig> {
  const api: ApiDefaultConfig = await fetchJson<ApiDefaultConfig>(
    buildApiUrl('/simulations/config/default'),
  );
  return {
    numAgents: api.num_agents,
    numTurns: api.num_turns,
    feedAlgorithm: 'chronological',
  };
}

function mapFeedAlgorithm(api: ApiFeedAlgorithm): FeedAlgorithm {
  return {
    id: api.id,
    displayName: api.display_name,
    description: api.description,
    configSchema: api.config_schema,
  };
}

export async function getFeedAlgorithms(): Promise<FeedAlgorithm[]> {
  const api: ApiFeedAlgorithm[] = await fetchJson<ApiFeedAlgorithm[]>(
    buildApiUrl('/simulations/feed-algorithms'),
  );
  return api.map(mapFeedAlgorithm);
}

export async function postRun(config: RunConfig): Promise<Run> {
  const body = {
    num_agents: config.numAgents,
    num_turns: config.numTurns,
    feed_algorithm: config.feedAlgorithm,
  };
  const api: ApiRunResponse = await fetchPost<typeof body, ApiRunResponse>(
    buildApiUrl('/simulations/run'),
    body,
  );
  return {
    runId: api.run_id,
    createdAt: new Date().toISOString(),
    totalTurns: api.num_turns,
    totalAgents: api.num_agents,
    status: api.status,
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

export async function getAgents(): Promise<Agent[]> {
  const apiAgents: ApiAgent[] = await fetchJson<ApiAgent[]>(
    buildApiUrl('/simulations/agents'),
  );
  return apiAgents.map(mapAgent);
}

export async function getPosts(uris?: string[]): Promise<Post[]> {
  const baseUrl: string = buildApiUrl('/simulations/posts');
  const url: string =
    uris != null && uris.length > 0
      ? `${baseUrl}?${uris.map((u) => `uris=${encodeURIComponent(u)}`).join('&')}`
      : baseUrl;
  const apiPosts: ApiPost[] = await fetchJson<ApiPost[]>(url);
  return apiPosts.map(mapPost);
}
