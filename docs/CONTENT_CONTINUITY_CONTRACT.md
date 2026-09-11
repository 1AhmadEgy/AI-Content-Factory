# Content Continuity Contract

## Purpose

AI Content Factory treats people, places, country context, and production identity as persistent project data. AI providers may improve wording and shot direction, but they are not allowed to silently redesign canonical identities.

## Canonical identity

A selected `CharacterProfile` is identified by its stable `character_id`. A selected `LocationProfile` is identified by its stable `location_id`. Their saved appearance, personality, voice, speaking style, visual style, geography, architecture, environment, lighting, weather, props, rules, negative constraints, and reference assets remain the source of truth.

## Country and local context

`country_id` and `library_id` define the active cultural/local production scope. The runtime rejects a country/library mismatch. Selected characters and locations must belong to the active project/library scope.

## AI stages

Story generation receives the saved character and location snapshots. Script editing must preserve scene count, shot count, character IDs, and location IDs. Scene/shot planning must preserve those IDs as well. The orchestration runtime validates continuity after every AI planning stage and fails closed on a scope or identity violation.

## No silent substitution

A provider may not invent a new person, place, country, library, character ID, or location ID to fill a missing value. Missing identity data is an explicit failure or an empty selection, depending on the operation contract.

## Visual generation

When a future image/video provider is connected, its prompt builder must use the same canonical identity and location context. Provider-specific character/location references may be stored as `providerCharacterId` and `providerLocationId`, but those mappings never replace the internal canonical IDs.

## Versioning

Character and location profiles carry versions. Future asset-generation jobs should snapshot the selected versions so later edits do not retroactively change an already-produced asset's provenance.
