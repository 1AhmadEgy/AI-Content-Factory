package com.example.data.local

import androidx.test.core.app.ApplicationProvider
import com.example.core.model.AssetType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class LocalProjectStorageTest {
    @Test
    fun importsBytes_intoProjectPrivateStorage_andVerifiesChecksum() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val storage = LocalProjectStorage(context)
        val asset = storage.importBytes(
            projectId = "project-test",
            bytes = "hello-local".toByteArray(),
            type = AssetType.OTHER,
            mimeType = "text/plain",
            fileName = "../unsafe name.txt",
        )

        assertTrue(storage.assetFile(asset).isFile)
        assertEquals(asset.sizeBytes, storage.assetFile(asset).length())
        assertTrue(storage.verify(asset))
        assertTrue(asset.relativePath.startsWith("project-test/"))
        assertTrue(!asset.fileName.contains("/"))
        assertTrue(!asset.fileName.contains(".."))

        storage.delete(asset)
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsPathTraversalProjectId() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        LocalProjectStorage(context).importBytes("../escape", byteArrayOf(1), AssetType.OTHER, "application/octet-stream", "x.bin")
    }
}
