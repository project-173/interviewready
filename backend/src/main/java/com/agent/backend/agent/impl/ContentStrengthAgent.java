package com.agent.backend.agent.impl;

import com.agent.backend.agent.AbstractAgent;
import com.agent.backend.model.AgentResponse;
import com.agent.backend.model.SessionContext;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.ai.chat.ChatClient;
import org.springframework.stereotype.Component;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Component("ContentStrengthAgent")
public class ContentStrengthAgent extends AbstractAgent {
    
    private static final String SYSTEM_PROMPT = """
        You are a Content Strength & Skills Reasoning Agent. Your role is to analyze resumes to identify key skills, achievements, and evidence of impact.
        
        ## Your Responsibilities
        1. Identify key skills and achievements from the resume
        2. Evaluate the strength of evidence supporting each claim
        3. Suggest stronger phrasing WITHOUT fabricating new content
        4. Apply confidence scoring and consistency checks
        
        ## Evidence Strength Classification
        - HIGH: Quantifiable results (e.g., "increased revenue by 25%", "led team of 12")
        - MEDIUM: Specific details but not quantified (e.g., "led cross-functional team", "implemented new system")
        - LOW: Vague claims (e.g., "improved processes", "worked on various projects")
        
        ## Faithful Transformation Rules
        - NEVER invent new skills, achievements, or experiences
        - NEVER add numbers or metrics that don't exist in the original
        - ONLY suggest phrasing that preserves the original meaning
        - FLAG any suggestion that cannot be directly traced to source content
        - If you cannot improve phrasing without fabrication, mark as faithful=false
        
        ## Output Format
        Return a JSON object with this exact structure:
        {
          "skills": [
            {
              "name": "skill name",
              "category": "Technical|Soft|Domain|Tool",
              "confidenceScore": 0.0-1.0,
              "evidenceStrength": "HIGH|MEDIUM|LOW",
              "evidence": "direct quote from resume supporting this skill"
            }
          ],
          "achievements": [
            {
              "description": "achievement description",
              "impact": "HIGH|MEDIUM|LOW",
              "quantifiable": true|false,
              "confidenceScore": 0.0-1.0,
              "originalText": "original text from resume"
            }
          ],
          "suggestions": [
            {
              "original": "original phrasing from resume",
              "suggested": "improved phrasing (must be faithful to original)",
              "rationale": "why this change improves clarity",
              "faithful": true|false,
              "confidenceScore": 0.0-1.0
            }
          ],
          "hallucinationRisk": 0.0-1.0,
          "summary": "brief summary of analysis"
        }
        
        ## Hallucination Risk Calculation
        - 0.0-0.2: All claims well-evidenced, suggestions fully faithful
        - 0.3-0.5: Some vague claims, minor rewording suggestions
        - 0.6-0.8: Multiple unsupported claims, some aggressive suggestions
        - 0.9-1.0: High risk of fabrication, flag for human review
        """;
    
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    public ContentStrengthAgent(ChatClient chatClient) {
        super(chatClient, SYSTEM_PROMPT, "ContentStrengthAgent");
    }

    @Override
    public AgentResponse process(String input, SessionContext context) {
        String rawResult = callGemini(input, context);
        
        JsonNode parsed = parseJson(rawResult);
        double overallConfidence = calculateOverallConfidence(parsed);
        double hallucinationRisk = getDoubleOrZero(parsed, "hallucinationRisk");
        String summary = getTextOrEmpty(parsed, "summary");
        
        List<String> decisionTrace = new ArrayList<>();
        decisionTrace.add("ContentStrengthAgent: Analyzed resume for skills and achievements");
        decisionTrace.add("ContentStrengthAgent: Identified " + countArray(parsed, "skills") + " skills");
        decisionTrace.add("ContentStrengthAgent: Identified " + countArray(parsed, "achievements") + " achievements");
        decisionTrace.add("ContentStrengthAgent: Generated " + countArray(parsed, "suggestions") + " suggestions");
        decisionTrace.add("ContentStrengthAgent: Hallucination risk: " + hallucinationRisk);
        
        Map<String, Object> sharpMetadata = new HashMap<>();
        sharpMetadata.put("hallucinationRisk", hallucinationRisk);
        sharpMetadata.put("overallConfidence", overallConfidence);
        
        return AgentResponse.builder()
                .agentName(getName())
                .content(rawResult)
                .reasoning(summary)
                .confidenceScore(overallConfidence)
                .decisionTrace(decisionTrace)
                .sharpMetadata(sharpMetadata)
                .build();
    }
    
    private JsonNode parseJson(String text) {
        try {
            Pattern jsonPattern = Pattern.compile("\\{[\\s\\S]*\\}", Pattern.MULTILINE);
            Matcher matcher = jsonPattern.matcher(text);
            if (matcher.find()) {
                return objectMapper.readTree(matcher.group());
            }
            return objectMapper.readTree(text);
        } catch (Exception e) {
            return objectMapper.createObjectNode();
        }
    }
    
    private double calculateOverallConfidence(JsonNode node) {
        double skillAvg = calculateArrayAverage(node, "skills", "confidenceScore");
        double achievementAvg = calculateArrayAverage(node, "achievements", "confidenceScore");
        double suggestionAvg = calculateArrayAverage(node, "suggestions", "confidenceScore");
        
        int count = 0;
        double total = 0.0;
        
        if (node.has("skills") && node.get("skills").isArray() && node.get("skills").size() > 0) {
            total += skillAvg;
            count++;
        }
        if (node.has("achievements") && node.get("achievements").isArray() && node.get("achievements").size() > 0) {
            total += achievementAvg;
            count++;
        }
        if (node.has("suggestions") && node.get("suggestions").isArray() && node.get("suggestions").size() > 0) {
            total += suggestionAvg;
            count++;
        }
        
        return count > 0 ? total / count : 0.0;
    }
    
    private double calculateArrayAverage(JsonNode parent, String arrayName, String fieldName) {
        if (!parent.has(arrayName) || !parent.get(arrayName).isArray()) {
            return 0.0;
        }
        
        double sum = 0.0;
        int count = 0;
        
        for (JsonNode item : parent.get(arrayName)) {
            if (item.has(fieldName)) {
                sum += item.get(fieldName).asDouble();
                count++;
            }
        }
        
        return count > 0 ? sum / count : 0.0;
    }
    
    private int countArray(JsonNode parent, String arrayName) {
        if (!parent.has(arrayName) || !parent.get(arrayName).isArray()) {
            return 0;
        }
        return parent.get(arrayName).size();
    }
    
    private String getTextOrEmpty(JsonNode node, String field) {
        if (node.has(field) && !node.get(field).isNull()) {
            return node.get(field).asText();
        }
        return "";
    }
    
    private double getDoubleOrZero(JsonNode node, String field) {
        if (node.has(field) && !node.get(field).isNull()) {
            return node.get(field).asDouble();
        }
        return 0.0;
    }
}
