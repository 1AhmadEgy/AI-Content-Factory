package com.example.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import com.example.core.model.*

@Database(
    entities = [
        Project::class,
        Series::class,
        Episode::class,
        Scene::class,
        Character::class,
        Location::class,
        Shot::class,
        GenerationJob::class,
    ],
    version = 1,
    exportSchema = false,
)
@TypeConverters(Converters::class)
abstract class FactoryDatabase : RoomDatabase() {
    abstract fun factoryDao(): FactoryDao

    companion object {
        @Volatile
        private var INSTANCE: FactoryDatabase? = null

        fun getDatabase(context: Context): FactoryDatabase {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    FactoryDatabase::class.java,
                    "factory_database",
                )
                    // Prevent an app-start crash when a future schema version is installed
                    // without a migration. This intentionally prioritizes a usable app over
                    // preserving incompatible local data; proper migrations should be added
                    // before production schema changes.
                    .fallbackToDestructiveMigration()
                    .build()
                    .also { INSTANCE = it }
            }
        }
    }
}
