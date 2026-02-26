package com.agent.backend.agent.impl;

import com.agent.backend.agent.AbstractAgent;
import com.agent.backend.model.AgentResponse;
import com.agent.backend.model.SessionContext;
import org.springframework.ai.chat.ChatClient;
import org.springframework.stereotype.Component;
import java.util.ArrayList;
import java.util.HashMap;

@Component("JobAlignmentAgent")
public class JobAlignmentAgent extends AbstractAgent {
    public JobAlignmentAgent(ChatClient chatClient) {
        super(chatClient, "You are a Job Alignment specialist. Evaluate how well a resume matches a specific job description.", "JobAlignmentAgent");
    }

    @Override
    public AgentResponse process(String input, SessionContext context) {
        String result = callGemini(input, context);
        return AgentResponse.builder()
                .agentName(getName())
                .content(result)
                .reasoning("Evaluated alignment between resume and job description.")
                .confidenceScore(0.88)
                .decisionTrace(new ArrayList<>())
                .sharpMetadata(new HashMap<>())
                .build();
    }
}
