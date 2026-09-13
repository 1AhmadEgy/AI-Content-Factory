package com.example.data.remote

import com.example.BuildConfig
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import java.net.URI
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
        val uri = URI(configured)
        check(uri.scheme.equals("https", ignoreCase = true)) {
            "AICF_API_BASE_URL must use HTTPS. Cleartext HTTP is disabled for production security."
        }
        check(uri.userInfo.isNullOrBlank()) {
            "AICF_API_BASE_URL must not embed credentials in the URL."
        }
        return if (configured.endsWith('/')) configured else "$configured/"
    }

    private val authInterceptor = Interceptor { chain ->
        val builder = chain.request().newBuilder().header("Accept", "application/json")
        val token = BuildConfig.AICF_API_TOKEN.trim()
        if (token.isNotBlank() && token != NOT_CONFIGURED) {
            builder.header("Authorization", "Bearer $token")
        }
        chain.proceed(builder.build())
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .callTimeout(45, TimeUnit.SECONDS)
        .build()

    val apiService: FactoryApiService by lazy {
        Retrofit.Builder().baseUrl(normalizedBaseUrl()).client(client)
            .addConverterFactory(MoshiConverterFactory.create(moshi)).build()
            .create(FactoryApiService::class.java)
    }
}
