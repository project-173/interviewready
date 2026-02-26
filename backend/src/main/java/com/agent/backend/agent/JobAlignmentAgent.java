package com.agent.backend.agent;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.stereotype.Component;

import com.agent.backend.model.AgentResponse;
import com.agent.backend.model.SessionContext;

@Component
public class JobAlignmentAgent implements BaseAgent {

    private String systemPrompt;

    public JobAlignmentAgent() {
        this.systemPrompt = """
            You are a Job Description Alignment Agent.

            Compare the candidate resume against the job description.

            Return structured JSON with:
            - skillsMatch (list)
            - missingSkills (list)
            - experienceMatch (summary)
            - fitScore (0-100 integer)
            - reasoning (short explanation)
        """;
    }
    
    @Override
    public String getName() {
        return "JobAlignmentAgent";
    }

    private String getFinalPrompt(String resume, String jobDesc) {
        String resumePrompt = "Resume is: " + resume + "\n\n Job Description is: " + jobDesc;
        this.systemPrompt = systemPrompt + "\n\n" + resumePrompt;

        return systemPrompt;
    }

    @Override
    public AgentResponse process(String input, SessionContext context) {

        // String finalPrompt = getFinalPrompt(input, input);

        // String rawOutput = callLLM(finalPrompt);

        // // ---- Parse LLM JSON (assume you use Gson) ----
        // Map<String, Object> parsed = parseJson(rawOutput);

        // List<String> skillsMatch = (List<String>) parsed.getOrDefault("skillsMatch", new ArrayList<>());
        // List<String> missingSkills = (List<String>) parsed.getOrDefault("missingSkills", new ArrayList<>());
        // int fitScore = ((Number) parsed.getOrDefault("fitScore", 50)).intValue();
        // String reasoning = (String) parsed.getOrDefault("reasoning", "No reasoning provided.");

        // // ---- Confidence logic ----
        // double confidence = computeConfidence(fitScore, missingSkills);

        // // ---- Decision trace ----
        // List<String> trace = new ArrayList<>();
        // trace.add("Parsed LLM output");
        // trace.add("Identified " + skillsMatch.size() + " matching skills");
        // trace.add("Identified " + missingSkills.size() + " missing skills");
        // trace.add("Computed fit score: " + fitScore);

        // // ---- Metadata ----
        // Map<String, Object> metadata = new HashMap<>();
        // metadata.put("fitScore", fitScore);
        // metadata.put("skillsMatch", skillsMatch);
        // metadata.put("missingSkills", missingSkills);
        // metadata.put("agentVersion", "1.0");

        return new AgentResponse(
                getName(),
                buildHumanReadableOutput(fitScore, skillsMatch, missingSkills),
                reasoning,
                confidence,
                trace,
                metadata
        );
    }

    @Override
    public void updateSystemPrompt(String newPrompt) {
        this.systemPrompt = newPrompt;
    }

    @Override
    public String getSystemPrompt() {
        return this.systemPrompt;
    }

    private String callLLM(String prompt) {
        
        return """
        {
            "skillsMatch": ["Java", "Spring Boot"],
            "missingSkills": ["AWS", "Kubernetes"],
            "experienceMatch": "Strong backend experience",
            "fitScore": 78,
            "reasoning": "Good backend alignment but missing cloud exposure."
        }
        """;
    }

    private Map<String, Object> parseJson(String json) {
        try {
            return new com.google.gson.Gson().fromJson(json, Map.class);
        } catch (Exception e) {
            return new HashMap<>();
        }
    }

    private double computeConfidence(int fitScore, List<String> missingSkills) {
        double base = fitScore / 100.0;
        double penalty = missingSkills.size() * 0.02;
        return Math.max(0.3, Math.min(0.95, base - penalty));
    }

    private String buildHumanReadableOutput(int fitScore, List<String> matched, List<String> missing) {

        return """
                JD Alignment Summary
                --------------------
                Fit Score: %d/100

                Matched Skills:
                %s

                Missing Skills:
                %s
                """.formatted(
                fitScore,
                String.join(", ", matched),
                String.join(", ", missing)
        );
    }

}
