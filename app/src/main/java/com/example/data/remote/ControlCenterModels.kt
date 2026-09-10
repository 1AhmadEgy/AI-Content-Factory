package com.example.data.remote

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class BackendJob(val id:String,val projectId:String,val type:String,val targetType:String,val targetId:String?,val status:String,val progress:Double=0.0,val attempt:Int=0,val maxAttempts:Int=3,val provider:String?=null,val model:String?=null,val errorCode:String?=null,val errorMessage:String?=null,val createdAt:String?=null,val updatedAt:String?=null)

@JsonClass(generateAdapter = true)
data class JobsMeta(val count:Int,val limit:Int)
@JsonClass(generateAdapter = true)
data class JobsFeed(val data:List<BackendJob>,val meta:JobsMeta,val requestId:String?=null)

@JsonClass(generateAdapter = true)
data class JobEventModel(val id:String,val jobId:String,val projectId:String,val eventType:String,val status:String,val progress:Double,val payload:Map<String,Any?>=emptyMap(),val createdAt:String)
@JsonClass(generateAdapter = true)
data class JobEventsFeed(val data:List<JobEventModel>,val requestId:String?=null)

@JsonClass(generateAdapter = true)
data class ProviderRunModel(val id:String,val jobId:String,val provider:String,val model:String?,val status:String,val requestMetadata:Map<String,Any?>=emptyMap(),val responseMetadata:Map<String,Any?>=emptyMap(),val startedAt:String,val completedAt:String?,val durationMs:Long?,val errorCode:String?,val createdAt:String)
@JsonClass(generateAdapter = true)
data class ProviderRunsMeta(val count:Int,val limit:Int)
@JsonClass(generateAdapter = true)
data class ProviderRunsFeed(val data:List<ProviderRunModel>,val meta:ProviderRunsMeta,val requestId:String?=null)

@JsonClass(generateAdapter = true)
data class WorkerData(val workerId:String,val running:Boolean,val autostart:Boolean,val iterations:Int,val lastError:String?)
@JsonClass(generateAdapter = true)
data class WorkerResponse(val data:WorkerData,val requestId:String?=null)

@JsonClass(generateAdapter = true)
data class SchedulerData(val running:Boolean,val autostart:Boolean,val ticks:Int,val lastError:String?)
@JsonClass(generateAdapter = true)
data class SchedulerResponse(val data:SchedulerData,val requestId:String?=null)

@JsonClass(generateAdapter = true)
data class HealthData(val status:String,val service:String)
@JsonClass(generateAdapter = true)
data class HealthResponse(val status:String,val data:HealthData,val requestId:String?=null)
