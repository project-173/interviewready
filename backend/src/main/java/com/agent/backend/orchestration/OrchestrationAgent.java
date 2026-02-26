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
import java.util.LinkedList;
import java.util.Queue;
import java.util.stream.Collectors;

@Service
public class OrchestrationAgent {
    private final Map<String, BaseAgent> agents;
    private final SharpGovernanceService governance;
    private final ChatClient chatClient;
    
    private static final String INTENT_ANALYSIS_PROMPT = """
        You are an intent classifier for a multi-agent resume analysis system. Analyze the user's input and determine which agent(s) should handle it.
        
        Available agents:
        - ResumeCriticAgent: General resume analysis, structure, ATS compatibility, overall feedback
        - JobAlignmentAgent: Matching resume to specific job descriptions, gap analysis
        - InterviewCoachAgent: Interview preparation, mock interviews, behavioral questions
        - ContentStrengthAgent: Skill extraction, evidence evaluation, phrasing improvements, strength analysis
        
        Respond with ONLY a JSON array of agent names in execution order, e.g.: ["ResumeCriticAgent", "ContentStrengthAgent"]
        
        Rules:
        - For general resume questions, use ResumeCriticAgent
        - For skill/strength/achievement analysis, use ContentStrengthAgent
        - For job matching questions, use JobAlignmentAgent
        - For interview preparation, use InterviewCoachAgent
        - Multiple agents can be chained: ResumeCriticAgent can be followed by ContentStrengthAgent for detailed analysis
        - Consider conversation context when determining intent
        
        User input: %s
        
        Previous context: %s
        
        Respond with ONLY the JSON array, no other text.
        """;

    public OrchestrationAgent(List<BaseAgent> agentList, SharpGovernanceService governance, ChatClient chatClient) {
        this.agents = agentList.stream()
                .collect(Collectors.toMap(BaseAgent::getName, agent -> agent));
        this.governance = governance;
        this.chatClient = chatClient;
    }

    public AgentResponse orchestrate(String input, SessionContext context) {
        List<String> agentSequence = analyzeIntent(input, context);
        
        if (agentSequence.isEmpty()) {
            agentSequence.add("ResumeCriticAgent");
        }
        
        AgentResponse currentResponse = null;
        String currentInput = input;
        
        for (String agentName : agentSequence) {
            BaseAgent agent = agents.get(agentName);
            
            if (agent == null) {
                throw new RuntimeException("No agent found for target: " + agentName + ". Available agents: " + agents.keySet());
            }
            
            currentResponse = agent.process(currentInput, context);
            
            List<String> trace = new ArrayList<>(context.getDecisionTrace());
            trace.add("Orchestrator: Routed to " + agentName + " based on intent analysis.");
            currentResponse.setDecisionTrace(trace);
            
            currentResponse = governance.audit(currentResponse, currentInput);
            
            context.addToHistory(currentResponse);
            context.setDecisionTrace(trace);
            
            if (agentSequence.indexOf(agentName) < agentSequence.size() - 1) {
                currentInput = buildChainedInput(input, currentResponse, agentName);
            }
        }
        
        return currentResponse;
    }
    
    private List<String> analyzeIntent(String input, SessionContext context) {
        if (input == null || input.trim().isEmpty()) {
            return List.of("ResumeCriticAgent");
        }
        
        String lowerInput = input.toLowerCase();
        
        if (lowerInput.contains("skill") || lowerInput.contains("strength") || 
            lowerInput.contains("phrasing") || lowerInput.contains("achievement") ||
            lowerInput.contains("evidence") || lowerInput.contains("improve my resume")) {
            return List.of("ContentStrengthAgent");
        }
        
        if (lowerInput.contains("interview") || lowerInput.contains("mock") || 
            lowerInput.contains("behavioral") || lowerInput.contains("practice")) {
            return List.of("InterviewCoachAgent");
        }
        
        if (lowerInput.contains("job") || lowerInput.contains("alignment") || 
            lowerInput.contains("match") || lowerInput.contains("gap")) {
            return List.of("JobAlignmentAgent");
        }
        
        if (lowerInput.contains("analyze") || lowerInput.contains("critique") || 
            lowerInput.contains("review") || lowerInput.contains("feedback")) {
            if (context.getHistory().isEmpty()) {
                return List.of("ResumeCriticAgent", "ContentStrengthAgent");
            }
            return List.of("ResumeCriticAgent");
        }
        
        return analyzeIntentWithLlm(input, context);
    }
    
    private List<String> analyzeIntentWithLlm(String input, SessionContext context) {
        try {
            String contextSummary = context.getHistory().isEmpty() ? 
                    "No previous interactions" : 
                    context.getHistory().size() + " previous agent interactions";
            
            String promptText = String.format(INTENT_ANALYSIS_PROMPT, input, contextSummary);
            
            SystemMessage systemMessage = new SystemMessage("You are an intent classifier. Respond with ONLY a JSON array of agent names.");
            UserMessage userMessage = new UserMessage(promptText);
            
            String response = chatClient.call(new Prompt(List.of(systemMessage, userMessage)))
                    .getResult().getOutput().getContent();
            
            return parseAgentSequence(response);
            
        } catch (Exception e) {
            return List.of("ResumeCriticAgent");
        }
    }
    
    private List<String> parseAgentSequence(String response) {
        List<String> agents = new ArrayList<>();
        
        response = response.trim();
        if (response.startsWith("[")) {
            response = response.substring(1);
        }
        if (response.endsWith("]")) {
            response = response.substring(0, response.length() - 1);
        }
        
        String[] parts = response.split(",");
        for (String part : parts) {
            String agent = part.trim().replace("\"", "").replace("'", "");
            if (isValidAgent(agent)) {
                agents.add(agent);
            }
        }
        
        if (agents.isEmpty()) {
            agents.add("ResumeCriticAgent");
        }
        
        return agents;
    }
    
    private boolean isValidAgent(String agentName) {
        return agents.containsKey(agentName);
    }
    
    private String buildChainedInput(String originalInput, AgentResponse previousResponse, String previousAgent) {
        StringBuilder chainedInput = new StringBuilder();
        chainedInput.append("Original request: ").append(originalInput).append("\n\n");
        chainedInput.append("Previous analysis from ").append(previousAgent).append(":\n");
        chainedInput.append(previousResponse.getContent()).append("\n\n");
        chainedInput.append("Continue analysis based on the above context.");
        return chainedInput.toString();
    }

    public Map<String, BaseAgent> getAgents() { return agents; }
}
