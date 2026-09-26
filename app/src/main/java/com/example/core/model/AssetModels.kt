package com.example.core.model

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import java.util.UUID

enum class AssetType { IMAGE, AUDIO, VIDEO, DOCUMENT, OTHER }
enum class AssetStatus { READY, IMPORTING, CORRUPTED, DELETED }

@Entity(tableName = "assets", indices = [Index(value = ["projectId"]), Index(value = ["sha256"]), Index(value = ["projectId", "status"])])
data class Asset(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val projectId: String,
    val type: AssetType,
    val mimeType: String,
    val fileName: String,
    val relativePath: String,
    val sizeBytes: Long,
    val sha256: String,
    val width: Int? = null,
    val height: Int? = null,
    val durationMs: Long? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val status: AssetStatus = AssetStatus.READY,
)
