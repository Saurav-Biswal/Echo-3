package com.example.echo.data

import com.example.echo.BuildConfig
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import java.util.concurrent.TimeUnit

/**
 * Lazily-built Retrofit stack. No secrets live here - the app only ever talks
 * to the Echo backend, which holds the Gemini key server-side.
 */
object Network {

    /** Tolerant decoder: unknown/new backend fields and enum values never crash the app. */
    val json: Json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
        explicitNulls = false
        isLenient = true
    }

    private val client: OkHttpClient by lazy {
        val builder = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            // Identify the user to the backend when configured; blank => demo user.
            .addInterceptor { chain ->
                val request = chain.request()
                val withUser = if (BuildConfig.ECHO_USER.isNotBlank()) {
                    request.newBuilder()
                        .header("X-Echo-User", BuildConfig.ECHO_USER)
                        .build()
                } else {
                    request
                }
                chain.proceed(withUser)
            }
        if (BuildConfig.DEBUG) {
            builder.addInterceptor(
                HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC }
            )
        }
        builder.build()
    }

    val api: EchoApi by lazy {
        Retrofit.Builder()
            .baseUrl(normalizedBaseUrl(BuildConfig.ECHO_BASE_URL))
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(EchoApi::class.java)
    }

    /** Ensures the base URL ends in "/api/" so relative endpoint paths resolve. */
    private fun normalizedBaseUrl(raw: String): String {
        val root = raw.trimEnd('/')
        return if (root.endsWith("/api")) "$root/" else "$root/api/"
    }
}
