package com.agent.backend.model;

import jakarta.persistence.Embeddable;
import jakarta.persistence.Column;
import java.time.LocalDate;

@Embeddable
public class Project {

    private String title;
    private LocalDate startDate;
    @Column(nullable = true)
    private LocalDate endDate;
    @Column(columnDefinition = "TEXT")
    private String description;

    public Project() {}

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public LocalDate getStartDate() { return startDate; }
    public void setStartDate(LocalDate startDate) { this.startDate = startDate; }
    public LocalDate getEndDate() { return endDate; }
    public void setEndDate(LocalDate endDate) { this.endDate = endDate; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
}
