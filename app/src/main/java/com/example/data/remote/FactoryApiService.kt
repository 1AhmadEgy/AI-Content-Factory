package com.example.data.remote

import com.example.core.model.EpisodeCreateRequest
import com.example.core.model.ProjectCreateRequest
import com.example.core.model.SeriesCreateRequest
import com.example.core.model.SceneCreateRequest
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface FactoryApiService {
    @POST("api/v1/projects") suspend fun createProject(@Body request: ProjectCreateRequest): ProjectEnvelope
    @GET("api/v1/jobs/{job_id}") suspend fun getJob(@Path("job_id") jobId: String): JobEnvelope
    @GET("api/v1/jobs") suspend fun listJobs(@Query("projectId") projectId: String? = null, @Query("status") status: String? = null, @Query("limit") limit: Int = 50): JobsFeed
    @POST("api/v1/jobs") suspend fun createJob(@Body request: CreateJobRequest, @Header("Idempotency-Key") idempotencyKey: String): JobEnvelope
    @POST("api/v1/jobs/{job_id}/cancel") suspend fun cancelJob(@Path("job_id") jobId: String): JobEnvelope
    @POST("api/v1/jobs/{job_id}/pause") suspend fun pauseJob(@Path("job_id") jobId: String): JobEnvelope
    @POST("api/v1/jobs/{job_id}/resume") suspend fun resumeJob(@Path("job_id") jobId: String): JobEnvelope
    @POST("api/v1/jobs/{job_id}/retry") suspend fun retryJob(@Path("job_id") jobId: String): JobEnvelope
    @GET("api/v1/jobs/{job_id}/events") suspend fun getJobEvents(@Path("job_id") jobId: String, @Query("limit") limit: Int = 200): JobEventsFeed
    @GET("api/v1/jobs/{job_id}/provider-runs") suspend fun getProviderRuns(@Path("job_id") jobId: String, @Query("limit") limit: Int = 50): ProviderRunsFeed

    @GET("api/v1/characters") suspend fun listCharacters(@Query("projectId") projectId: String? = null, @Query("limit") limit: Int = 100): CharacterListEnvelope
    @GET("api/v1/characters/{character_id}") suspend fun getCharacter(@Path("character_id") characterId: String): CharacterEnvelope
    @GET("api/v1/locations") suspend fun listLocations(@Query("projectId") projectId: String? = null, @Query("limit") limit: Int = 100): LocationListEnvelope
    @POST("api/v1/shots/compose") suspend fun composeShot(@Body request: ComposeShotRequest): ComposeShotEnvelope

    @GET("api/v1/library/countries") suspend fun listCountryLibraries(): CountryLibrariesEnvelope
    @GET("api/v1/library/countries/{country_id}") suspend fun getCountryLibrary(@Path("country_id") countryId: String): CountryLibraryEnvelope
    @GET("api/v1/library/countries/{country_id}/content") suspend fun getCountryLibraryContent(@Path("country_id") countryId: String): CountryLibraryContentEnvelope
    @GET("api/v1/library/countries/{country_id}/languages") suspend fun getCountryLanguages(@Path("country_id") countryId: String): LanguagesEnvelope
    @GET("api/v1/library/languages") suspend fun listLanguages(): LanguagesEnvelope

    @GET("api/v1/translations/languages") suspend fun listTranslationLanguages(): LanguagesEnvelope
    @GET("api/v1/translations") suspend fun listTranslations(@Query("sourceId") sourceId: String? = null, @Query("targetLanguage") targetLanguage: String? = null, @Query("limit") limit: Int = 100): TranslationsEnvelope
    @POST("api/v1/translations") suspend fun translate(@Body request: TranslationRequest): TranslationEnvelope
    @POST("api/v1/translations/batch") suspend fun translateBatch(@Body request: TranslationBatchRequest): TranslationBatchEnvelope
    @GET("api/v1/translations/{translation_id}") suspend fun getTranslation(@Path("translation_id") translationId: String): TranslationEnvelope

    @GET("api/v1/series/templates") suspend fun listSeriesTemplates(): SeriesTemplatesEnvelope
    @GET("api/v1/series/templates/{template_id}") suspend fun getSeriesTemplate(@Path("template_id") templateId: String): SeriesTemplateEnvelope
    @POST("api/v1/series/projects/{project_id}/apply-template") suspend fun applySeriesTemplate(@Path("project_id") projectId: String, @Body request: ApplySeriesTemplateRequest): SeriesContextEnvelope
    @GET("api/v1/series/projects/{project_id}/context") suspend fun getSeriesContext(@Path("project_id") projectId: String): SeriesContextEnvelope
    @PATCH("api/v1/series/projects/{project_id}/context") suspend fun patchSeriesContext(@Path("project_id") projectId: String, @Body request: SeriesContextPatchRequest): SeriesContextEnvelope
    @POST("api/v1/series/projects/{project_id}/translate") suspend fun translateSeries(@Path("project_id") projectId: String, @Body request: SeriesTranslationRequest): SeriesTranslationEnvelope
    @POST("api/v1/series/projects/{project_id}/episodes/{episode_id}/snapshot") suspend fun snapshotEpisodeContext(@Path("project_id") projectId: String, @Path("episode_id") episodeId: String): EpisodeSnapshotEnvelope
    @GET("api/v1/series/projects/{project_id}/snapshots") suspend fun listSeriesSnapshots(@Path("project_id") projectId: String): SeriesSnapshotsEnvelope

    @GET("api/v1/health") suspend fun health(): HealthResponse
    @GET("api/v1/worker/status") suspend fun workerStatus(): WorkerResponse
}
