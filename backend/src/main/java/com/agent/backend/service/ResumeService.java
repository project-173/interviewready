package com.agent.backend.service;

import com.agent.backend.model.Resume;
import com.agent.backend.repository.ResumeRepository;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class ResumeService {

    private final ResumeRepository resumeRepository;

    public ResumeService(ResumeRepository resumeRepository) {
        this.resumeRepository = resumeRepository;
    }

    public Resume createResume(Resume resume) {
        return resumeRepository.save(resume);
    }

    public List<Resume> getAllResumes() {
        return resumeRepository.findAll();
    }

    public Optional<Resume> getResumeById(String id) {
        return resumeRepository.findById(id);
    }

    public Optional<Resume> updateResume(String id, Resume resumeDetails) {
        return resumeRepository.findById(id).map(resume -> {
            resume.setTitle(resumeDetails.getTitle());
            resume.setSummary(resumeDetails.getSummary());
            resume.setIsMaster(resumeDetails.getIsMaster());
            resume.setContact(resumeDetails.getContact());
            resume.setSkills(resumeDetails.getSkills());
            resume.setExperiences(resumeDetails.getExperiences());
            resume.setEducations(resumeDetails.getEducations());
            resume.setProjects(resumeDetails.getProjects());
            resume.setCertifications(resumeDetails.getCertifications());
            resume.setAwards(resumeDetails.getAwards());
            return resumeRepository.save(resume);
        });
    }

    public boolean deleteResume(String id) {
        return resumeRepository.findById(id).map(resume -> {
            resumeRepository.delete(resume);
            return true;
        }).orElse(false);
    }
}
