package com.wealthos.connect

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

class SmsSyncWorker(context: Context, params: WorkerParameters): CoroutineWorker(context, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val config = BridgeConfig(applicationContext)
        if (!config.paired || ContextCompat.checkSelfPermission(applicationContext, Manifest.permission.READ_SMS) != PackageManager.PERMISSION_GRANTED) return@withContext Result.success()
        val since = if (config.lastSyncedSmsAt > 0) maxOf(config.historySince, config.lastSyncedSmsAt - TimeUnit.MINUTES.toMillis(5)) else config.historySince
        val messages = SmsRepository.read(applicationContext, since, config.senderAllowlist)
        if (messages.isEmpty()) return@withContext Result.success()
        try {
            BridgeApi.upload(config, messages, config.lastSyncedSmsAt == 0L)
            config.lastSyncedSmsAt = messages.maxOf { it.receivedAt }
            if (messages.size >= 500) enqueueNow(applicationContext)
            Result.success()
        } catch (error: Exception) {
            if (runAttemptCount >= 8) Result.failure() else Result.retry()
        }
    }

    companion object {
        private const val PERIODIC_NAME = "wealthos-sms-periodic"
        private const val IMMEDIATE_NAME = "wealthos-sms-immediate"
        fun schedule(context: Context) {
            val request = PeriodicWorkRequestBuilder<SmsSyncWorker>(15, TimeUnit.MINUTES).build()
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(PERIODIC_NAME, ExistingPeriodicWorkPolicy.UPDATE, request)
        }
        fun enqueueNow(context: Context) {
            WorkManager.getInstance(context).enqueueUniqueWork(IMMEDIATE_NAME, ExistingWorkPolicy.APPEND_OR_REPLACE, OneTimeWorkRequestBuilder<SmsSyncWorker>().build())
        }
    }
}
