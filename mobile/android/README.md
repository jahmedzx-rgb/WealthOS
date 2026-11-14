# WealthOS Connect for Android

WealthOS Connect is the private mobile bridge for financial SMS messages.

## Data flow

1. WealthOS creates a ten-minute pairing secret from **Settings → Mobile Connections**.
2. The Android app scans the QR code and exchanges the one-time secret for a revocable device token.
3. The token is stored using Android encrypted preferences.
4. The app reads only configured sender IDs, rejects OTP messages on the phone, and sends financial messages over HTTPS.
5. The server rejects duplicate source IDs and duplicate message fingerprints.
6. Parsed operations enter the existing WealthOS review queue. They never post directly to the ledger.

The first paired sync starts on 15 October 2026. New messages trigger an immediate background sync, while WorkManager provides an offline retry and periodic safety sync.

## Build

The GitHub Actions workflow `WealthOS Connect Android` produces a private debug APK for validation. A production release must use a private release signing key stored in GitHub Actions secrets; the signing key must never be committed to the repository.

## Android permissions

The private build requests `READ_SMS` and `RECEIVE_SMS` because SMS-based money management is its core function. If the application is distributed through Google Play, the SMS permission declaration and privacy disclosure must be approved before release.
