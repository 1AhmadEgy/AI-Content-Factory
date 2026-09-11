package com.example.data.remote

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class ProjectEnvelope(val data: ProjectDto, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class ProjectDto(
    val id: String,
    val name: String,
    val description: String? = null,
)

@JsonClass(generateAdapter = true)
data class JobInputRequest(
    val parameters: Map<String, Any?> = emptyMap(),
    val referenceAssetIds: List<String> = emptyList(),
    val constraints: Map<String, Any?> = emptyMap(),
    val seed: Int? = null,
    val deterministic: Boolean = false,
)

@JsonClass(generateAdapter = true)
data class CreateJobRequest(
    val projectId: String,
    val type: String,
    val targetType: String,
    val targetId: String? = null,
    val parentJobId: String? = null,
    val priority: Int = 100,
    val maxAttempts: Int = 3,
    val provider: String? = null,
    val model: String? = null,
    val input: JobInputRequest = JobInputRequest(),
)

@JsonClass(generateAdapter = true)
data class JobEnvelope(val data: BackendJob, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class CharacterEnvelope(val data: CharacterDto, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class CharacterListEnvelope(val data: List<CharacterDto>, val meta: CharacterMeta? = null, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class CharacterMeta(val count: Int = 0, val limit: Int = 100)

@JsonClass(generateAdapter = true)
data class CharacterDto(
    val id: String,
    val projectId: String,
    val name: String,
    val aliases: List<String> = emptyList(),
    val description: String = "",
    val personality: Map<String, Any?> = emptyMap(),
    val appearance: Map<String, Any?> = emptyMap(),
    val voice: Map<String, Any?> = emptyMap(),
    val speakingStyle: Map<String, Any?> = emptyMap(),
    val visualStyle: Map<String, Any?> = emptyMap(),
    val behaviorRules: List<String> = emptyList(),
    val referenceAssetIds: List<String> = emptyList(),
    val providerCharacterId: String? = null,
    val metadata: Map<String, Any?> = emptyMap(),
    val version: Int = 1,
    val createdAt: String? = null,
    val updatedAt: String? = null,
)

@JsonClass(generateAdapter = true)
data class LocationDto(
    val id: String,
    val projectId: String,
    val name: String,
    val description: String = "",
    val visualStyle: Map<String, Any?> = emptyMap(),
)

@JsonClass(generateAdapter = true)
data class LocationListEnvelope(val data: List<LocationDto>, val meta: CharacterMeta? = null, val requestId: String? = null)

@JsonClass(generateAdapter = true)
data class ShotCharacterRequest(
    val characterId: String,
    val action: String? = null,
    val emotion: String? = null,
    val dialogue: String? = null,
    val pose: String? = null,
    val expressionOverride: String? = null,
    val positionOrder: Int = 0,
)

@JsonClass(generateAdapter = true)
data class ComposeShotRequest(
    val characters: List<ShotCharacterRequest>,
    val locationId: String? = null,
    val cameraAngle: String = "medium",
    val mood: String? = null,
    val sceneContext: String? = null,
    val durationSec: Double = 3.0,
    val visualStyle: Map<String, Any?> = emptyMap(),
)

@JsonClass(generateAdapter = true)
data class ComposeShotData(
    val prompt: String,
    val negativePrompt: String,
    val continuityHash: String,
    val characters: List<Map<String, Any?>> = emptyList(),
    val location: Map<String, Any?>? = null,
)

@JsonClass(generateAdapter = true)
data class ComposeShotEnvelope(val data: ComposeShotData, val requestId: String? = null)
