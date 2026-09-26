package com.example.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.core.model.Asset
import kotlinx.coroutines.flow.Flow

@Dao
interface AssetDao {
    @Query("SELECT * FROM assets WHERE projectId = :projectId AND status != 'DELETED' ORDER BY createdAt DESC")
    fun observeProjectAssets(projectId: String): Flow<List<Asset>>

    @Query("SELECT * FROM assets WHERE projectId = :projectId AND type = :type AND status != 'DELETED' ORDER BY createdAt DESC")
    fun observeProjectAssetsByType(projectId: String, type: String): Flow<List<Asset>>

    @Query("SELECT * FROM assets WHERE id = :assetId LIMIT 1")
    suspend fun get(assetId: String): Asset?

    @Query("SELECT * FROM assets WHERE projectId = :projectId AND sha256 = :sha256 LIMIT 1")
    suspend fun findByHash(projectId: String, sha256: String): Asset?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(asset: Asset)

    @Update
    suspend fun update(asset: Asset)

    @Query("UPDATE assets SET status = 'DELETED' WHERE id = :assetId")
    suspend fun markDeleted(assetId: String)

    @Query("DELETE FROM assets WHERE projectId = :projectId AND status = 'DELETED'")
    suspend fun purgeDeleted(projectId: String)

    @Query("SELECT COALESCE(SUM(sizeBytes), 0) FROM assets WHERE projectId = :projectId AND status = 'READY'")
    suspend fun projectBytes(projectId: String): Long
}
