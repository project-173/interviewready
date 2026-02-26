package com.agent.backend.model;

import jakarta.persistence.Embeddable;
import jakarta.persistence.Column;
import java.time.LocalDate;

@Embeddable
public class Education {

    private String school;
    private String degree;
    private LocalDate startDate;
    @Column(nullable = true)
    private LocalDate endDate;
    private Double gpa;
    private Double gpaMax;
    private String description;

    public Education() {}

    public String getSchool() { return school; }
    public void setSchool(String school) { this.school = school; }
    public String getDegree() { return degree; }
    public void setDegree(String degree) { this.degree = degree; }
    public LocalDate getStartDate() { return startDate; }
    public void setStartDate(LocalDate startDate) { this.startDate = startDate; }
    public LocalDate getEndDate() { return endDate; }
    public void setEndDate(LocalDate endDate) { this.endDate = endDate; }
    public Double getGpa() { return gpa; }
    public void setGpa(Double gpa) { this.gpa = gpa; }
    public Double getGpaMax() { return gpaMax; }
    public void setGpaMax(Double gpaMax) { this.gpaMax = gpaMax; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
}
