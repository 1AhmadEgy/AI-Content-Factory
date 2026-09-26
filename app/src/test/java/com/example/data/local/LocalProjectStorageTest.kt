package com.example.data.local

import com.example.core.model.AssetType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

class LocalProjectStorageTest {
    @Test
    fun importsBytes_intoProjectPrivateStorage_andVerifiesChecksum() {
        val root = testRoot()
        try {
            val storage = LocalProjectStorage(root)
            val asset = storage.importBytes(
                projectId = "project-test",
                bytes = "hello-local".toByteArray(),
                type = AssetType.OTHER,
                mimeType = "text/plain",
                fileName = "unsafe-name.txt",
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
        val root = testRoot()
        try {
            val storage = LocalProjectStorage(root)
            assertThrows(IllegalArgumentException::class.java) {
                storage.importBytes("../escape", byteArrayOf(1), AssetType.OTHER, "application/octet-stream", "x.bin")
            }
        } finally {
            root.deleteRecursively()
        }
    }

    @Test
    fun rejectsAssetPathOutsideProject() {
        val root = testRoot()
        try {
            val storage = LocalProjectStorage(root)
            val asset = storage.importBytes(
                projectId = "project-test",
                bytes = byteArrayOf(1),
                type = AssetType.OTHER,
                mimeType = "application/octet-stream",
                fileName = "x.bin",
            )
            assertThrows(IllegalStateException::class.java) {
                storage.assetFile(asset.copy(relativePath = "other-project/other/x.bin"))
            }
            assertTrue(storage.delete(asset))
        } finally {
            root.deleteRecursively()
        }
    }

    @Test
    fun keepsProjectIsolation_whenResolvingRelativeAssetPaths() {
        val root = testRoot()
        try {
            val storage = LocalProjectStorage(root)
            val assetA = storage.importBytes(
                projectId = "project-a",
                bytes = byteArrayOf(1),
                type = AssetType.OTHER,
                mimeType = "application/octet-stream",
                fileName = "a.bin",
            )
            val assetB = storage.importBytes(
                projectId = "project-b",
                bytes = byteArrayOf(2),
                type = AssetType.OTHER,
                mimeType = "application/octet-stream",
                fileName = "b.bin",
            )

            assertTrue(storage.assetFile(assetA).path.startsWith(File(root, "project-a").canonicalPath + File.separator))
            assertTrue(storage.assetFile(assetB).path.startsWith(File(root, "project-b").canonicalPath + File.separator))
            assertTrue(storage.delete(assetA))
            assertTrue(storage.delete(assetB))
        } finally {
            root.deleteRecursively()
        }
    }

    private fun testRoot(): File =
        File(System.getProperty("java.io.tmpdir"), "aicf-local-storage-" + System.nanoTime()).apply {
            check(mkdirs()) { "Unable to create temporary test directory" }
        }
}
