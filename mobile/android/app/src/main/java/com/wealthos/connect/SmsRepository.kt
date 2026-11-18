package com.wealthos.connect

import java.time.Instant

data class SmsRecord(val sourceId: String, val sender: String, val body: String, val receivedAt: Long) {
    val receivedAtIso: String get() = Instant.ofEpochMilli(receivedAt).toString()
}

object SmsRepository {
    private val financial = Regex("transaction|purchase|payment|card|credit|debit|transfer|deposit|withdraw|balance|amount|sar|usd|عملية|شراء|دفع|سداد|بطاقة|ائتمان|مدى|حوالة|تحويل|إيداع|ايداع|سحب|رصيد|مبلغ|خصم|مشتريات|رسوم|راتب|توزيع|استلام", RegexOption.IGNORE_CASE)
    private val otp = Regex("otp|verification code|one.?time password|رمز (?:التحقق|التأكيد|التفعيل|التنشيط|لمرة واحدة)", RegexOption.IGNORE_CASE)

    fun fromNotification(sourceId: String, sender: String, body: String, receivedAt: Long, senders: Set<String>): SmsRecord? {
        val normalizedSenders = senders.map { it.trim().lowercase() }.filter { it.isNotBlank() }.toSet()
        val cleanSender = sender.trim()
        val cleanBody = body.trim()
        if (cleanBody.isBlank() || otp.containsMatchIn(cleanBody) || !financial.containsMatchIn(cleanBody)) return null
        if (normalizedSenders.isNotEmpty() && cleanSender.lowercase() !in normalizedSenders) return null
        return SmsRecord(sourceId, cleanSender, cleanBody, receivedAt)
    }
}
