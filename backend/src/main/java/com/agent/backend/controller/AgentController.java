package com.agent.backend.controller;

import com.agent.backend.model.AgentResponse;
import com.agent.backend.model.ChatRequest;
import com.agent.backend.model.SessionContext;
import com.agent.backend.orchestration.OrchestrationAgent;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.bind.annotation.*;
import java.util.Map;
import java.util.HashMap;
import java.util.concurrent.ConcurrentHashMap;

@RestController
@RequestMapping("/api/v1")
public class AgentController {

    private final OrchestrationAgent orchestrator;
    private final Map<String, SessionContext> sessions = new ConcurrentHashMap<>();

    public AgentController(OrchestrationAgent orchestrator) {
        this.orchestrator = orchestrator;
    }

    @PostMapping("/chat")
    public AgentResponse chat(@RequestParam String sessionId, @RequestBody ChatRequest request) {
        // Get Firebase UID from Security Context
        var auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !auth.isAuthenticated()) {
            throw new RuntimeException("Unauthenticated request. Please check if Firebase is enabled/disabled correctly.");
        }
        
        String userId = (String) auth.getPrincipal();
        
        SessionContext context = sessions.computeIfAbsent(sessionId, k -> {
            SessionContext ctx = new SessionContext();
            ctx.setSessionId(k);
            ctx.setUserId(userId); // Track user ownership
            return ctx;
        });
        
        // Security check: Ensure user owns the session
        if (!context.getUserId().equals(userId)) {
            throw new RuntimeException("Unauthorized access to session");
        }
        
        return orchestrator.orchestrate(request.getMessage(), context);
    }

    @GetMapping("/agents")
    public Map<String, String> listAgents() {
        Map<String, String> agentPrompts = new HashMap<>();
        orchestrator.getAgents().forEach((name, agent) -> 
            agentPrompts.put(name, agent.getSystemPrompt())
        );
        return agentPrompts;
    }
}
