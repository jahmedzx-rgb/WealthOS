package com.wealthos.connect

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification

class MessagesNotificationListener : NotificationListenerService() {
    private val supportedPackages = setOf(
        "com.google.android.apps.messaging",
        "com.samsung.android.messaging",
        "com.android.messaging",
        "com.android.mms",
    )

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName !in supportedPackages) return
        val config = BridgeConfig(this)
        if (!config.paired) return
        val extras = sbn.notification.extras
        val sender = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString().orEmpty()
        val body = (extras.getCharSequence(Notification.EXTRA_BIG_TEXT)
            ?: extras.getCharSequence(Notification.EXTRA_TEXT))?.toString().orEmpty()
        val record = SmsRepository.fromNotification(
            "${sbn.packageName}:${sbn.key}:${sbn.postTime}",
            sender,
            body,
            sbn.postTime,
            // Sender authorization is enforced by the server so changes from
            // WealthOS apply immediately without re-pairing the phone.
            emptySet(),
        ) ?: return
        SmsSyncWorker.enqueue(this, record)
    }
}
