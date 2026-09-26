package com.example.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.example.core.model.*

@Database(
    entities = [
        Project::class, Series::class, Episode::class, Scene::class,
        Character::class, Location::class, Shot::class, GenerationJob::class, Asset::class,
    ],
    version = 2,
    exportSchema = false,
)
@TypeConverters(Converters::class)
abstract class FactoryDatabase : RoomDatabase() {
    abstract fun factoryDao(): FactoryDao
    abstract fun assetDao(): AssetDao

    companion object {
        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("""
                    CREATE TABLE IF NOT EXISTS assets (
                        id TEXT NOT NULL PRIMARY KEY,
                        projectId TEXT NOT NULL,
                        type TEXT NOT NULL,
                        mimeType TEXT NOT NULL,
                        fileName TEXT NOT NULL,
                        relativePath TEXT NOT NULL,
                        sizeBytes INTEGER NOT NULL,
                        sha256 TEXT NOT NULL,
                        width INTEGER,
                        height INTEGER,
                        durationMs INTEGER,
                        createdAt INTEGER NOT NULL,
                        status TEXT NOT NULL
                    )
                """.trimIndent())
                db.execSQL("CREATE INDEX IF NOT EXISTS index_assets_projectId ON assets(projectId)")
                db.execSQL("CREATE INDEX IF NOT EXISTS index_assets_sha256 ON assets(sha256)")
                db.execSQL("CREATE INDEX IF NOT EXISTS index_assets_projectId_status ON assets(projectId, status)")
            }
        }

        @Volatile private var INSTANCE: FactoryDatabase? = null

        fun getDatabase(context: Context): FactoryDatabase =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    FactoryDatabase::class.java,
                    "factory_database",
                )
                    .addMigrations(MIGRATION_1_2)
                    .build()
                    .also { INSTANCE = it }
            }
    }
}
