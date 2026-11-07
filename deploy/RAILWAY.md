# Railway beta deployment

This branch deploys the current local application in a separate hosted environment.
Never connect it to the desktop application's database or copy a local `.env` file.

## Release checks

- `railway.json` selects `Dockerfile.web`, a single replica, a pre-deploy migration
  command, and `/ready`. Startup validates hosted settings without migrating again.
- Current migration head: `a1b2c3d4e5f6`.
- Pre-deploy also inserts missing public currencies, chart-of-account entries,
  strategies and objectives atomically. Existing catalog rows are preserved;
  no personal portfolios, balances or financial transactions are seeded.
- Local checks: React production build, 23 focused tests, and a PostgreSQL 17
  registration/session/isolation smoke test against a freshly migrated database.
- GitHub Actions builds and starts the actual Linux image against disposable
  PostgreSQL. Require this check to pass before the first Railway deployment.
- No GitHub workflow deploys to Railway automatically.

## Railway setup

1. Create a separate beta project and a new PostgreSQL service. Keep the database
   private. Do not import existing financial data.
2. Add a GitHub-backed application service using branch `wealthos/railway-beta`.
   Keep automatic deploys disabled while preparing the initial release.
3. Set the variables in `deploy/railway.env.example`. Use Railway's reference to
   the new PostgreSQL service's private `DATABASE_URL`. Set `TRUSTED_HOSTS` to the
   generated application hostname plus `healthcheck.railway.app`.
4. Generate three unique invitation codes with a cryptographic random generator
   (at least 16 characters each). Put one in `WEB_ADMIN_INVITE_CODE` and the other
   two, comma-separated, in `WEB_INVITE_CODES`. Keep them private and never commit
   them. Only hashes and role flags are stored in the database. The admin invite
   creates the sole Administrator; the other two create tester accounts. Remove
   both invitation variables after the migration provisions them; the stored
   invitation rows remain available for their first use.
5. Enable database backups and test restoring into another disposable database.
   Configure usage alerts. Confirm costs in the account before provisioning.
6. Deploy the reviewed commit manually. Verify `/ready`, login, logout, page refresh,
   secure cookies and isolation with three synthetic accounts on the Railway URL.
7. Invite testers only after those checks. Naming and custom domains are deferred.

## Operational notes

- PostgreSQL must be writable for pre-deploy migrations; the release lock avoids
  simultaneous migration jobs. Schema mismatch fails readiness.
- One process/replica is intentional while the in-process scheduled job remains.
- A code rollback does not undo database migrations. Avoid automatic downgrades;
  restore backups into a separate database before deciding on recovery.
- Existing `render.yaml` is historical and is not the deployment configuration.
