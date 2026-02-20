# OAuth Setup for agent-simulation-platform

Step-by-step instructions to configure Google and GitHub OAuth in the existing Supabase project. The project `agent-simulation-platform` already exists; this guide configures Auth providers and redirect URLs.

---

## 1. Get your Supabase callback URL

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Open the **agent-simulation-platform** project
3. In the left sidebar: **Authentication** → **Providers**
4. Expand the **GitHub** accordion (or **Google**) and find the **Callback URL** field
5. Copy the URL; it has the form: `https://<PROJECT_REF>.supabase.co/auth/v1/callback`
6. Save this URL; you will use it in both Google and GitHub OAuth app settings

Alternatively, replace `<PROJECT_REF>` with your project reference from **Project Settings** → **General** → **Reference ID**.

---

## 2. Configure Supabase URL settings

Before testing OAuth, configure where users are sent after sign-in.

1. In Supabase: **Authentication** → **URL Configuration**
2. Set **Site URL**:
   - Local dev: `http://localhost:3000`
   - Production: your deployed app URL (e.g. `https://example.com`)
3. Under **Redirect URLs**, add:
   - `http://localhost:3000`
   - `http://localhost:3000/**` (allows any path on localhost, including `/auth/callback`)
   - For production: your app URL and `https://your-domain.com/**`
4. Click **Save**

---

## 3. Google OAuth setup

### 3a. Create Google OAuth credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project (top bar)
3. **APIs & Services** → **Credentials**
4. **Create Credentials** → **OAuth client ID**
5. If prompted, configure the **OAuth consent screen**:
   - **User Type**: External (for public users) or Internal (workspace only)
   - **App name**: e.g. `Agent Simulation Platform`
   - **User support email**: your email
   - **Developer contact**: your email
   - **Scopes** (Data Access): ensure `openid`, `userinfo.profile`, and `userinfo.email` are included; add `openid` manually if missing
   - Save
6. Back in **Credentials**, **Create Credentials** → **OAuth client ID**
7. **Application type**: Web application
8. **Name**: e.g. `Agent Simulation Platform (Supabase)`
9. **Authorized JavaScript origins**:
   - `http://localhost:3000`
   - `https://<PROJECT_REF>.supabase.co` (replace with your project ref)
   - Your production domain if applicable (e.g. `https://example.com`)
10. **Authorized redirect URIs**:
    - Add the Supabase callback URL: `https://<PROJECT_REF>.supabase.co/auth/v1/callback`
    - For local Supabase CLI: `http://127.0.0.1:54321/auth/v1/callback` (only if using `supabase start`)
11. **Create**
12. Copy the **Client ID** and **Client secret** (secret is shown once; store it securely)

### 3b. Add Google credentials to Supabase

1. Supabase: **Authentication** → **Providers**
2. Expand **Google**
3. Toggle **Google Enabled** to ON
4. Paste **Client ID**
5. Paste **Client secret**
6. **Save**

---

## 4. GitHub OAuth setup

### 4a. Register a GitHub OAuth App

1. Go to [GitHub Developer Settings → OAuth Apps](https://github.com/settings/developers)
2. **New OAuth App** (or **Register a new application**)
3. Fill in:
   - **Application name**: e.g. `Agent Simulation Platform`
   - **Homepage URL**: `http://localhost:3000` (local) or your production URL
   - **Authorization callback URL**: `https://<PROJECT_REF>.supabase.co/auth/v1/callback`
   - Leave **Enable Device Flow** unchecked
4. **Register application**
5. On the app page: copy **Client ID**
6. **Generate a new client secret** and copy it (shown once; store securely)

### 4b. Add GitHub credentials to Supabase

1. Supabase: **Authentication** → **Providers**
2. Expand **GitHub**
3. Toggle **GitHub Enabled** to ON
4. Paste **Client ID**
5. Paste **Client secret**
6. **Save**

---

## 5. Verify setup

1. **Environment variables** (in `ui/.env.local`):
   - `NEXT_PUBLIC_SUPABASE_URL` – Project URL from Supabase **Project Settings** → **API**
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` – anon key from the same page
2. Start the UI: `cd ui && npm run dev`
3. Visit `http://localhost:3000` and click **Sign in with Google** or **Sign in with GitHub**
4. Complete the OAuth flow. You will be redirected to `/auth/callback`, which exchanges the code for a session and redirects you to the main simulation UI

---

## References

- [Supabase: Login with Google](https://supabase.com/docs/guides/auth/social-login/auth-google)
- [Supabase: Login with GitHub](https://supabase.com/docs/guides/auth/social-login/auth-github)
- [Supabase: Redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)
