package com.wealthos.connect

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.Data
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class SmsSyncWorker(context: Context, params: WorkerParameters): CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val config = BridgeConfig(applicationContext)
        if (!config.paired) return@withContext Result.success()
        val record = SmsRepository.fromNotification(
            inputData.getString("source_id").orEmpty(),
            inputData.getString("sender").orEmpty(),
            inputData.getString("body").orEmpty(),
            inputData.getLong("received_at", System.currentTimeMillis()),
            // The API owns the live sender allowlist. Keep only the financial
            // and OTP filters on-device before the encrypted upload.
            emptySet(),
        ) ?: return@withContext Result.success()
        try {
            BridgeApi.upload(config, listOf(record), false)
            Result.success()
        } catch (error: Exception) {
            if (runAttemptCount >= 8) Result.failure() else Result.retry()
        }
    }

    companion object {
        fun enqueue(context: Context, record: SmsRecord) {
            val input = Data.Builder()
                .putString("source_id", record.sourceId)
                .putString("sender", record.sender)
                .putString("body", record.body)
                .putLong("received_at", record.receivedAt)
                .build()
            val request = OneTimeWorkRequestBuilder<SmsSyncWorker>().setInputData(input).build()
            WorkManager.getInstance(context).enqueueUniqueWork("wealthos-message-${record.sourceId.hashCode()}", ExistingWorkPolicy.KEEP, request)
        }
    }
}
