# Android Local-First Project Storage

## Source of truth

The Android project is local-first for project media:

- Room stores project structure and asset metadata.
- Binary images, audio, video, documents and other project files are stored in the app-private filesystem.
- Cloud/Supabase storage is not used as the primary project-media store.
- Backend-generated media may be downloaded once and materialized into the local project store.
- Every imported asset is SHA-256 hashed and can be verified later.

## Layout

```text
<app filesDir>/
└── projects/
    └── <projectId>/
        ├── image/
        ├── audio/
        ├── video/
        ├── document/
        └── other/
```

Files are written to a temporary `.part` file and renamed after the write completes. The final filename starts with a short SHA-256 prefix.

## Room

Room schema version 2 adds the `assets` table:

- id
- projectId
- type
- mimeType
- fileName
- relativePath
- sizeBytes
- sha256
- width / height
- durationMs
- createdAt
- status

The 1→2 migration is explicit; destructive migration is not used.

## Security

- Project IDs are validated.
- Relative paths are canonicalized and cannot escape the project directory.
- User-controlled file names are sanitized.
- Binary data is not stored in Room.
- General cleartext traffic is disabled. Debug may use the Android emulator loopback backend.
- Release builds require an HTTPS backend URL.
- Backend configuration is injected only during CI builds; there is no API-key entry screen in the Android app.

## Generated media

The Android client exposes the backend asset list/get/download API and provides a repository method to materialize a ready backend asset locally. The downloaded bytes are checksum-verified before being registered in Room.

## Backups and export

App-private project media is intentionally separate from public gallery storage. A future explicit export feature can copy selected assets to MediaStore without changing the primary storage model.
