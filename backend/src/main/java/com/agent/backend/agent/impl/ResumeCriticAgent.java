package com.agent.backend.agent.impl;

import com.agent.backend.agent.AbstractAgent;
import com.agent.backend.model.AgentResponse;
import com.agent.backend.model.SessionContext;
import org.springframework.ai.chat.ChatClient;
import org.springframework.stereotype.Component;
import java.util.ArrayList;
import java.util.HashMap;

@Component("ResumeCriticAgent")
public class ResumeCriticAgent extends AbstractAgent {
    public ResumeCriticAgent(ChatClient chatClient) {
        super(chatClient, "You are an expert Resume Critic. Analyze the resume for structure, ATS compatibility, and impact.", "ResumeCriticAgent");
    }

    @Override
    public AgentResponse process(String input, SessionContext context) {
        String result = callGemini(input, context);
        return AgentResponse.builder()
                .agentName(getName())
                .content(result)
                .reasoning("Analyzed resume structure and content impact.")
                .confidenceScore(0.9)
                .decisionTrace(new ArrayList<>())
                .sharpMetadata(new HashMap<>())
                .build();
    }
}
