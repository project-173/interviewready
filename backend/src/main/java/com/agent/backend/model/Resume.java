package com.agent.backend.model;

import jakarta.persistence.*;
import java.util.List;

import com.agent.backend.model.Contact;

@Entity
@Table(name = "resumes")
public class Resume {

    @Id
    private String id;
    private String title;
    private String summary;
    private Boolean isMaster;

    @ElementCollection
    private List<String> skills;

    @ElementCollection
    @CollectionTable(name = "resume_experiences", joinColumns = @JoinColumn(name = "resume_id"))
    @OrderBy("company ASC")
    private List<Experience> experiences;

    @ElementCollection
    @CollectionTable(name = "resume_educations", joinColumns = @JoinColumn(name = "resume_id"))
    @OrderBy("school ASC")
    private List<Education> educations;

    @ElementCollection
    @CollectionTable(name = "resume_projects", joinColumns = @JoinColumn(name = "resume_id"))
    @OrderBy("title ASC")
    private List<Project> projects;

    @ElementCollection
    @CollectionTable(name = "resume_certifications", joinColumns = @JoinColumn(name = "resume_id"))
    @OrderBy("name ASC")
    private List<Certification> certifications;

    @ElementCollection
    @CollectionTable(name = "resume_awards", joinColumns = @JoinColumn(name = "resume_id"))
    @OrderBy("title ASC")
    private List<Award> awards;

    @Embedded
    private Contact contact;

    public Resume() {}

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getSummary() { return summary; }
    public void setSummary(String summary) { this.summary = summary; }
    public Boolean getIsMaster() { return isMaster; }
    public void setIsMaster(Boolean isMaster) { this.isMaster = isMaster; }
    public List<String> getSkills() { return skills; }
    public void setSkills(List<String> skills) { this.skills = skills; }
    public List<Experience> getExperiences() { return experiences; }
    public void setExperiences(List<Experience> experiences) { this.experiences = experiences; }
    public List<Education> getEducations() { return educations; }
    public void setEducations(List<Education> educations) { this.educations = educations; }
    public List<Project> getProjects() { return projects; }
    public void setProjects(List<Project> projects) { this.projects = projects; }
    public List<Certification> getCertifications() { return certifications; }
    public void setCertifications(List<Certification> certifications) { this.certifications = certifications; }
    public List<Award> getAwards() { return awards; }
    public void setAwards(List<Award> awards) { this.awards = awards; }
    public Contact getContact() { return contact; }
    public void setContact(Contact contact) { this.contact = contact; }
}
