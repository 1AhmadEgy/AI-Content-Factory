package com.example.data.remote

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class RemoteAsset(
    val id: String,
    @Json(name = "projectId") val projectId: String,
    val type: String,
    val path: String,
    @Json(name = "mimeType") val mimeType: String,
    @Json(name = "sizeBytes") val sizeBytes: Long,
    val sha256: String,
    val status: String,
    @Json(name = "createdAt") val createdAt: String? = null,
)

@JsonClass(generateAdapter = true)
data class AssetEnvelope(val data: RemoteAsset)

@JsonClass(generateAdapter = true)
data class AssetsFeed(
    val data: List<RemoteAsset>,
    val pagination: Pagination? = null,
)

@JsonClass(generateAdapter = true)
data class Pagination(
    val page: Int,
    val pageSize: Int,
    val total: Int,
    val hasNext: Boolean,
)
