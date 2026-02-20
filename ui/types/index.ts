export interface Run {
  runId: string;
  createdAt: string;
  totalTurns: number;
  totalAgents: number;
  status: 'running' | 'completed' | 'failed';
}

export interface Agent {
  handle: string;
  name: string;
  bio: string;
  generatedBio: string;
  followers: number;
  following: number;
  postsCount: number;
}

export interface Post {
  uri: string;
  authorDisplayName: string;
  authorHandle: string;
  text: string;
  bookmarkCount: number;
  likeCount: number;
  quoteCount: number;
  replyCount: number;
  repostCount: number;
  createdAt: string;
}

export interface Feed {
  feedId: string;
  runId: string;
  turnNumber: number;
  agentHandle: string;
  postUris: string[];
  createdAt: string;
}

export interface AgentAction {
  actionId: string;
  agentHandle: string;
  postUri?: string;
  userId?: string;
  type: 'like' | 'comment' | 'follow';
  createdAt: string;
}

export interface Turn {
  turnNumber: number;
  agentFeeds: Record<string, Feed>;
  agentActions: Record<string, AgentAction[]>;
}

/** Maps to FeedAlgorithmSchema (simulation/api/schemas/simulation.py) from GET /v1/simulations/feed-algorithms */
export interface FeedAlgorithm {
  id: string;
  displayName: string;
  description: string;
  configSchema: Record<string, unknown> | null;
}

export interface RunConfig {
  numAgents: number;
  numTurns: number;
  feedAlgorithm?: string;
}

/**
 * Structured API error from backend. Backend uses { error: { code, message, detail } }.
 * Thrown by fetchJson on non-2xx responses.
 */
export class ApiError extends Error {
  readonly code: string;
  readonly message: string;
  readonly detail: string | null;
  readonly status: number;

  constructor(code: string, message: string, detail: string | null, status: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.message = message;
    this.detail = detail;
    this.status = status;
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

