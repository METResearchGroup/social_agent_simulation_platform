# naive_llm (Comment)

One LLM call per `generate()`. Prompts the model with agent handle + post summaries and asks what comments the agent would make. Filters to valid candidates, deduplicates by post_id (first wins), returns sorted `GeneratedComment` objects.
