package com.agent.backend.model;

import jakarta.persistence.Embeddable;
import jakarta.persistence.Column;
import java.time.LocalDate;

@Embeddable
public class Award {

    private String title;
    private String issuer;
    @Column(nullable = true)
    private LocalDate date;
    @Column(columnDefinition = "TEXT")
    private String description;

    public Award() {}

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getIssuer() { return issuer; }
    public void setIssuer(String issuer) { this.issuer = issuer; }
    public LocalDate getDate() { return date; }
    public void setDate(LocalDate date) { this.date = date; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
}
