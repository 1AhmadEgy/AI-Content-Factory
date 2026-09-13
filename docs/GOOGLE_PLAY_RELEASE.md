# Google Play release

This project produces a signed Android App Bundle (`.aab`) for Google Play.

## Signing model

The CI workflow uses the **upload key** stored in GitHub Actions secrets. Google Play App Signing should remain enabled in Play Console so Google manages the final app-signing key and signs the APKs distributed to users.

CI never commits a keystore or password to the repository.

## Required GitHub Actions secrets

Configure these repository secrets before running `Android Google Play Release`:

- `RELEASE_KEYSTORE_B64` — base64-encoded upload keystore (`.jks`/`.keystore`).
- `RELEASE_STORE_PASSWORD` — keystore password.
- `RELEASE_KEY_PASSWORD` — upload-key password.
- `RELEASE_KEY_ALIAS` — upload-key alias.

The workflow intentionally **fails** when any of these production signing secrets are missing. The normal APK CI may still use an ephemeral key for non-production validation, but that key must never be used as the Play upload key.

## First Play Console setup

1. Create the application in Google Play Console using the same Android package/application ID as the project.
2. Enable Google Play App Signing when prompted.
3. Register the upload certificate generated from the CI upload keystore if Play Console asks for it.
4. Store the upload keystore and its credentials only in GitHub Actions secrets.
5. Run `Android Google Play Release` manually or push a version tag such as `v1.0.1`.
6. Download the `AI-Content-Factory-Play-AAB` artifact and, when desired, upload the AAB to the appropriate Play Console track.

## Important versioning rule

Every Play upload must have a strictly increasing `versionCode`. Update `versionCode` and `versionName` in `app/build.gradle.kts` before the next production upload.

Never replace the Play upload keystore after production adoption unless the Play Console's supported upload-key reset/change process is used.

## CI verification

The Play workflow performs:

- Android lint.
- JVM/unit tests.
- Release AAB build.
- Existence and non-empty checks.
- Upload-key certificate inspection.
- AAB signature verification with `jarsigner`.
- Artifact publication for the Play-ready AAB.

The workflow does **not** claim that an AAB has been published to Google Play. Publishing requires Play Console configuration and the appropriate Google Play Developer API credentials/permissions.
