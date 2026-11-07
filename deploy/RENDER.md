# WealthOS on Render

This beta uses a separate Render PostgreSQL database. Never connect it to the
desktop application's database or copy a local `.env` file.

## Current release

- Render Blueprint: `render.yaml`.
- App service: paid Starter compute, 512 MB RAM, one instance; auto-deploy is off.
- Database: a new, private 1 GB PostgreSQL database, PostgreSQL 17. It is named
  `wealthos-main-db-2026` to avoid reusing any previous database.
- The workspace can stay on Hobby. The selected web service is $7/month; the
  smallest paid PostgreSQL compute is about $6/month, plus about $0.30/month for
  1 GB storage. Expected baseline: about $13.30/month before usage-based charges.
- Migration head: `a1b2c3d4e5f6`. Render runs migrations before starting the web
  service. It inserts only public reference catalogs, never financial records.
- The release supports one Administrator and two tester accounts, using one
  admin invite and two tester invites. Registration is limited to three accounts.
- GitHub Actions builds the actual Linux image and checks startup against a
  disposable PostgreSQL database. It does not deploy to Render.

## Initial Render setup

1. Review and remove only the old WealthOS Render service/database after checking
   their names and contents. Do not delete unrelated workspace resources.
2. Create/sync the Blueprint from this repository and branch `wealthos/railway-beta`.
   Select the paid 512 MB service plan and keep deploys manual during beta testing.
3. Render prompts for `WEB_ADMIN_INVITE_CODE` and `WEB_INVITE_CODES`. Set one
   unique secret admin invite and two unique tester invites (each 16+ characters).
   Never commit them. The migration stores only hashes and role flags.
4. After the first successful migration provisions the invite rows, remove both
   invite environment variables. Their hashed one-time invitations remain usable.
5. Verify `/ready`, registration, login, logout, secure cookies and three-user
   limits. Confirm database backups are enabled, then share the app with testers.

The hosted database is created as a new destination, then receives a snapshot of
the current local database. The original local database is retained unchanged.

## Recovery

- PostgreSQL must be writable for pre-deploy migrations; a release lock prevents
  simultaneous migration jobs. A schema mismatch fails readiness.
- A code rollback does not undo database migrations. Restore backups into another
  disposable database before deciding on recovery.
