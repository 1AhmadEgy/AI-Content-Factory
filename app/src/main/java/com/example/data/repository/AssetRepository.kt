package com.example.data.repository

import com.example.core.model.Asset
import com.example.core.model.AssetStatus
import com.example.core.model.AssetType
import com.example.data.local.AssetDao
import com.example.data.local.LocalProjectStorage
import com.example.data.remote.RemoteAsset
import okhttp3.ResponseBody
import kotlinx.coroutines.flow.Flow
import java.io.File

class AssetRepository(private val dao: AssetDao, private val storage: LocalProjectStorage) {
    fun observeProjectAssets(projectId: String): Flow<List<Asset>> = dao.observeProjectAssets(projectId)
    fun observeProjectAssets(projectId: String, type: AssetType): Flow<List<Asset>> =
        dao.observeProjectAssetsByType(projectId, type.name)
    suspend fun get(assetId: String): Asset? = dao.get(assetId)
    fun file(asset: Asset): File = storage.assetFile(asset)

    suspend fun importFile(projectId: String, source: File, type: AssetType, mimeType: String, fileName: String = source.name): Asset {
        val asset = storage.importFile(projectId, source, type, mimeType, fileName)
        val existing = dao.findByHash(projectId, asset.sha256)
        if (existing != null) { storage.delete(asset); return existing }
        dao.insert(asset)
        return asset
    }

    suspend fun importBytes(projectId: String, bytes: ByteArray, type: AssetType, mimeType: String, fileName: String): Asset {
        val asset = storage.importBytes(projectId, bytes, type, mimeType, fileName)
        val existing = dao.findByHash(projectId, asset.sha256)
        if (existing != null) { storage.delete(asset); return existing }
        dao.insert(asset)
        return asset
    }

    suspend fun delete(assetId: String) {
        val asset = dao.get(assetId) ?: return
        storage.delete(asset)
        dao.markDeleted(assetId)
    }

    suspend fun verify(assetId: String): Boolean {
        val asset = dao.get(assetId) ?: return false
        val valid = storage.verify(asset)
        if (!valid) dao.update(asset.copy(status = AssetStatus.CORRUPTED))
        return valid
    }

    suspend fun importRemote(projectId: String, remote: RemoteAsset, body: ResponseBody): Asset {
        require(remote.projectId == projectId) { "Remote asset belongs to another project" }
        require(remote.status == "READY") { "Remote asset is not ready" }
        body.use {
            val type = runCatching { AssetType.valueOf(remote.type.uppercase()) }.getOrDefault(AssetType.OTHER)
            val fileName = remote.path.substringAfterLast('/').ifBlank { remote.id }
            val asset = storage.importStream(projectId, it.byteStream(), type, remote.mimeType, fileName)
            require(asset.sha256.equals(remote.sha256, ignoreCase = true)) { "Remote asset checksum mismatch" }
            val existing = dao.findByHash(projectId, asset.sha256)
            if (existing != null) { storage.delete(asset); return existing }
            dao.insert(asset)
            return asset
        }
    }

    suspend fun projectBytes(projectId: String): Long = dao.projectBytes(projectId)
}
