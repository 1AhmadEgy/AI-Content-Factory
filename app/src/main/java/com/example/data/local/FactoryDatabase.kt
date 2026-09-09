package com.example.data.local

import com.example.core.model.*

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters

@Database(entities = [Project::class, Series::class, Episode::class, Scene::class, Character::class, Location::class, Shot::class, GenerationJob::class], version = 1, exportSchema = false)
@TypeConverters(Converters::class)
abstract class FactoryDatabase : RoomDatabase() {
    abstract fun factoryDao(): FactoryDao

    companion object {
        @Volatile
        private var INSTANCE: FactoryDatabase? = null

        fun getDatabase(context: Context): FactoryDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    FactoryDatabase::class.java,
                    "factory_database"
                ).build()
                INSTANCE = instance
                instance
            }
        }
    }
}
