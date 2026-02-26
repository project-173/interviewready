package com.agent.backend.repository;

import com.agent.backend.model.SharedState;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SharedStateRepository extends JpaRepository<SharedState, Long> {
}
