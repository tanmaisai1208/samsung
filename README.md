package com.app.ondevicellmdemo.llm.tool

import android.content.Context
import android.os.BatteryManager
import android.util.Log

private val Unit.BATTERY_PROPERTY_TEMPERATURE: Int

class GetTemperatureTool(private val context: Context) : Tool {
    override val name = "get_temperature"
    override val description = "Retrieves the current device temperature in Celsius."
    override val parameters = emptyList<ToolParameter>()

    override suspend fun execute(args: Map<String, String>): String {
        return try {
            val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
            // Temperature is reported in tenths of a degree Celsius
            val tempTenths = batteryManager.getIntProperty(BatteryManager.BATTERY_PROPERTY_TEMPERATURE)
            val tempCelsius = tempTenths / 10.0
            "Current temperature: $tempCelsius°C"
        } catch (e: Exception) {
            Log.e("GetTemperatureTool", "Failed to retrieve temperature", e)
            "Error retrieving temperature: ${e.localizedMessage}"
        }
    }
}
