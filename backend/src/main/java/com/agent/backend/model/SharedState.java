package com.agent.backend.model;

import java.util.List;

public class SharedState {

    private Resume currentResume;
    private List<Resume> history;
    private String jobDescription;
    private WorkflowStatus status;
    private StructuralAssessment criticReport;
    private ContentAnalysisReport contentReport;
    private AlignmentReport alignmentReport;
    private List<InterviewMessage> interviewHistory;

    public SharedState() {}

    public Resume getCurrentResume() { return currentResume; }
    public void setCurrentResume(Resume currentResume) { this.currentResume = currentResume; }
    public List<Resume> getHistory() { return history; }
    public void setHistory(List<Resume> history) { this.history = history; }
    public String getJobDescription() { return jobDescription; }
    public void setJobDescription(String jobDescription) { this.jobDescription = jobDescription; }
    public WorkflowStatus getStatus() { return status; }
    public void setStatus(WorkflowStatus status) { this.status = status; }
    public StructuralAssessment getCriticReport() { return criticReport; }
    public void setCriticReport(StructuralAssessment criticReport) { this.criticReport = criticReport; }
    public ContentAnalysisReport getContentReport() { return contentReport; }
    public void setContentReport(ContentAnalysisReport contentReport) { this.contentReport = contentReport; }
    public AlignmentReport getAlignmentReport() { return alignmentReport; }
    public void setAlignmentReport(AlignmentReport alignmentReport) { this.alignmentReport = alignmentReport; }
    public List<InterviewMessage> getInterviewHistory() { return interviewHistory; }
    public void setInterviewHistory(List<InterviewMessage> interviewHistory) { this.interviewHistory = interviewHistory; }
}
