# Deployment Guide

This project is configured to deploy to **Google Cloud Run** via **GitHub Actions**.

## Infrastructure Requirements

1.  **GCP Project**: A Google Cloud Project with billing enabled.
2.  **Artifact Registry**: A Docker repository named `interviewready-repo` in `asia-southeast1`.
3.  **Service Account**: A service account with the following roles:
    - `Cloud Run Admin`
    - `Artifact Registry Writer`
    - `Service Account User` (to act as the runtime service account)
    - `Storage Admin` (optional, for registry management)
4.  **GitHub Secrets**: The following secrets must be added to your GitHub repository:
    - `GCP_PROJECT_ID`: Your GCP Project ID.
    - `GCP_SA_KEY`: The JSON key of your service account.
    - `GOOGLE_AI_API_KEY`: Your Gemini/Google AI API Key.
    - `LANGFUSE_PUBLIC_KEY`: (Optional) Langfuse Public Key.
    - `LANGFUSE_SECRET_KEY`: (Optional) Langfuse Secret Key.
    - `LANGFUSE_HOST`: (Optional) Langfuse Host (defaults to https://cloud.langfuse.com).

## Agentic AI Observability with Langfuse

We have integrated **Langfuse** for agentic AI observability. It provides:
- **Tracing**: Full trace of LangGraph agent workflows.
- **Cost Tracking**: Monitor Gemini token usage.
- **Evaluations**: Human-in-the-loop and LLM-as-a-judge evaluations.

To view traces, log in to your Langfuse dashboard. The backend automatically initializes the `CallbackHandler` if keys are provided.

## CI/CD Pipeline

The GitHub Action in `.github/workflows/deploy.yml` triggers on every push to `main`.

1.  **Builds** the Backend and Frontend Docker images.
2.  **Injects** the Backend URL into the Frontend build.
3.  **Pushes** images to GCP Artifact Registry.
4.  **Deploys** the Backend first, then the Frontend to Cloud Run.

## Manual Setup Commands

If you need to set up the infrastructure via CLI:

```bash
# Enable APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

# Create Artifact Registry
gcloud artifacts repositories create interviewready-repo --repository-format=docker --location=asia-southeast1

# Create Service Account
gcloud iam service-accounts create github-deployer --display-name="GitHub Deployer"

# Add Roles (replace [PROJECT_ID] and [SA_EMAIL])
gcloud projects add-iam-policy-binding [PROJECT_ID] --member="serviceAccount:[SA_EMAIL]" --role="roles/run.admin"
gcloud projects add-iam-policy-binding [PROJECT_ID] --member="serviceAccount:[SA_EMAIL]" --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding [PROJECT_ID] --member="serviceAccount:[SA_EMAIL]" --role="roles/iam.serviceAccountUser"
```
