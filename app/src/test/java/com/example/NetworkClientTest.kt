package com.example

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.example.data.remote.NetworkClient
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class NetworkClientTest {
    private val context: Context = ApplicationProvider.getApplicationContext()

    @After
    fun tearDown() {
        NetworkClient.resetBaseUrl(context)
    }

    @Test
    fun setBaseUrl_normalizesAndPersistsUrl() {
        NetworkClient.setBaseUrl(context, "http://192.168.1.10:8000")

        assertEquals("http://192.168.1.10:8000/", NetworkClient.getConfiguredBaseUrl(context))
    }

    @Test
    fun setBaseUrl_rejectsNonHttpSchemes() {
        val failure = runCatching { NetworkClient.setBaseUrl(context, "ftp://192.168.1.10:8000") }.exceptionOrNull()

        assertTrue(failure is IllegalStateException)
    }
}
