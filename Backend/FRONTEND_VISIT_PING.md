# Frontend addition — visit ping

Hand this to the FE Claude session. Backend now exposes a new endpoint
`POST /api/visit` that should be called once on page load. It triggers a
Telegram notification to the site owner so they get a phone push when
someone visits the site.

## What to add

A small React effect that fires `fetch` once on mount.

### Endpoint

`POST {VITE_CHAT_API_URL}/api/visit`

**Request body** (both fields optional):
```json
{
  "path": "/",
  "referrer": "https://www.linkedin.com/"
}
```

- `path` — `window.location.pathname` (default `"/"`)
- `referrer` — `document.referrer || null`

**Response 200**:
```json
{ "ok": true }
```

Always 200 unless the network fails. Backend throttles per (IP, path) for
1 hour by default, so calling on every page load is safe — duplicates are
dropped server-side. Don't await the response; don't show errors to the
user; if it fails, we just miss one notification.

### Component to add

```tsx
// src/components/VisitPing.tsx
import { useEffect } from "react";

const API_BASE = import.meta.env.VITE_CHAT_API_URL as string | undefined;

export function VisitPing() {
  useEffect(() => {
    if (!API_BASE) return;

    void fetch(`${API_BASE}/api/visit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path: window.location.pathname || "/",
        referrer: document.referrer || null,
      }),
      // Use keepalive so the request survives a fast unload/navigation.
      keepalive: true,
    }).catch(() => {
      // Swallow — a missed ping should never surface to the user.
    });
  }, []);

  return null;
}
```

### Mount once at app root

```tsx
// src/App.tsx (or wherever your root is)
import { VisitPing } from "./components/VisitPing";

export function App() {
  return (
    <>
      <VisitPing />
      {/* …rest of app… */}
    </>
  );
}
```

### If using React Router

If you have client-side routing and want a ping per route change, mount the
component inside the `<Routes>` tree and depend on the path:

```tsx
import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export function VisitPing() {
  const location = useLocation();
  useEffect(() => {
    if (!API_BASE) return;
    void fetch(`${API_BASE}/api/visit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path: location.pathname || "/",
        referrer: document.referrer || null,
      }),
      keepalive: true,
    }).catch(() => {});
  }, [location.pathname]);
  return null;
}
```

## CORS

The backend already accepts `POST /api/visit` from any origin in its
`CORS_ORIGINS` env var (same allowlist as `/api/chat`), so no CORS changes
are needed if `/api/chat` is already working.

## What you DO NOT need to do

- No new dependencies. Plain `fetch` is fine.
- No env vars beyond the existing `VITE_CHAT_API_URL` you already use.
- No backend changes.

## Verify

After deploying:
1. Open the site once.
2. Within ~1–2 seconds, the site owner should get a Telegram message that
   looks like:
   ```
   👀 New visit to vaughneugenio.com
   Path: /
   📍 Brooklyn, New York, US
   🌐 IP: 73.x.x.x
   ↩️ Referrer: direct
   ```
3. Refresh the page within an hour — should NOT trigger a second
   notification (throttled). Wait an hour or test from a different IP to
   see another one.
