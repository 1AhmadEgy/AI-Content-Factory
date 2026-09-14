package com.example.data.remote

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

    private val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

    private fun normalizedBaseUrl(): String {
        val configured = BuildConfig.AICF_API_BASE_URL.trim()
        check(configured.isNotBlank() && configured != NOT_CONFIGURED) {
            "AICF_API_BASE_URL is not configured. Configure the backend URL for this build."
        }
        return if (configured.endsWith('/')) configured else "$configured/"
    }

    private val requestInterceptor = Interceptor { chain ->
        val builder = chain.request().newBuilder()
            .header("Accept", "application/json")
            .header("X-Request-Id", "android-${UUID.randomUUID()}")
        val token = BuildConfig.AICF_API_TOKEN.trim()
        if (token.isNotBlank() && token != NOT_CONFIGURED) {
            builder.header("Authorization", "Bearer $token")
        }
        chain.proceed(builder.build())
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(requestInterceptor)
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .callTimeout(45, TimeUnit.SECONDS)
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
