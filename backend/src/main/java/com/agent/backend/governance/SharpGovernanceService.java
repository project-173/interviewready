package com.agent.backend.governance;

import com.agent.backend.model.AgentResponse;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.stereotype.Service;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.HashSet;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.regex.Pattern;
import java.util.regex.Matcher;

@Service
public class SharpGovernanceService {
    
    private static final double CONFIDENCE_THRESHOLD = 0.3;
    private static final double HALLUCINATION_RISK_THRESHOLD = 0.7;
    
    private static final Set<String> QUANTIFIABLE_PATTERNS = Set.of(
            "\\d+%", "\\$\\d+", "\\d+\\s*(years?|months?|weeks?)", 
            "\\d+\\s*(people|team members|employees)",
            "\\d+\\s*(projects?|clients?|customers?)",
            "increased?\\s+by\\s+\\d+", "reduced?\\s+by\\s+\\d+",
            "saved\\s+\\d+", "improved\\s+.*\\d+"
    );
    
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AgentResponse audit(AgentResponse response, String originalInput) {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("governance_audit", "passed");
        metadata.put("audit_timestamp", System.currentTimeMillis());
        
        boolean hallucinationCheck = checkHallucination(response, originalInput);
        metadata.put("hallucination_check_passed", hallucinationCheck);
        
        boolean confidenceCheck = checkConfidenceThreshold(response);
        metadata.put("confidence_check_passed", confidenceCheck);
        
        if ("ContentStrengthAgent".equals(response.getAgentName())) {
            validateContentStrengthAgent(response, metadata, originalInput);
        }
        
        List<String> flags = new ArrayList<>();
        if (!hallucinationCheck) flags.add("hallucination_risk");
        if (!confidenceCheck) flags.add("low_confidence");
        
        if (!flags.isEmpty()) {
            metadata.put("governance_audit", "flagged");
            metadata.put("audit_flags", flags);
        }
        
        response.setSharpMetadata(metadata);
        return response;
    }
    
    public AgentResponse audit(AgentResponse response) {
        return audit(response, null);
    }
    
    private boolean checkHallucination(AgentResponse response, String originalInput) {
        if (originalInput == null || originalInput.isEmpty()) {
            return true;
        }
        
        if (response.getSharpMetadata() != null && 
            response.getSharpMetadata().containsKey("hallucinationRisk")) {
            double risk = ((Number) response.getSharpMetadata().get("hallucinationRisk")).doubleValue();
            return risk < HALLUCINATION_RISK_THRESHOLD;
        }
        
        return true;
    }
    
    private boolean checkConfidenceThreshold(AgentResponse response) {
        return response.getConfidenceScore() >= CONFIDENCE_THRESHOLD;
    }
    
    private void validateContentStrengthAgent(AgentResponse response, Map<String, Object> metadata, String originalInput) {
        try {
            JsonNode content = parseContentJson(response.getContent());
            
            if (content == null || content.isNull()) {
                metadata.put("content_parse_error", true);
                return;
            }
            
            double hallucinationRisk = getDoubleOrZero(content, "hallucinationRisk");
            metadata.put("hallucinationRisk", hallucinationRisk);
            metadata.put("hallucination_check_passed", hallucinationRisk < HALLUCINATION_RISK_THRESHOLD);
            
            JsonNode suggestions = content.get("suggestions");
            if (suggestions != null && suggestions.isArray()) {
                long unfaithfulCount = 0;
                for (JsonNode suggestion : suggestions) {
                    if (suggestion.has("faithful") && !suggestion.get("faithful").asBoolean()) {
                        unfaithfulCount++;
                    }
                }
                metadata.put("unfaithful_suggestions", unfaithfulCount);
                metadata.put("total_suggestions", suggestions.size());
                
                if (unfaithfulCount > 0) {
                    metadata.put("governance_audit", "flagged");
                    metadata.put("audit_flags", List.of("unfaithful_suggestions", "requires_human_review"));
                }
            }
            
            JsonNode achievements = content.get("achievements");
            if (achievements != null && achievements.isArray()) {
                boolean hasQuantified = false;
                for (JsonNode achievement : achievements) {
                    if (achievement.has("quantifiable") && achievement.get("quantifiable").asBoolean()) {
                        hasQuantified = true;
                        break;
                    }
                }
                metadata.put("has_quantified_achievements", hasQuantified);
            }
            
            JsonNode skills = content.get("skills");
            if (skills != null && skills.isArray()) {
                long highEvidenceSkills = 0;
                for (JsonNode skill : skills) {
                    if (skill.has("evidenceStrength") && 
                        "HIGH".equalsIgnoreCase(skill.get("evidenceStrength").asText())) {
                        highEvidenceSkills++;
                    }
                }
                metadata.put("high_evidence_skills_count", highEvidenceSkills);
            }
            
        } catch (Exception e) {
            metadata.put("validation_error", e.getMessage());
        }
    }
    
    private JsonNode parseContentJson(String content) {
        if (content == null || content.isEmpty()) {
            return null;
        }
        try {
            Pattern jsonPattern = Pattern.compile("\\{[\\s\\S]*\\}", Pattern.MULTILINE);
            Matcher matcher = jsonPattern.matcher(content);
            if (matcher.find()) {
                return objectMapper.readTree(matcher.group());
            }
            return objectMapper.readTree(content);
        } catch (Exception e) {
            return null;
        }
    }
    
    private double getDoubleOrZero(JsonNode node, String field) {
        if (node != null && node.has(field) && !node.get(field).isNull()) {
            return node.get(field).asDouble();
        }
        return 0.0;
    }
    
    public boolean containsQuantifiableClaim(String text) {
        if (text == null || text.isEmpty()) {
            return false;
        }
        
        for (String pattern : QUANTIFIABLE_PATTERNS) {
            Pattern p = Pattern.compile(pattern, Pattern.CASE_INSENSITIVE);
            if (p.matcher(text).find()) {
                return true;
            }
        }
        return false;
    }
    
    public double calculateHallucinationRisk(String original, String generated) {
        if (original == null || generated == null) {
            return 1.0;
        }
        
        double risk = 0.0;
        
        Set<String> originalWords = extractSignificantWords(original);
        Set<String> generatedWords = extractSignificantWords(generated);
        
        Set<String> newWords = new HashSet<>(generatedWords);
        newWords.removeAll(originalWords);
        
        if (!generatedWords.isEmpty()) {
            risk = (double) newWords.size() / generatedWords.size() * 0.5;
        }
        
        if (containsNewNumbers(original, generated)) {
            risk += 0.3;
        }
        
        if (containsNewProperNouns(original, generated)) {
            risk += 0.2;
        }
        
        return Math.min(risk, 1.0);
    }
    
    private Set<String> extractSignificantWords(String text) {
        Set<String> words = new HashSet<>();
        String[] tokens = text.toLowerCase().split("[^a-z0-9]+");
        for (String token : tokens) {
            if (token.length() > 3) {
                words.add(token);
            }
        }
        return words;
    }
    
    private boolean containsNewNumbers(String original, String generated) {
        Pattern numberPattern = Pattern.compile("\\d+");
        
        Set<String> originalNumbers = new HashSet<>();
        Matcher originalMatcher = numberPattern.matcher(original);
        while (originalMatcher.find()) {
            originalNumbers.add(originalMatcher.group());
        }
        
        Matcher generatedMatcher = numberPattern.matcher(generated);
        while (generatedMatcher.find()) {
            if (!originalNumbers.contains(generatedMatcher.group())) {
                return true;
            }
        }
        
        return false;
    }
    
    private boolean containsNewProperNouns(String original, String generated) {
        Pattern properNounPattern = Pattern.compile("\\b[A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*\\b");
        
        Set<String> originalNouns = new HashSet<>();
        Matcher originalMatcher = properNounPattern.matcher(original);
        while (originalMatcher.find()) {
            originalNouns.add(originalMatcher.group().toLowerCase());
        }
        
        Matcher generatedMatcher = properNounPattern.matcher(generated);
        while (generatedMatcher.find()) {
            if (!originalNouns.contains(generatedMatcher.group().toLowerCase())) {
                return true;
            }
        }
        
        return false;
    }
}
