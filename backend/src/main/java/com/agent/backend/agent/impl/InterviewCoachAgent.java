package com.agent.backend.agent.impl;

import com.agent.backend.agent.AbstractAgent;
import com.agent.backend.model.AgentResponse;
import com.agent.backend.model.SessionContext;
import org.springframework.ai.chat.ChatClient;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;

@Component("InterviewCoachAgent")
public class InterviewCoachAgent extends AbstractAgent {
    private final GeminiLiveService geminiLiveService;
    private static final String DEFAULT_MODEL = "gemini-2.5-flash-native-audio-preview-12-2025";

    public InterviewCoachAgent(ChatClient chatClient) {
        super(chatClient, "You are an expert Interview Coach. Provide feedback and simulation for interview preparation.", "InterviewCoachAgent");
        this.geminiLiveService = new GeminiLiveService();
        String apiKey = System.getenv("GEMINI_API_KEY");
        if (apiKey != null && !apiKey.isEmpty()) {
            try {
                geminiLiveService.connect(apiKey, DEFAULT_MODEL);
            } catch (Exception e) {
                System.err.println("Failed to connect to Gemini Live: " + e.getMessage());
            }
        } else {
            System.out.println("GEMINI_API_KEY not set; Gemini Live will not be used.");
        }
    }

    @Override
    public AgentResponse process(String input, SessionContext context) {
        String result = callGemini(input, context);
        return AgentResponse.builder()
                .agentName(getName())
                .content(result)
                .reasoning("Generated interview coaching feedback.")
                .confidenceScore(0.85)
                .decisionTrace(new ArrayList<>())
                .sharpMetadata(new HashMap<>())
                .build();
    }

    private String callGemini(String input, SessionContext context) {
        try {
            // Send input as text and wait for a response (10s timeout)
            String raw = geminiLiveService.sendTextAndWaitResponse(input, 10_000);
            if (raw == null || raw.isEmpty()) {
                return "(No response from Gemini Live)";
            }
            // The live API returns richer messages; here we return the raw JSON string as a fallback.
            return raw;
        } catch (IOException | InterruptedException e) {
            Thread.currentThread().interrupt();
            return "Error contacting Gemini Live: " + e.getMessage();
        }
    }
}
