package com.app.ondevicellmdemo.llm.tool

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.util.Log

class GetTemperatureTool(private val context: Context) : Tool {

    override val name = "get_temperature"

    override val description =
        "Retrieves the current device temperature in Celsius."

    override val parameters = emptyList<String>()

    override suspend fun execute(args: Map<String, String>): String {
        return try {
            val batteryStatus = context.registerReceiver(
                null,
                IntentFilter(Intent.ACTION_BATTERY_CHANGED)
            )

            val tempTenths = batteryStatus?.getIntExtra(
                BatteryManager.EXTRA_TEMPERATURE,
                0
            ) ?: 0

            val tempCelsius = tempTenths / 10.0

            "Current temperature: $tempCelsius°C"
        } catch (e: Exception) {
            Log.e("GetTemperatureTool", "Failed to retrieve temperature", e)
            "Error retrieving temperature: ${e.localizedMessage}"
        }
    }
}
