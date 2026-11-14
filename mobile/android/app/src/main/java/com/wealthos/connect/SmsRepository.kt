package com.wealthos.connect

import android.content.Context
import android.provider.Telephony
import java.time.Instant

data class SmsRecord(val sourceId: String, val sender: String, val body: String, val receivedAt: Long) {
    val receivedAtIso: String get() = Instant.ofEpochMilli(receivedAt).toString()
}

object SmsRepository {
    private val financial = Regex("transaction|purchase|payment|card|credit|debit|transfer|deposit|withdraw|balance|amount|sar|usd|عملية|شراء|دفع|سداد|بطاقة|ائتمان|مدى|حوالة|تحويل|إيداع|ايداع|سحب|رصيد|مبلغ|خصم|مشتريات|رسوم|راتب|توزيع|استلام", RegexOption.IGNORE_CASE)
    private val otp = Regex("otp|verification code|one.?time password|رمز (?:التحقق|التأكيد|التفعيل|التنشيط|لمرة واحدة)", RegexOption.IGNORE_CASE)

    fun read(context: Context, since: Long, senders: Set<String>, limit: Int = 500): List<SmsRecord> {
        val normalizedSenders = senders.map { it.trim().lowercase() }.filter { it.isNotBlank() }.toSet()
        val result = mutableListOf<SmsRecord>()
        val projection = arrayOf(Telephony.Sms._ID, Telephony.Sms.ADDRESS, Telephony.Sms.BODY, Telephony.Sms.DATE)
        context.contentResolver.query(
            Telephony.Sms.Inbox.CONTENT_URI,
            projection,
            "${Telephony.Sms.DATE} >= ?",
            arrayOf(since.toString()),
            "${Telephony.Sms.DATE} ASC",
        )?.use { cursor ->
            val idIndex = cursor.getColumnIndexOrThrow(Telephony.Sms._ID)
            val addressIndex = cursor.getColumnIndexOrThrow(Telephony.Sms.ADDRESS)
            val bodyIndex = cursor.getColumnIndexOrThrow(Telephony.Sms.BODY)
            val dateIndex = cursor.getColumnIndexOrThrow(Telephony.Sms.DATE)
            while (cursor.moveToNext() && result.size < limit) {
                val sender = cursor.getString(addressIndex).orEmpty().trim()
                val body = cursor.getString(bodyIndex).orEmpty().trim()
                val date = cursor.getLong(dateIndex)
                if (body.isBlank() || otp.containsMatchIn(body) || !financial.containsMatchIn(body)) continue
                if (normalizedSenders.isNotEmpty() && sender.lowercase() !in normalizedSenders) continue
                result += SmsRecord("${cursor.getLong(idIndex)}:$date", sender, body, date)
            }
        }
        return result
    }
}
