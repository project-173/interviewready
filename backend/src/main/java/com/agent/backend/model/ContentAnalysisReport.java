package com.agent.backend.model;

import java.util.List;

public class ContentAnalysisReport {

    private List<String> strengths;
    private List<String> gaps;
    private List<String> skillImprovements;
    private Double quantifiedImpactScore;

    public ContentAnalysisReport() {}

    public List<String> getStrengths() { return strengths; }
    public void setStrengths(List<String> strengths) { this.strengths = strengths; }
    public List<String> getGaps() { return gaps; }
    public void setGaps(List<String> gaps) { this.gaps = gaps; }
    public List<String> getSkillImprovements() { return skillImprovements; }
    public void setSkillImprovements(List<String> skillImprovements) { this.skillImprovements = skillImprovements; }
    public Double getQuantifiedImpactScore() { return quantifiedImpactScore; }
    public void setQuantifiedImpactScore(Double quantifiedImpactScore) { this.quantifiedImpactScore = quantifiedImpactScore; }
}
