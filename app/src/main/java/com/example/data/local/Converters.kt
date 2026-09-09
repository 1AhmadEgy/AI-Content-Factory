package com.example.data.local

import com.example.core.model.*

import androidx.room.TypeConverter
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

class Converters {
    private val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()
    private val mapType = Types.newParameterizedType(Map::class.java, String::class.java, String::class.java)
    private val mapAdapter = moshi.adapter<Map<String, String>>(mapType)

    @TypeConverter
    fun fromStringMap(value: Map<String, String>?): String {
        return mapAdapter.toJson(value ?: emptyMap())
    }

    @TypeConverter
    fun toStringMap(value: String?): Map<String, String> {
        return if (value.isNullOrEmpty()) emptyMap() else mapAdapter.fromJson(value) ?: emptyMap()
    }

    @TypeConverter
    fun fromJobStatus(status: JobStatus): String = status.name

    @TypeConverter
    fun toJobStatus(status: String): JobStatus = enumValueOf(status)
}
