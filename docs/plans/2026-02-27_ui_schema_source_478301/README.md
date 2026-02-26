# UI schema source plan assets

This folder documents the work that treats the backend OpenAPI spec as the primary source of truth for the UI contracts.

- `scripts/generate-ui-contracts.mts` (in `ui/`) auto-generates the camelCased UI type aliases from `ui/types/api.generated.ts`.
- `ui/types/generated.ts` is the generated output that exports the UI-friendly `Run`, `Agent`, `Post`, and related types.
- `ui/types/index.ts` re-exports those aliases while keeping `ApiError` defined in one place.
- `ui/package.json` ensures the script runs right after the OpenAPI generation step so CI always regenerates the contract aliases.

Run `ui/package.json`'s `generate:api` target to regenerate both OpenAPI data and the derived UI contracts.
