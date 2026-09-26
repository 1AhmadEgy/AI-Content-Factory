package com.example.data.local

import androidx.test.core.app.ApplicationProvider
import com.example.core.model.AssetType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.util.UUID

class LocalProjectStorageTest {
    @Test
    fun importsBytes_intoProjectPrivateStorage_andVerifiesChecksum() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val root = testRoot()
        val storage = LocalProjectStorage(context, root)
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

        assertTrue(storage.delete(asset))
        assertTrue(root.deleteRecursively())
    }

    @Test
    fun rejectsPathTraversalProjectId() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val root = testRoot()
        val storage = LocalProjectStorage(context, root)
        assertThrows(IllegalArgumentException::class.java) {
            storage.importBytes("../escape", byteArrayOf(1), AssetType.OTHER, "application/octet-stream", "x.bin")
        }
        assertTrue(root.deleteRecursively())
    }

    private fun testRoot(): File =
        File(System.getProperty("java.io.tmpdir"), "aicf-local-storage-" + UUID.randomUUID()).apply {
            check(mkdirs()) { "Unable to create temporary test root: $absolutePath" }
        }
}
