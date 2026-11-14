package com.wealthos.connect

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.provider.Settings
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.google.android.material.textfield.TextInputEditText
import com.google.android.material.textfield.TextInputLayout
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import org.json.JSONObject
import java.time.LocalDate
import java.time.ZoneId
import java.util.UUID
import kotlin.concurrent.thread

class MainActivity: AppCompatActivity() {
    private lateinit var config: BridgeConfig
    private lateinit var apiBase: EditText
    private lateinit var pairingSecret: EditText
    private lateinit var status: TextView
    private lateinit var pairButton: Button

    private val permissionLauncher = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { grants ->
        if (grants[Manifest.permission.READ_SMS] == true && grants[Manifest.permission.RECEIVE_SMS] == true) {
            SmsSyncWorker.schedule(this); SmsSyncWorker.enqueueNow(this); showStatus("SMS access granted. Historical sync started.", true)
        } else showStatus("SMS permission is required to import financial messages.", false)
    }
    private val scanLauncher = registerForActivityResult(ScanContract()) { result ->
        if (result.contents.isNullOrBlank()) return@registerForActivityResult
        runCatching {
            val payload = JSONObject(result.contents)
            apiBase.setText(payload.getString("api_base"))
            pairingSecret.setText(payload.getString("pairing_secret"))
            pair()
        }.onFailure { showStatus("This is not a valid WealthOS pairing QR code.", false) }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        config = BridgeConfig(this)
        if (config.installationId.isBlank()) config.installationId = UUID.randomUUID().toString()
        setContentView(buildContent())
        if (config.paired) {
            apiBase.setText(config.apiBase)
            pairButton.text = "Re-pair phone"
            showStatus("Connected to WealthOS. New financial messages sync automatically.", true)
            requestSmsPermissions()
        }
    }

    private fun buildContent(): ScrollView {
        val padding = (20 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(padding, padding, padding, padding); setBackgroundColor(Color.rgb(246,248,251)) }
        root.addView(TextView(this).apply { text = "WealthOS Connect"; textSize = 25f; setTextColor(Color.rgb(16,39,68)); setTypeface(typeface, android.graphics.Typeface.BOLD) })
        root.addView(TextView(this).apply { text = "Secure financial SMS bridge"; textSize = 14f; setTextColor(Color.DKGRAY); setPadding(0,0,0,padding) })
        apiBase = field(root, "WealthOS API address", "https://wealthos-web-beta.onrender.com/api/v1")
        pairingSecret = field(root, "Manual pairing code", "Paste the code from WealthOS")
        root.addView(Button(this).apply { text = "Scan pairing QR"; setOnClickListener { scanLauncher.launch(ScanOptions().setDesiredBarcodeFormats(ScanOptions.QR_CODE).setPrompt("Scan the WealthOS QR code").setBeepEnabled(false)) } }, params())
        pairButton = Button(this).apply { text = "Pair phone"; setOnClickListener { pair() } }
        root.addView(pairButton, params())
        root.addView(Button(this).apply { text = "Sync messages now"; setOnClickListener { requestSmsPermissions(); SmsSyncWorker.enqueueNow(this@MainActivity); showStatus("Sync requested.", true) } }, params())
        status = TextView(this).apply { textSize = 14f; setPadding(0,padding,0,padding) }
        root.addView(status)
        root.addView(TextView(this).apply { text = "Privacy: the app filters OTP messages on the phone, accepts only configured financial senders, and sends operations to the WealthOS review queue. Nothing is posted automatically."; textSize = 13f; setTextColor(Color.DKGRAY })
        return ScrollView(this).apply { addView(root) }
    }

    private fun field(root: LinearLayout, label: String, hint: String): EditText {
        val input = TextInputEditText(this).apply { this.hint = hint; setSingleLine(true) }
        root.addView(TextInputLayout(this).apply { this.hint = label; addView(input, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)) }, params())
        return input
    }
    private fun params() = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply { bottomMargin = (10 * resources.displayMetrics.density).toInt() }

    private fun pair() {
        val base = apiBase.text.toString().trim().trimEnd('/')
        val secret = pairingSecret.text.toString().trim()
        if (!base.startsWith("https://") || secret.length < 32) { showStatus("Scan the QR code or enter a valid HTTPS address and pairing code.", false); return }
        pairButton.isEnabled = false; showStatus("Pairing…", true)
        thread {
            runCatching { BridgeApi.claim(base, secret, android.os.Build.MODEL, config.installationId) }
                .onSuccess { result ->
                    config.apiBase = base; config.deviceId = result.deviceId; config.deviceToken = result.deviceToken; config.senderAllowlist = result.senders
                    config.historySince = LocalDate.of(2026,10,15).atStartOfDay(ZoneId.systemDefault()).toInstant().toEpochMilli()
                    runOnUiThread { pairButton.isEnabled = true; pairButton.text = "Re-pair phone"; pairingSecret.setText(""); showStatus("Phone paired. Grant SMS access to start the historical sync from 15 October 2026.", true); requestSmsPermissions() }
                }.onFailure { error -> runOnUiThread { pairButton.isEnabled = true; showStatus(error.message ?: "Pairing failed.", false) } }
        }
    }

    private fun requestSmsPermissions() {
        val missing = listOf(Manifest.permission.READ_SMS, Manifest.permission.RECEIVE_SMS).filter { ContextCompat.checkSelfPermission(this,it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isNotEmpty()) permissionLauncher.launch(missing.toTypedArray()) else { SmsSyncWorker.schedule(this); SmsSyncWorker.enqueueNow(this) }
    }
    private fun showStatus(text: String, success: Boolean) { status.text = text; status.setTextColor(if(success) Color.rgb(25,130,75) else Color.rgb(185,45,45)) }
}
