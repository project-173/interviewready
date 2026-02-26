package com.agent.backend.model;

public class InterviewMessage {

    private String role;
    private String text;

    public InterviewMessage() {}

    public InterviewMessage(String role, String text) {
        this.role = role;
        this.text = text;
    }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }
    public String getText() { return text; }
    public void setText(String text) { this.text = text; }
}
