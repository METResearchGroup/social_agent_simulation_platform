# naive_llm (Follow)

One LLM call per `generate()`. Extracts unique authors from candidates (excluding self), keeping the most recent post per author. Prompts with agent handle + author summaries (handle, like_count). Filters response to valid authors, returns sorted `GeneratedFollow` objects.
