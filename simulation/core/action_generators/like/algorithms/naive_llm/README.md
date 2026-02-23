# naive_llm (Like)

One LLM call per `generate()`. Prompts the model with agent handle + post summaries (id, text, author, like_count) and asks which posts the agent would like. Filters response to valid candidate IDs and returns sorted `GeneratedLike` objects.
