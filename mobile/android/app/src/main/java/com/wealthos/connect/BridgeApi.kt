package com.wealthos.connect

import android.os.Build
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

object BridgeApi {
    private val jsonType = "application/json; charset=utf-8".toMediaType()
    private val client = OkHttpClient.Builder().connectTimeout(20, TimeUnit.SECONDS).readTimeout(30, TimeUnit.SECONDS).build()

    data class PairResult(val deviceId: String, val deviceToken: String, val senders: Set<String>)
    data class UploadResult(val accepted: Int, val duplicates: Int, val ignored: Int)

    fun claim(apiBase: String, pairingSecret: String, deviceName: String, installationId: String): PairResult {
        val body = JSONObject()
            .put("pairing_secret", pairingSecret)
            .put("device_name", deviceName)
            .put("installation_id", installationId)
            .put("app_version", BuildConfig.VERSION_NAME)
            .put("os_version", "Android ${Build.VERSION.RELEASE}")
        val request = Request.Builder().url("${apiBase.trimEnd('/')}/mobile/pairings/claim").post(body.toString().toRequestBody(jsonType)).build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("Pairing failed (${response.code})")
            val payload = JSONObject(response.body?.string().orEmpty())
            val senders = payload.optJSONArray("sender_allowlist").toStringSet()
            return PairResult(payload.getString("device_id"), payload.getString("device_token"), senders)
        }
    }

    fun upload(config: BridgeConfig, messages: List<SmsRecord>, historySync: Boolean): UploadResult {
        val array = JSONArray()
        messages.forEach { item -> array.put(JSONObject().put("source_id", item.sourceId).put("sender", item.sender).put("body", item.body).put("received_at", item.receivedAtIso)) }
        val body = JSONObject().put("history_sync", historySync).put("messages", array)
        val request = Request.Builder()
            .url("${config.apiBase}/mobile/messages/batch")
            .header("Authorization", "Bearer ${config.deviceToken}")
            .post(body.toString().toRequestBody(jsonType)).build()
        client.newCall(request).execute().use { response ->
            if (response.code == 401) error("Device access was revoked. Pair the phone again.")
            if (!response.isSuccessful) error("Sync failed (${response.code})")
            val payload = JSONObject(response.body?.string().orEmpty())
            return UploadResult(payload.getInt("accepted"), payload.getInt("duplicates"), payload.getInt("ignored"))
        }
    }

    private fun JSONArray?.toStringSet(): Set<String> = buildSet {
        if (this@toStringSet != null) for (index in 0 until length()) add(getString(index))
    }
}
