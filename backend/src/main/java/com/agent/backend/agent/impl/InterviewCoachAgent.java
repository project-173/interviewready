package com.agent.backend.agent.impl;

import com.agent.backend.agent.AbstractAgent;
import com.agent.backend.model.AgentResponse;
import com.agent.backend.model.SessionContext;
import org.springframework.ai.chat.ChatClient;
import org.springframework.stereotype.Component;
import java.util.ArrayList;
import java.util.HashMap;

@Component("InterviewCoachAgent")
public class InterviewCoachAgent extends AbstractAgent {
    public InterviewCoachAgent(ChatClient chatClient) {
        super(chatClient, "You are an expert Interview Coach. Provide feedback and simulation for interview preparation.", "InterviewCoachAgent");
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
}
