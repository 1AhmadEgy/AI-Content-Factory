package com.example.data.local

import android.content.Context
import android.graphics.BitmapFactory
import android.media.MediaMetadataRetriever
import com.example.core.model.Asset
import com.example.core.model.AssetStatus
import com.example.core.model.AssetType
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.UUID

/** Local-first, app-private binary storage. Room stores metadata only. */
class LocalProjectStorage(context: Context) {
    private val root = File(context.applicationContext.filesDir, "projects")

    fun projectRoot(projectId: String): File = safeProjectDirectory(projectId)
    fun assetFile(asset: Asset): File = resolveRelative(asset.projectId, asset.relativePath)

    fun importFile(projectId: String, source: File, type: AssetType, mimeType: String, fileName: String = source.name): Asset {
        require(source.isFile) { "Source file does not exist" }
        return source.inputStream().use { importStream(projectId, it, type, mimeType, fileName) }
    }

    fun importBytes(projectId: String, bytes: ByteArray, type: AssetType, mimeType: String, fileName: String): Asset =
        bytes.inputStream().use { importStream(projectId, it, type, mimeType, fileName) }

    fun importStream(projectId: String, input: java.io.InputStream, type: AssetType, mimeType: String, fileName: String): Asset {
        validateProjectId(projectId)
        val safeName = sanitizeFileName(fileName)
        val directory = File(safeProjectDirectory(projectId), type.name.lowercase()).apply { mkdirs() }
        check(directory.isDirectory) { "Unable to create asset directory" }

        val temp = File(directory, ".${UUID.randomUUID()}.part")
        var size = 0L
        val digest = MessageDigest.getInstance("SHA-256")
        FileOutputStream(temp).use { output ->
            val buffer = ByteArray(BUFFER_SIZE)
            while (true) {
                val read = input.read(buffer)
                if (read <= 0) break
                output.write(buffer, 0, read)
                digest.update(buffer, 0, read)
                size += read
            }
            output.fd.sync()
        }

        val hash = digest.digest().toHex()
        val finalFile = File(directory, "${hash.take(16)}-$safeName")
        if (finalFile.exists()) temp.delete() else check(temp.renameTo(finalFile)) { "Unable to commit local asset" }

        val dimensions = if (type == AssetType.IMAGE) readImageDimensions(finalFile) else null
        val duration = if (type == AssetType.AUDIO || type == AssetType.VIDEO) readDuration(finalFile) else null
        val relativePath = root.canonicalFile.toURI().relativize(finalFile.canonicalFile.toURI()).path

        return Asset(
            projectId = projectId, type = type, mimeType = mimeType, fileName = safeName,
            relativePath = relativePath, sizeBytes = size, sha256 = hash,
            width = dimensions?.first, height = dimensions?.second, durationMs = duration,
            status = AssetStatus.READY,
        )
    }

    fun delete(asset: Asset): Boolean = assetFile(asset).delete()

    fun verify(asset: Asset): Boolean {
        val file = assetFile(asset)
        if (!file.isFile || file.length() != asset.sizeBytes) return false
        return sha256(file) == asset.sha256
    }

    private fun safeProjectDirectory(projectId: String): File {
        validateProjectId(projectId)
        return File(root, projectId).also { it.mkdirs() }
    }

    private fun resolveRelative(projectId: String, relativePath: String): File {
        validateProjectId(projectId)
        require(!relativePath.startsWith("/") && !relativePath.contains("..")) { "Invalid asset path" }
        val project = safeProjectDirectory(projectId).canonicalFile
        val file = File(project, relativePath).canonicalFile
        check(file.path.startsWith(project.path + File.separator)) { "Asset path escapes project directory" }
        return file
    }

    private fun validateProjectId(projectId: String) {
        require(projectId.matches(Regex("[A-Za-z0-9._-]{1,128}"))) { "Invalid project id" }
    }

    private fun sanitizeFileName(name: String): String {
        val cleaned = name.substringAfterLast('/').substringAfterLast('\\')
            .replace(Regex("[^A-Za-z0-9._-]"), "_").trim('.')
        return cleaned.takeIf { it.isNotBlank() }?.take(180) ?: "asset"
    }

    private fun readImageDimensions(file: File): Pair<Int, Int>? {
        val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(file.absolutePath, options)
        return if (options.outWidth > 0 && options.outHeight > 0) options.outWidth to options.outHeight else null
    }

    private fun readDuration(file: File): Long? {
        val retriever = MediaMetadataRetriever()
        return try {
            retriever.setDataSource(file.absolutePath)
            retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull()
        } catch (_: Throwable) { null } finally { runCatching { retriever.release() } }
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { input ->
            val buffer = ByteArray(BUFFER_SIZE)
            while (true) {
                val read = input.read(buffer)
                if (read <= 0) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().toHex()
    }

    private fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }
    private companion object { const val BUFFER_SIZE = 1024 * 1024 }
}
