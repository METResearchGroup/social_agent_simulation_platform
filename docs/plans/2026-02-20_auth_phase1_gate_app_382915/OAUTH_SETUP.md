# OAuth Setup for agent-simulation-platform

Manual steps to configure Google and GitHub OAuth in the existing Supabase project.

1. Supabase Dashboard → Authentication → Providers
2. **Google:** Enable, add Client ID and Client Secret from [Google Cloud Console](https://console.cloud.google.com/apis/credentials) (OAuth 2.0). Redirect URI: `https://<PROJECT_REF>.supabase.co/auth/v1/callback`
3. **GitHub:** Enable, add Client ID and Client Secret from [GitHub Developer Settings](https://github.com/settings/developers). Callback URL: `https://<PROJECT_REF>.supabase.co/auth/v1/callback`
4. In Auth URL Configuration, add `http://localhost:3000` to Redirect URLs for local dev.
