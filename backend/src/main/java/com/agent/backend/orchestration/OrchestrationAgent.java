package com.agent.backend.orchestration;

import com.agent.backend.agent.BaseAgent;
import com.agent.backend.model.AgentResponse;
import com.agent.backend.model.SessionContext;
import com.agent.backend.governance.SharpGovernanceService;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.List;
import java.util.Map;
import java.util.ArrayList;
import java.util.stream.Collectors;

@Service
public class OrchestrationAgent {
    private final Map<String, BaseAgent> agents;
    private final SharpGovernanceService governance;

    @Autowired
    public OrchestrationAgent(List<BaseAgent> agentList, SharpGovernanceService governance) {
        this.agents = agentList.stream()
                .collect(Collectors.toMap(BaseAgent::getName, agent -> agent));
        this.governance = governance;
    }

    public AgentResponse orchestrate(String input, SessionContext context) {
        // 1. Decide which agent to run (Simplified Routing)
        String targetAgent = route(input);
        BaseAgent agent = agents.get(targetAgent);
        
        // 2. Execute Agent
        AgentResponse response = agent.process(input, context);
        
        // 3. Add Traceability
        List<String> trace = new ArrayList<>(context.getDecisionTrace());
        trace.add("Routed to " + targetAgent + " based on intent analysis.");
        response.setDecisionTrace(trace);
        
        // 4. Apply SHARP Governance
        AgentResponse auditedResponse = governance.audit(response);
        
        // 5. Update Shared Context
        context.addToHistory(auditedResponse);
        context.setDecisionTrace(trace);
        
        return auditedResponse;
    }

    private String route(String input) {
        if (input.toLowerCase().contains("interview")) return "InterviewCoachAgent";
        if (input.toLowerCase().contains("job")) return "JobAlignmentAgent";
        return "ResumeCriticAgent";
    }

    public Map<String, BaseAgent> getAgents() { return agents; }
}
