# Forge deployment health check

**Date:** 2025-02-08  
**Target:** https://zuup-forge.vercel.app/

## Issue (404: NOT_FOUND)

The app was building and deploying as "Ready" on Vercel but returned **404** when visiting the site.

## Root causes

1. **Broken rewrite in root `vercel.json`**  
   All traffic was rewritten to `/api`, but there is no `api` directory or serverless function. Vercel therefore had no handler for requests and returned 404.

2. **Wrong Python path when deploying from repo root**  
   Root `index.py` added only the repo root to `sys.path`. The `forge` package lives under `zuup-forge/forge/`, so the FastAPI app could not be imported when the project root was the repo root.

## Fixes applied

- **Root `vercel.json`**  
  Removed the `rewrites` entry that sent everything to `/api`. Vercel now uses the FastAPI app exposed from `index.py` as intended.

- **Root `index.py`**  
  Path logic updated so the directory that contains `forge` is on `sys.path`: if `zuup-forge/forge` exists, `zuup-forge` is added; otherwise the file’s directory is used. This works for both repo-root and `zuup-forge`-root deployments.

## Optional: use subfolder as root

If the Git repo root contains more than the app, you can set **Root Directory** in Vercel to `zuup-forge`:

1. Vercel dashboard → your project → **Settings**
2. **Build and Deployment** → **Root Directory** → set to `zuup-forge`
3. Redeploy

Then only `zuup-forge/` is built; its `vercel.json` and `index.py` are used and no rewrites are involved.

## Log analysis (404 after first fix)

Vercel logs showed two behaviors:

- **Older deployment** (`dpl_EK9mMuHNuaX4zjA9JDHiVJtn5Fuk`): `"function":"/api"` — requests were correctly routed to `/api`, but there was **no handler** for `/api`, so 404. That matched the missing `api/` implementation.
- **Newer deployments** (e.g. `dpl_DfWLUe2pmN3xwKba5cn3f6dGnVCQ`): `"function":"/404.html"`, `"type":"static"` — after removing the rewrite, Vercel **did not invoke any Python app** and fell through to the static 404 page.

So framework auto-detection was not running the root `index.py` as a serverless function. The fix is to use an **explicit serverless handler** under `api/` and route all traffic to it.

## Additional fix: explicit API handler

- **`api/index.py`** was added: a serverless handler that adds the correct `sys.path`, imports the FastAPI app from `forge.ui.app`, and wraps it so that when Vercel sends path `/api` or `/api/...` (after rewrite), the path is normalized to `/` and `/...` before calling FastAPI.
- **Root `vercel.json`** again uses `"rewrites": [{ "source": "/(.*)", "destination": "/api" }]` so every request hits the `/api` serverless function. This time `/api` is implemented by `api/index.py`.

## After redeploy

1. Push the changes and let Vercel redeploy (or trigger a redeploy from the dashboard).
2. Open https://zuup-forge.vercel.app/ — you should see the ZUUP FORGE UI.
3. Favicon 404s (`favicon.ico`, `favicon.png`) may still appear until you add those files under `public/` or handle them in the app; the main page should load.
4. If you still see 404, check the deployment **Logs** in the Vercel dashboard for Python import or runtime errors.
