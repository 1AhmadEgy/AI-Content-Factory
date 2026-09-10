package com.example.data.remote

import com.example.BuildConfig
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory

object NetworkClient {
    private val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

    private fun normalizedBaseUrl(): String {
        val configured = BuildConfig.AICF_API_BASE_URL.trim()
        val value = if (configured.isBlank()) "http://10.0.2.2:8000/" else configured
        return if (value.endsWith('/')) value else "$value/"
    }

    private val authInterceptor = Interceptor { chain ->
        val builder = chain.request().newBuilder().header("Accept", "application/json")
        val token = BuildConfig.AICF_API_TOKEN.trim()
        if (token.isNotBlank()) builder.header("Authorization", "Bearer $token")
        chain.proceed(builder.build())
    }

    private val client = OkHttpClient.Builder().addInterceptor(authInterceptor).build()

    val apiService: FactoryApiService by lazy {
        Retrofit.Builder().baseUrl(normalizedBaseUrl()).client(client)
            .addConverterFactory(MoshiConverterFactory.create(moshi)).build()
            .create(FactoryApiService::class.java)
    }
}
