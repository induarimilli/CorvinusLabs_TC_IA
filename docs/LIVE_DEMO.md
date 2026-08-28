# Live demo hosting

GitHub stores the repo; it does **not** serve this full stack as a fixed public URL. Use Codespaces for a one-click browser demo, or Render for an always-on link.

## Option A — GitHub Codespaces (from the repo)

1. Open: [Create Codespace](https://codespaces.new/induarimilli/CorvinusLabs_TC_IA)  
   Or on the repo page: **Code → Codespaces → Create codespace on main**.
2. Wait for the post-create script (`make up` / compose). First boot can take several minutes.
3. In the **Ports** tab, open **5173** (App). Optionally open **8000** (API docs).
4. To share with someone else: right-click port **5173** → Port Visibility → **Public**, then copy the `*.app.github.dev` URL.
5. Set the frontend API URL if the UI cannot reach the API:
   ```bash
   # In Codespaces terminal (replace with your forwarded API URL)
   export VITE_API_URL="https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
   cd frontend && npm run dev -- --host
   ```
   Make port **8000** Public as well when sharing.

Demo login uses the four seeded identities (Jordan, Marcus, Dave, Eve).

## Option B — Always-on (Render Blueprint)

1. Sign in at [render.com](https://render.com) → **New → Blueprint**.
2. Connect `induarimilli/CorvinusLabs_TC_IA` and apply [`render.yaml`](../render.yaml).
3. After deploy, set the web service `VITE_API_URL` (or rebuild) to the public API URL, and set API `CORS_ORIGINS` to the web URL.
4. Put the public App URL in the README “Live demo” table.

Free tiers sleep when idle; cold start can take ~30–60s.

## Option C — Local

```bash
make up
# App http://localhost:5173
```

Or `make install && make setup-db` then `make dev-api` / `make dev-web`.
