package com.example.echo.data

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Echo backend endpoints (docs/API.md). Paths are relative to a base URL that
 * already ends in "/api/" (see [Network]). Every call returns a [Response] so
 * the repository can read the single error envelope on non-2xx (§41).
 */
interface EchoApi {

    @POST("capture")
    suspend fun capture(@Body request: CaptureRequest): Response<CaptureResponse>

    @Multipart
    @POST("capture/image")
    suspend fun captureImage(
        @Part file: MultipartBody.Part,
        @Part("source") source: RequestBody,
        @Part("note") note: RequestBody?,
    ): Response<CaptureResponse>

    @GET("jobs/{id}")
    suspend fun job(@Path("id") jobId: String): Response<JobDetail>

    @GET("memories/{id}")
    suspend fun memory(@Path("id") memoryId: String): Response<MemoryDto>

    @PATCH("memories/{id}")
    suspend fun updateMemory(
        @Path("id") memoryId: String,
        @Body body: Map<String, String>,
    ): Response<MemoryDto>

    @DELETE("memories/{id}")
    suspend fun deleteMemory(@Path("id") memoryId: String): Response<Ack>

    @POST("memories/{id}/correct")
    suspend fun correct(
        @Path("id") memoryId: String,
        @Body correction: MemoryCorrection,
    ): Response<MemoryDto>

    @GET("overview")
    suspend fun overview(): Response<OverviewResponse>

    /** The resurfacing feed the device polls; filter by status (e.g. "SENT") and pass GPS coordinates for geofencing. */
    @GET("notifications")
    suspend fun notifications(
        @Query("status") status: String? = null,
        @Query("latitude") latitude: Double? = null,
        @Query("longitude") longitude: Double? = null,
        @Query("limit") limit: Int = 50,
    ): Response<NotificationPage>

    /** Acknowledge a notification: body {"action": "acted"|"dismissed"}. */
    @POST("notifications/{id}/ack")
    suspend fun ack(
        @Path("id") id: String,
        @Body body: Map<String, String>,
    ): Response<Ack>

    /** Simulate a geofence ENTER for a specific memory (demo control, §45). */
    @POST("demo/simulate-nearby")
    suspend fun simulateNearby(
        @Body body: SimulateNearbyRequest,
    ): Response<SimulateNearbyResponse>
}

