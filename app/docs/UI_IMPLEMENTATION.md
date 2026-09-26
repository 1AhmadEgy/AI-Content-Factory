# AI Content Factory — UI Implementation

## Design source

Figma design system:
https://www.figma.com/design/UoFddqBmf5sYE0ZSGnbilC

The Android UI keeps the existing navigation and backend architecture while standardizing visual language and reusable Compose components.

## Screen coverage

### Core production
- Dashboard / Projects
- Project Details
- Series Details
- Series Control
- Episode Details
- Characters
- Character Details
- Scene Builder
- Control Center
- Designer / Profile

### AI workspace
- AI Studio
- Prompt workspace
- Generation result
- Generation history
- Processing state
- Retry / error state
- Empty state

### Operations
- Jobs
- Worker status
- Provider runs
- Backend status
- Provider settings

### Global UX
- Search
- Notifications
- Settings
- Help / About
- Loading
- Empty
- Error
- Offline / processing visual states

## Design tokens

- Background: DarkBlue
- Surface: SurfaceBlue
- Elevated surface: ElevatedBlue
- Primary: PrimaryCyan
- Secondary: SecondaryTeal
- Accent: NeonPurple
- Accent: NeonPink
- Success: SuccessGreen
- Warning: WarningOrange
- Error: ErrorRed
- Text: TextLight / TextMuted
- Border: BorderBlue

## Reusable Compose components

- NeonHero
- NeonSectionCard
- NeonStatusChip
- NeonMetricCard
- NeonActionButton
- NeonOutlinedButton
- NeonEmptyState
- NeonErrorState
- NeonProcessingState
- NeonLoading

## Navigation

The main navigation now exposes:
- Projects
- AI Studio
- Characters
- Control Center
- Designer/Profile

Global actions in the header:
- Search
- Notifications
- Settings

Secondary routes:
- Provider Settings
- Backend Status
- Generation History
- Help / About

## Implementation rule

Do not duplicate screen-specific neon styling when an existing shared component can express the same UI. New screens should use the shared design tokens and components first.

## Verification

GitHub Actions now includes an Android job that:
1. Uses JDK 17.
2. Compiles :app:compileDebugKotlin.
3. Runs :app:testDebugUnitTest.

The backend CI remains unchanged and continues to validate Python, assets, tests, and Docker publishing.