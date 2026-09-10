package com.example.data.remote

import okhttp3.ConnectionPool
import okhttp3.OkHttpClient
import com.squareup.moshi.Moshi
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit

object NetworkClient {
    // 10.0.2.2 points to localhost of the host machine from the Android emulator.
    // Replace with your actual backend URL or IP when running on physical device or cloud.
    private const val BASE_URL = "http://10.0.2.2:8000/"

    // All current API DTOs use Moshi code generation (@JsonClass(generateAdapter = true)),
    // so reflection is unnecessary and can be removed from the hot startup path.
    private val moshi = Moshi.Builder().build()

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .callTimeout(35, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .connectionPool(ConnectionPool(8, 5, TimeUnit.MINUTES))
        .build()

    val apiService: FactoryApiService by lazy(LazyThreadSafetyMode.SYNCHRONIZED) {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(httpClient)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
            .create(FactoryApiService::class.java)
    }
}
