package com.agent.backend.model;

import jakarta.persistence.Embeddable;
import jakarta.persistence.Column;
import java.time.LocalDate;

@Embeddable
public class Experience {

    private String title;
    private String company;
    private LocalDate startDate;
    @Column(nullable = true)
    private LocalDate endDate;
    private String description;

    public Experience() {}

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getCompany() { return company; }
    public void setCompany(String company) { this.company = company; }
    public LocalDate getStartDate() { return startDate; }
    public void setStartDate(LocalDate startDate) { this.startDate = startDate; }
    public LocalDate getEndDate() { return endDate; }
    public void setEndDate(LocalDate endDate) { this.endDate = endDate; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
}
