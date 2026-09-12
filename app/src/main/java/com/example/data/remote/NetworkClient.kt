package com.example.data.remote

import android.content.Context
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
    private const val PREFS_NAME = "network_settings"
    private const val API_BASE_URL_KEY = "api_base_url"

    private val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()
    private var service: FactoryApiService? = null
    private var serviceBaseUrl: String? = null
    private var baseUrlOverride: String? = null

    private fun normalizeBaseUrl(value: String): String {
        val configured = value.trim()
        check(configured.isNotBlank() && configured != NOT_CONFIGURED) {
            "Backend URL is not configured. Set it in Control Center."
        }
        val uri = runCatching { URI(configured) }.getOrElse {
            throw IllegalArgumentException("Invalid backend URL: $configured", it)
        }
        check(uri.scheme.equals("http", ignoreCase = true) || uri.scheme.equals("https", ignoreCase = true)) {
            "Backend URL must use http:// or https://"
        }
        check(!uri.host.isNullOrBlank() || !uri.rawAuthority.isNullOrBlank()) {
            "Backend URL must include a host"
        }
        return if (configured.endsWith('/')) configured else "$configured/"
    }

    fun initialize(context: Context) {
        val stored = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .getString(API_BASE_URL_KEY, null)
            ?.trim()
            .orEmpty()
        synchronized(this) {
            baseUrlOverride = stored.takeIf { it.isNotBlank() }?.let(::normalizeBaseUrl)
            service = null
            serviceBaseUrl = null
        }
    }

    fun getConfiguredBaseUrl(context: Context): String = synchronized(this) {
        baseUrlOverride ?: BuildConfig.AICF_API_BASE_URL.trim().let { if (it == NOT_CONFIGURED) "" else it }
    }

    fun setBaseUrl(context: Context, value: String) {
        val normalized = normalizeBaseUrl(value)
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(API_BASE_URL_KEY, normalized)
            .apply()
        synchronized(this) {
            baseUrlOverride = normalized
            service = null
            serviceBaseUrl = null
        }
    }

    fun resetBaseUrl(context: Context) {
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            .edit()
            .remove(API_BASE_URL_KEY)
            .apply()
        synchronized(this) {
            baseUrlOverride = null
            service = null
            serviceBaseUrl = null
        }
    }

    private fun configuredBaseUrl(): String = synchronized(this) {
        normalizeBaseUrl(baseUrlOverride ?: BuildConfig.AICF_API_BASE_URL)
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

    val apiService: FactoryApiService
        get() = synchronized(this) {
            val baseUrl = configuredBaseUrl()
            service?.takeIf { serviceBaseUrl == baseUrl } ?: Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(client)
                .addConverterFactory(MoshiConverterFactory.create(moshi))
                .build()
                .create(FactoryApiService::class.java)
                .also {
                    service = it
                    serviceBaseUrl = baseUrl
                }
        }
}
