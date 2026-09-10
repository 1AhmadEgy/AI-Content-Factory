package com.example.data.local

import com.example.core.model.*
import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface FactoryDao {
    @Query("SELECT * FROM projects")
    fun getAllProjects(): Flow<List<Project>>
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProject(project: Project)

    @Query("SELECT * FROM series")
    fun getAllSeries(): Flow<List<Series>>
    @Query("SELECT * FROM series WHERE id = :id LIMIT 1")
    suspend fun getSeries(id: String): Series?
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertSeries(series: Series)

    @Query("SELECT * FROM episodes")
    fun getAllEpisodes(): Flow<List<Episode>>
    @Query("SELECT * FROM episodes WHERE id = :id LIMIT 1")
    suspend fun getEpisode(id: String): Episode?
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertEpisode(episode: Episode)

    @Query("SELECT * FROM scenes")
    fun getAllScenes(): Flow<List<Scene>>
    @Query("SELECT * FROM scenes WHERE id = :id LIMIT 1")
    suspend fun getScene(id: String): Scene?
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertScene(scene: Scene)
    @Update
    suspend fun updateScene(scene: Scene)

    @Query("SELECT * FROM characters")
    fun getAllCharacters(): Flow<List<Character>>
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertCharacter(character: Character)

    @Query("SELECT * FROM locations")
    fun getAllLocations(): Flow<List<Location>>
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLocation(location: Location)

    @Query("SELECT * FROM shots")
    fun getAllShots(): Flow<List<Shot>>
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertShot(shot: Shot)

    @Query("SELECT * FROM jobs")
    fun getAllJobs(): Flow<List<GenerationJob>>
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertJob(job: GenerationJob)
    @Update
    suspend fun updateJob(job: GenerationJob)
}
