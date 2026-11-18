# WealthOS Connect for Android

WealthOS Connect is the private mobile bridge for financial messages delivered through Google Messages notifications.

## Data flow

1. WealthOS creates a ten-minute pairing secret from **Settings → Mobile Connections**.
2. The Android app scans the QR code and exchanges the one-time secret for a revocable device token.
3. The token is stored using Android encrypted preferences.
4. After the user enables notification access, the app reads new Google Messages notifications only, accepts configured sender IDs, rejects OTP messages on the phone, and sends financial messages over HTTPS.
5. The server rejects duplicate source IDs and duplicate message fingerprints.
6. Parsed operations enter the existing WealthOS review queue. They never post directly to the ledger.

New messages trigger an immediate background sync, while WorkManager provides reliable offline retry. Historical messages are not read from the SMS database and can be backfilled separately through the WealthOS import review flow.

## Build

The GitHub Actions workflow `WealthOS Connect Android` produces a private debug APK for validation. A production release must use a private release signing key stored in GitHub Actions secrets; the signing key must never be committed to the repository.

## Android permissions

The app does not request `READ_SMS` or `RECEIVE_SMS`. Android displays a one-time notification-access screen, and the user can revoke access at any time. This avoids Google Play's restricted SMS permissions while preserving automatic capture of new Google Messages notifications.
