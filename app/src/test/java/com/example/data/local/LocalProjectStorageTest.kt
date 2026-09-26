package com.example.data.local

import com.example.core.model.AssetType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.nio.file.Files

class LocalProjectStorageTest {
    @Test
    fun importsBytes_intoProjectPrivateStorage_andVerifiesChecksum() {
        val root = testRoot()
        try {
            val storage = LocalProjectStorage(rootDirectory = root)
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
        } finally {
            root.deleteRecursively()
        }
    }

    @Test
    fun rejectsPathTraversalProjectId() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val root = testRoot()
        try {
            val storage = LocalProjectStorage(context, root)
            assertThrows(IllegalArgumentException::class.java) {
                storage.importBytes("../escape", byteArrayOf(1), AssetType.OTHER, "application/octet-stream", "x.bin")
            }
        } finally {
            root.deleteRecursively()
        }
    }

    private fun testRoot(): File = Files.createTempDirectory("aicf-local-storage-").toFile()
}
