package com.agent.backend.orchestration;

import com.agent.backend.agent.BaseAgent;
import com.agent.backend.model.AgentResponse;
import com.agent.backend.model.SessionContext;
import com.agent.backend.governance.SharpGovernanceService;
import org.springframework.ai.chat.ChatClient;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.chat.messages.SystemMessage;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.stereotype.Service;
import java.util.List;
import java.util.Map;
import java.util.ArrayList;
import java.util.stream.Collectors;

@Service
public class OrchestrationAgent {
    private final Map<String, BaseAgent> agents;
    private final SharpGovernanceService governance;
    private final ChatClient chatClient;

    private static final String ROUTER_PROMPT = 
        "You are an AI Router for a career assistance system. Your job is to analyze the user's input and " +
        "decide which agent should handle the request. Return ONLY the name of the agent.\n\n" +
        "Available Agents:\n" +
        "1. ResumeCriticAgent: Use for resume reviews, structure analysis, formatting, or general resume feedback.\n" +
        "2. InterviewCoachAgent: Use for interview preparation, mock interviews, or coaching advice.\n" +
        "3. JobAlignmentAgent: Use for matching a resume to a job description or evaluating fit for a specific role.\n\n" +
        "Rules:\n" +
        "- If unsure, default to ResumeCriticAgent.\n" +
        "- Return ONLY the agent name string (e.g., 'InterviewCoachAgent'). No preamble or explanation.";

    public OrchestrationAgent(List<BaseAgent> agentList, SharpGovernanceService governance, ChatClient chatClient) {
        this.agents = agentList.stream()
                .collect(Collectors.toMap(BaseAgent::getName, agent -> agent));
        this.governance = governance;
        this.chatClient = chatClient;
    }

    public AgentResponse orchestrate(String input, SessionContext context) {
        // 1. Decide which agent to run (LLM Routing)
        String targetAgent = route(input);
        BaseAgent agent = agents.get(targetAgent);
        
        if (agent == null) {
            // Fallback if LLM returns something weird
            targetAgent = "ResumeCriticAgent";
            agent = agents.get(targetAgent);
        }
        
        // 2. Execute Agent
        AgentResponse response = agent.process(input, context);
        
        // 3. Add Traceability
        List<String> trace = new ArrayList<>(context.getDecisionTrace());
        trace.add("LLM Routed to " + targetAgent + " based on intent analysis.");
        response.setDecisionTrace(trace);
        
        // 4. Apply SHARP Governance
        AgentResponse auditedResponse = governance.audit(response);
        
        // 5. Update Shared Context
        context.addToHistory(auditedResponse);
        context.setDecisionTrace(trace);
        
        return auditedResponse;
    }

    private String route(String input) {
        if (input == null || input.trim().isEmpty()) return "ResumeCriticAgent";
        
        try {
            SystemMessage systemMessage = new SystemMessage(ROUTER_PROMPT);
            UserMessage userMessage = new UserMessage("User Input: " + input);
            
            String decision = chatClient.call(new Prompt(List.of(systemMessage, userMessage)))
                    .getResult().getOutput().getContent().trim();
            
            // Clean up LLM response just in case it added punctuation
            decision = decision.replaceAll("[^a-zA-Z]", "");
            
            if (agents.containsKey(decision)) {
                return decision;
            }
        } catch (Exception e) {
            System.err.println("Routing failed: " + e.getMessage());
        }
        
        return "ResumeCriticAgent";
    }

    public Map<String, BaseAgent> getAgents() { return agents; }
}
