package com.agent.backend.agent.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import okhttp3.*;

import java.io.Closeable;
import java.io.IOException;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.TimeUnit;

public class GeminiLiveService implements Closeable {
    private final OkHttpClient client;
    private WebSocket webSocket;
    private final ObjectMapper mapper = new ObjectMapper();
    private final BlockingQueue<String> incoming = new LinkedBlockingQueue<>();

    public GeminiLiveService() {
        this.client = new OkHttpClient.Builder()
                .callTimeout(Duration.ofSeconds(60))
                .build();
    }

    /**
     * Connects to the Gemini Live websocket.
     * IMPORTANT: Replace the URL below with the official Gemini Live websocket endpoint.
     */
    public void connect(String apiKey, String model) {
        String url = "wss://api.generativeai.google/v1/realtime?model=" + model;
        Request request = new Request.Builder()
                .url(url)
                .addHeader("Authorization", "Bearer " + apiKey)
                .build();

        this.webSocket = client.newWebSocket(request, new WebSocketListener() {
            @Override
            public void onOpen(WebSocket webSocket, Response response) {
                System.out.println("Gemini Live websocket opened: " + response);
            }

            @Override
            public void onMessage(WebSocket webSocket, String text) {
                try {
                    incoming.put(text);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }

            @Override
            public void onMessage(WebSocket webSocket, ByteString bytes) {
                // Binary frames (audio) are not handled here in this simple helper.
                onMessage(webSocket, bytes.utf8());
            }

            @Override
            public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                System.err.println("Gemini Live websocket failure: " + t.getMessage());
                if (response != null) System.err.println(response);
            }

            @Override
            public void onClosing(WebSocket webSocket, int code, String reason) {
                webSocket.close(code, reason);
            }
        });
    }

    /**
     * Send a simple text input and wait for the first textual response (blocking up to timeoutMs).
     * This is a convenience wrapper — Live API uses richer message types in production.
     */
    public String sendTextAndWaitResponse(String text, long timeoutMs) throws IOException, InterruptedException {
        if (webSocket == null) throw new IllegalStateException("WebSocket not connected");

        Map<String, Object> payload = new HashMap<>();
        payload.put("type", "input_text");
        payload.put("text", text);

        String json = mapper.writeValueAsString(payload);
        boolean sent = webSocket.send(json);
        if (!sent) throw new IOException("Failed to send message over websocket");

        String resp = incoming.poll(timeoutMs, TimeUnit.MILLISECONDS);
        return resp == null ? "" : resp;
    }

    @Override
    public void close() throws IOException {
        if (webSocket != null) {
            webSocket.close(1000, "closing");
            webSocket = null;
        }
        client.dispatcher().executorService().shutdown();
    }
}
