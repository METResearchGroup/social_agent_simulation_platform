# Database schema (Alembic migrations @ head)

## Mermaid Diagram

```mermaid
erDiagram
  agent {
    TEXT agent_id PK
    TEXT handle
    TEXT persona_source
    TEXT display_name
    TEXT created_at
    TEXT updated_at
  }
  agent_bios {
    TEXT handle PK
    TEXT generated_bio
    TEXT created_at
  }
  agent_persona_bios {
    TEXT id PK
    TEXT agent_id FK
    TEXT persona_bio
    TEXT persona_bio_source
    TEXT created_at
    TEXT updated_at
  }
  alembic_version {
    VARCHAR(32) version_num PK
  }
  bluesky_feed_posts {
    TEXT uri PK
    TEXT author_display_name
    TEXT author_handle
    TEXT text
    INTEGER bookmark_count
    INTEGER like_count
    INTEGER quote_count
    INTEGER reply_count
    INTEGER repost_count
    TEXT created_at
  }
  bluesky_profiles {
    TEXT handle PK
    TEXT did
    TEXT display_name
    TEXT bio
    INTEGER followers_count
    INTEGER follows_count
    INTEGER posts_count
  }
  generated_feeds {
    TEXT feed_id
    TEXT run_id PK FK
    INTEGER turn_number PK
    TEXT agent_handle PK
    TEXT post_uris
    TEXT created_at
  }
  run_metrics {
    TEXT run_id PK FK
    TEXT metrics
    TEXT created_at
  }
  runs {
    TEXT run_id PK
    TEXT created_at
    INTEGER total_turns
    INTEGER total_agents
    TEXT started_at
    TEXT status
    TEXT completed_at
    TEXT feed_algorithm
    TEXT metric_keys
  }
  turn_metadata {
    TEXT run_id PK FK
    INTEGER turn_number PK
    TEXT total_actions
    TEXT created_at
  }
  turn_metrics {
    TEXT run_id PK FK
    INTEGER turn_number PK
    TEXT metrics
    TEXT created_at
  }
  user_agent_profile_metadata {
    TEXT id PK
    TEXT agent_id FK
    INTEGER followers_count
    INTEGER follows_count
    INTEGER posts_count
    TEXT created_at
    TEXT updated_at
  }
  agent ||--o{ agent_persona_bios : "fk_agent_persona_bios_agent_id (agent_id)"
  agent ||--o{ user_agent_profile_metadata : "fk_user_agent_profile_metadata_agent_id (agent_id)"
  runs ||--o{ generated_feeds : "fk_generated_feeds_run_id (run_id)"
  runs ||--o{ run_metrics : "fk_run_metrics_run_id (run_id)"
  runs ||--o{ turn_metadata : "fk_turn_metadata_run_id (run_id)"
  runs ||--o{ turn_metrics : "fk_turn_metrics_run_id (run_id)"
```

This documentation is generated from a fresh SQLite database after applying Alembic migrations to `head`.

## `agent`

### Columns (`agent`)

| name | type | nullable | default | pk |
| --- | --- | --- | --- | --- |
| `agent_id` | `TEXT` | no | `` | `1` |
| `handle` | `TEXT` | no | `` | `` |
| `persona_source` | `TEXT` | no | `` | `` |
| `display_name` | `TEXT` | no | `` | `` |
| `created_at` | `TEXT` | no | `` | `` |
| `updated_at` | `TEXT` | no | `` | `` |

### Primary key (`agent`)

- Name: `pk_agent`
- Columns: `agent_id`

### Unique constraints (`agent`)

- `uq_agent_handle`: `handle`

### Referenced by (`agent`)

- `agent_persona_bios` `fk_agent_persona_bios_agent_id`: `agent_id` → `agent_id`
- `user_agent_profile_metadata` `fk_user_agent_profile_metadata_agent_id`: `agent_id` → `agent_id`

## `agent_bios`

### Columns (`agent_bios`)

| name | type | nullable | default | pk |
| --- | --- | --- | --- | --- |
| `handle` | `TEXT` | no | `` | `1` |
| `generated_bio` | `TEXT` | no | `` | `` |
| `created_at` | `TEXT` | no | `` | `` |

### Primary key (`agent_bios`)

- Name: (none)
- Columns: `handle`

## `agent_persona_bios`

### Columns (`agent_persona_bios`)

| name | type | nullable | default | pk |
| --- | --- | --- | --- | --- |
| `id` | `TEXT` | no | `` | `1` |
| `agent_id` | `TEXT` | no | `` | `` |
| `persona_bio` | `TEXT` | no | `` | `` |
| `persona_bio_source` | `TEXT` | no | `` | `` |
| `created_at` | `TEXT` | no | `` | `` |
| `updated_at` | `TEXT` | no | `` | `` |

### Primary key (`agent_persona_bios`)

- Name: `pk_agent_persona_bios`
- Columns: `id`

### Foreign keys (`agent_persona_bios`)

- `fk_agent_persona_bios_agent_id`: `agent_id` → `agent(agent_id)`

### Indexes (`agent_persona_bios`)

- `idx_agent_persona_bios_agent_id_created_at`: `agent_id`, `created_at`

## `alembic_version`

### Columns (`alembic_version`)

| name | type | nullable | default | pk |
| --- | --- | --- | --- | --- |
| `version_num` | `VARCHAR(32)` | no | `` | `1` |

### Primary key (`alembic_version`)

- Name: `alembic_version_pkc`
- Columns: `version_num`

## `bluesky_feed_posts`

### Columns (`bluesky_feed_posts`)

| name | type | nullable | default | pk |
| --- | --- | --- | --- | --- |
| `uri` | `TEXT` | no | `` | `1` |
| `author_display_name` | `TEXT` | no | `` | `` |
| `author_handle` | `TEXT` | no | `` | `` |
| `text` | `TEXT` | no | `` | `` |
| `bookmark_count` | `INTEGER` | no | `` | `` |
| `like_count` | `INTEGER` | no | `` | `` |
| `quote_count` | `INTEGER` | no | `` | `` |
| `reply_count` | `INTEGER` | no | `` | `` |
| `repost_count` | `INTEGER` | no | `` | `` |
| `created_at` | `TEXT` | no | `` | `` |

### Primary key (`bluesky_feed_posts`)

- Name: (none)
- Columns: `uri`

### Indexes (`bluesky_feed_posts`)

- `idx_bluesky_feed_posts_author_handle`: `author_handle`

## `bluesky_profiles`

### Columns (`bluesky_profiles`)

| name | type | nullable | default | pk |
| --- | --- | --- | --- | --- |
| `handle` | `TEXT` | no | `` | `1` |
| `did` | `TEXT` | no | `` | `` |
| `display_name` | `TEXT` | no | `` | `` |
| `bio` | `TEXT` | no | `` | `` |
| `followers_count` | `INTEGER` | no | `` | `` |
| `follows_count` | `INTEGER` | no | `` | `` |
| `posts_count` | `INTEGER` | no | `` | `` |

### Primary key (`bluesky_profiles`)

- Name: (none)
- Columns: `handle`

## `generated_feeds`

### Columns (`generated_feeds`)

| name | type | nullable | default | pk |
| --- | --- | --- | --- | --- |
| `feed_id` | `TEXT` | no | `` | `` |
| `run_id` | `TEXT` | no | `` | `2` |
| `turn_number` | `INTEGER` | no | `` | `3` |
| `agent_handle` | `TEXT` | no | `` | `1` |
| `post_uris` | `TEXT` | no | `` | `` |
| `created_at` | `TEXT` | no | `` | `` |

### Primary key (`generated_feeds`)

- Name: `pk_generated_feeds`
- Columns: `agent_handle`, `run_id`, `turn_number`

### Foreign keys (`generated_feeds`)

- `fk_generated_feeds_run_id`: `run_id` → `runs(run_id)`

## `run_metrics`

### Columns (`run_metrics`)

| name | type | nullable | default | pk |
| --- | --- | --- | --- | --- |
| `run_id` | `TEXT` | no | `` | `1` |
| `metrics` | `TEXT` | no | `` | `` |
| `created_at` | `TEXT` | no | `` | `` |

### Primary key (`run_metrics`)

- Name: `pk_run_metrics`
- Columns: `run_id`

### Foreign keys (`run_metrics`)

- `fk_run_metrics_run_id`: `run_id` → `runs(run_id)`

## `runs`

### Columns (`runs`)

| name | type | nullable | default | pk |
| --- | --- | --- | --- | --- |
| `run_id` | `TEXT` | no | `` | `1` |
| `created_at` | `TEXT` | no | `` | `` |
| `total_turns` | `INTEGER` | no | `` | `` |
| `total_agents` | `INTEGER` | no | `` | `` |
| `started_at` | `TEXT` | no | `` | `` |
| `status` | `TEXT` | no | `` | `` |
| `completed_at` | `TEXT` | yes | `` | `` |
| `feed_algorithm` | `TEXT` | no | `'chronological'` | `` |
| `metric_keys` | `TEXT` | yes | `` | `` |

### Primary key (`runs`)

- Name: (none)
- Columns: `run_id`

### Indexes (`runs`)

- `idx_runs_created_at`: `created_at`
- `idx_runs_status`: `status`

### Check constraints (`runs`)

- `ck_runs_completed_at_consistent`: `((status = 'completed' AND completed_at IS NOT NULL AND completed_at >= started_at) OR (status != 'completed' AND completed_at IS NULL))`
- `ck_runs_status_valid`: `status IN ('running', 'completed', 'failed')`
- `ck_runs_total_agents_gt_0`: `total_agents > 0`
- `ck_runs_total_turns_gt_0`: `total_turns > 0`

### Referenced by (`runs`)

- `generated_feeds` `fk_generated_feeds_run_id`: `run_id` → `run_id`
- `run_metrics` `fk_run_metrics_run_id`: `run_id` → `run_id`
- `turn_metadata` `fk_turn_metadata_run_id`: `run_id` → `run_id`
- `turn_metrics` `fk_turn_metrics_run_id`: `run_id` → `run_id`

## `turn_metadata`

### Columns (`turn_metadata`)

| name | type | nullable | default | pk |
| --- | --- | --- | --- | --- |
| `run_id` | `TEXT` | no | `` | `1` |
| `turn_number` | `INTEGER` | no | `` | `2` |
| `total_actions` | `TEXT` | no | `` | `` |
| `created_at` | `TEXT` | no | `` | `` |

### Primary key (`turn_metadata`)

- Name: `pk_turn_metadata`
- Columns: `run_id`, `turn_number`

### Foreign keys (`turn_metadata`)

- `fk_turn_metadata_run_id`: `run_id` → `runs(run_id)`

### Indexes (`turn_metadata`)

- `idx_turn_metadata_run_id`: `run_id`

### Check constraints (`turn_metadata`)

- `ck_turn_metadata_turn_number_gte_0`: `turn_number >= 0`

## `turn_metrics`

### Columns (`turn_metrics`)

| name | type | nullable | default | pk |
| --- | --- | --- | --- | --- |
| `run_id` | `TEXT` | no | `` | `1` |
| `turn_number` | `INTEGER` | no | `` | `2` |
| `metrics` | `TEXT` | no | `` | `` |
| `created_at` | `TEXT` | no | `` | `` |

### Primary key (`turn_metrics`)

- Name: `pk_turn_metrics`
- Columns: `run_id`, `turn_number`

### Foreign keys (`turn_metrics`)

- `fk_turn_metrics_run_id`: `run_id` → `runs(run_id)`

### Indexes (`turn_metrics`)

- `idx_turn_metrics_run_id`: `run_id`

### Check constraints (`turn_metrics`)

- `ck_turn_metrics_turn_number_gte_0`: `turn_number >= 0`

## `user_agent_profile_metadata`

### Columns (`user_agent_profile_metadata`)

| name | type | nullable | default | pk |
| --- | --- | --- | --- | --- |
| `id` | `TEXT` | no | `` | `1` |
| `agent_id` | `TEXT` | no | `` | `` |
| `followers_count` | `INTEGER` | no | `` | `` |
| `follows_count` | `INTEGER` | no | `` | `` |
| `posts_count` | `INTEGER` | no | `` | `` |
| `created_at` | `TEXT` | no | `` | `` |
| `updated_at` | `TEXT` | no | `` | `` |

### Primary key (`user_agent_profile_metadata`)

- Name: `pk_user_agent_profile_metadata`
- Columns: `id`

### Foreign keys (`user_agent_profile_metadata`)

- `fk_user_agent_profile_metadata_agent_id`: `agent_id` → `agent(agent_id)`

### Unique constraints (`user_agent_profile_metadata`)

- `uq_user_agent_profile_metadata_agent_id`: `agent_id`
