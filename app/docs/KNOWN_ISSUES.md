# Known Issues

## #1 — Robolectric Unsupported SDK

**Symptoms**:

```text
java.lang.UnsupportedOperationException
at org.robolectric.internal.DefaultSdkProvider...
```

**Cause**:
Robolectric may resolve the test SDK from the application's `targetSdk`. When the project targets SDK 36 but the Robolectric version used by the test environment does not provide support for SDK 36, Robolectric initialization can fail.

**Test-only workaround**:

```kotlin
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class ExampleRobolectricTest { /* ... */ }
```

This does **not** change the application's `compileSdk` or `targetSdk`; those remain 36.

**Preferred protection for new Robolectric tests**:
Use the shared `@RobolectricSdk35` annotation from the test source set so the compatibility workaround has one maintenance point.

```kotlin
@RunWith(RobolectricTestRunner::class)
@RobolectricSdk35
class MyTest { /* ... */ }
```

When the project's Robolectric version officially supports SDK 36 in the CI environment, update the shared annotation once and remove the workaround when appropriate.

**Affected test**:

- `app/src/test/java/.../ExampleRobolectricTest.kt`

**Detection**:

```bash
./gradlew :app:testDebugUnitTest
```

A recurrence normally appears as `UnsupportedOperationException` from `org.robolectric.internal.DefaultSdkProvider` during Robolectric test initialization.
