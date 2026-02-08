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

## After redeploy

1. Push the changes and let Vercel redeploy (or trigger a redeploy from the dashboard).
2. Open https://zuup-forge.vercel.app/ — you should see the ZUUP FORGE UI.
3. If you still see 404, check the deployment **Logs** in the Vercel dashboard for Python import or runtime errors.
