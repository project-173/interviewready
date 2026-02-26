package com.agent.backend.model;

import java.util.List;

public class AlignmentReport {

    private Double overallScore;
    private List<String> matchingKeywords;
    private List<String> missingKeywords;
    private String roleFitAnalysis;
    private List<Source> sources;

    public AlignmentReport() {}

    public Double getOverallScore() { return overallScore; }
    public void setOverallScore(Double overallScore) { this.overallScore = overallScore; }
    public List<String> getMatchingKeywords() { return matchingKeywords; }
    public void setMatchingKeywords(List<String> matchingKeywords) { this.matchingKeywords = matchingKeywords; }
    public List<String> getMissingKeywords() { return missingKeywords; }
    public void setMissingKeywords(List<String> missingKeywords) { this.missingKeywords = missingKeywords; }
    public String getRoleFitAnalysis() { return roleFitAnalysis; }
    public void setRoleFitAnalysis(String roleFitAnalysis) { this.roleFitAnalysis = roleFitAnalysis; }
    public List<Source> getSources() { return sources; }
    public void setSources(List<Source> sources) { this.sources = sources; }
}
