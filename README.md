package com.app.ondevicellmdemo.llm.tool

/**
 * Interface definition for a tool that can be called by the LLM.
 * Each tool must define its name, description, parameters, and execution logic.
 */
interface Tool {
    val name: String
    val description: String
    val parameters: List<ToolParameter>

    /**
     * Execute the tool with the given arguments and return the result as a string.
     */
    suspend fun execute(args: Map<String, String>): String

    /**
     * Generate a compact description of this tool for the system prompt.
     * Keeps it minimal for small models like Gemma 2B.
     */
    fun getSchemaDescription(): String {
        return buildString {
            append("$name: $description")
            if (parameters.isNotEmpty()) {
                append(" Params: ")
                append(parameters.joinToString(", ") { "${it.name}=${it.type}" })
            }
        }
    }
}

/**
 * Represents a parameter definition for a tool.
 */
data class ToolParameter(
    val name: String,
    val type: String, // "string", "integer", "boolean", etc.
    val description: String,
    val required: Boolean = true
)
