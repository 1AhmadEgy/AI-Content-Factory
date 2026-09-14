package com.example

import android.content.Context
import com.example.data.security.ApiKeyStore

object AppContainer {
    private lateinit var applicationContext: Context

    fun initialize(context: Context) {
        applicationContext = context.applicationContext
    }

    fun apiKeyStore(): ApiKeyStore = ApiKeyStore(applicationContext)
}
