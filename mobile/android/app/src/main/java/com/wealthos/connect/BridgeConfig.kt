package com.wealthos.connect

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.time.LocalDate
import java.time.ZoneId

class BridgeConfig(context: Context) {
    private val prefs = EncryptedSharedPreferences.create(
        context,
        "wealthos-connect-secure",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    var apiBase: String
        get() = prefs.getString("api_base", "") ?: ""
        set(value) = prefs.edit().putString("api_base", value.trimEnd('/')).apply()
    var deviceToken: String
        get() = prefs.getString("device_token", "") ?: ""
        set(value) = prefs.edit().putString("device_token", value).apply()
    var deviceId: String
        get() = prefs.getString("device_id", "") ?: ""
        set(value) = prefs.edit().putString("device_id", value).apply()
    var installationId: String
        get() = prefs.getString("installation_id", "") ?: ""
        set(value) = prefs.edit().putString("installation_id", value).apply()
    var senderAllowlist: Set<String>
        get() = prefs.getStringSet("sender_allowlist", emptySet()) ?: emptySet()
        set(value) = prefs.edit().putStringSet("sender_allowlist", value).apply()
    var historySince: Long
        get() = prefs.getLong("history_since", LocalDate.of(2026, 10, 15).atStartOfDay(ZoneId.systemDefault()).toInstant().toEpochMilli())
        set(value) = prefs.edit().putLong("history_since", value).apply()
    var lastSyncedSmsAt: Long
        get() = prefs.getLong("last_synced_sms_at", 0L)
        set(value) = prefs.edit().putLong("last_synced_sms_at", value).apply()

    val paired: Boolean get() = apiBase.startsWith("https://") && deviceToken.isNotBlank()
}
