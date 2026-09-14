package com.example.data.remote

import com.example.AppContainer
import com.example.BuildConfig
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import java.util.UUID
import java.util.concurrent.TimeUnit
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory

object NetworkClient {
    private const val NOT_CONFIGURED = "__NOT_CONFIGURED__"
    private const val DEFAULT_EMULATOR_BASE_URL = "http://10.0.2.2:8000/"

    private val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

    private fun normalizedBaseUrl(): String {
        val configured = BuildConfig.AICF_API_BASE_URL.trim()
        val baseUrl = if (configured.isBlank() || configured == NOT_CONFIGURED) {
            DEFAULT_EMULATOR_BASE_URL
        } else {
            configured
        }
        return if (baseUrl.endsWith('/')) baseUrl else "$baseUrl/"
    }

    private val requestInterceptor = Interceptor { chain ->
        val builder = chain.request().newBuilder()
            .header("Accept", "application/json")
            .header("X-Request-Id", "android-${UUID.randomUUID()}")
        val token = AppContainer.apiKeyStore().getApiKey()
        if (!token.isNullOrBlank()) {
            builder.header("Authorization", "Bearer $token")
        }
        chain.proceed(builder.build())
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(requestInterceptor)
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(45, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .callTimeout(60, TimeUnit.SECONDS)
        .build()

    val apiService: FactoryApiService by lazy {
        Retrofit.Builder()
            .baseUrl(normalizedBaseUrl())
            .client(client)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
            .create(FactoryApiService::class.java)
    }
}
