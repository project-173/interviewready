package com.agent.backend.model;

import java.util.List;

public class StructuralAssessment {

    private Double score;
    private String readability;
    private List<String> formattingRecommendations;
    private List<String> suggestions;

    public StructuralAssessment() {}

    public Double getScore() { return score; }
    public void setScore(Double score) { this.score = score; }
    public String getReadability() { return readability; }
    public void setReadability(String readability) { this.readability = readability; }
    public List<String> getFormattingRecommendations() { return formattingRecommendations; }
    public void setFormattingRecommendations(List<String> formattingRecommendations) { this.formattingRecommendations = formattingRecommendations; }
    public List<String> getSuggestions() { return suggestions; }
    public void setSuggestions(List<String> suggestions) { this.suggestions = suggestions; }
}
