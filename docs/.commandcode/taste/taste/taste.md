# Taste
- Hosting target is AWS; develops locally first (localhost origins/redirects) and defers domain purchase + HTTPS setup until deploy time. Confidence: 0.7
- Auth via Google OAuth (OAuth client ID web app, `/api/auth/google/callback` style redirect). Confidence: 0.5
- Maintains step-by-step setup runbooks as markdown in the repo's `docs/` folder (e.g., `docs/google-oauth-setup.md`) and treats them as the plan of record — when a setup changes, update the existing doc rather than starting over. Confidence: 0.6
- When configuring cloud services, wants exact console paths and literal values (e.g., "APIs & Services → Credentials → Create Credentials → OAuth client ID"), not vague descriptions. Confidence: 0.6
- For new pages/features, plans content first (copy, section structure, what each part says) before UI styling/illustration work — explicitly asked to plan landing-page content before touching visuals. Confidence: 0.9
- University thesis project ("Happynest"); pragmatic, low-cost paths are acceptable — free platform-provided domains fine, purchases deferred until needed for a public deploy. Confidence: 0.5
