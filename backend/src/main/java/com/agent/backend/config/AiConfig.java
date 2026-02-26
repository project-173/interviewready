package com.agent.backend.config;

import com.google.auth.oauth2.GoogleCredentials;
import org.springframework.ai.chat.ChatClient;
import org.springframework.ai.vertexai.gemini.VertexAiGeminiChatClient;
import com.google.cloud.vertexai.VertexAI;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;

import java.io.IOException;
import java.util.Collections;

@Configuration
public class AiConfig {

    @Value("${spring.ai.vertex.ai.gemini.project-id}")
    private String projectId;

    @Value("${spring.ai.vertex.ai.gemini.location}")
    private String location;

    @Value("${spring.ai.vertex.ai.gemini.chat.options.model}")
    private String modelName;

    @Value("${firebase.config.path}")
    private String credentialsPath;

    @Bean
    @Primary
    public ChatClient chatClient(ResourceLoader resourceLoader) throws IOException {
        Resource resource = resourceLoader.getResource(credentialsPath);
        GoogleCredentials credentials = GoogleCredentials.fromStream(resource.getInputStream())
                .createScoped(Collections.singletonList("https://www.googleapis.com/auth/cloud-platform"));

        System.out.println("AI Config: Loading Vertex AI with Model: " + modelName);
        VertexAI vertexAI = new VertexAI(projectId, location, credentials);
        
        return new VertexAiGeminiChatClient(vertexAI, 
            org.springframework.ai.vertexai.gemini.VertexAiGeminiChatOptions.builder()
                .withModel(modelName)
                .build());
    }
}
