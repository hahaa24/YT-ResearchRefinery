### **Project Brief: YT-Research-Refinery**

#### **1. Project Vision**

To create **YT-Research-Refinery**, a self-hostable, secure, and user-friendly web application. The application's purpose is to empower users to extract transcripts from YouTube videos, leverage Large Language Models (LLMs) to clean and synthesize this information, and produce refined, interconnected knowledge documents in Markdown format. The primary goals are ease of installation via Docker, a simple and powerful WebUI, and robust, maintainable backend services.

#### **2. Core Features & User Stories**

*   **F1: LLM Configuration**
    *   **User Story:** As a user, I want a settings page in the WebUI where I can securely input my API keys and select my preferred LLM provider (OpenAI, Anthropic, Ollama) so the application can make API calls on my behalf.

*   **F2: Cost Management**
    *   **User Story:** As a user, before I execute an expensive LLM operation, I want to see an estimated cost for the task and be able to set a maximum cost limit to prevent unexpected charges.

*   **F3: Single Video Processor**
    *   **User Story:** As a user, I want to provide a single YouTube URL, have the system fetch its transcript, and then use my configured LLM to generate a concise summary of the content.

*   **F4: Research Cluster**
    *   **User Story:** As a researcher, I want to input a list of YouTube URLs on a specific topic to create a "Research Cluster." The system should allow me to save and resume my work on this cluster.
    *   **User Story:** As a researcher, I want an optional feature to use an LLM to "clean" the raw transcripts, removing sponsorships, intros, outros, and filler words to improve the quality of the source material.
    *   **User Story:** As a researcher, I want to trigger a final analysis that processes all cleaned transcripts in a cluster to produce a single, consolidated report. This report must include an introduction, key takeaways, actionable steps, a section analyzing contradictions or pro/con arguments, and a conclusion.

*   **F5: Output & Integration**
    *   **User Story:** As a user, I want all generated transcripts and summaries to be available for download as `.md` files directly from the WebUI.
    *   **User Story:** As a user, I want the application to automatically save all generated Markdown files to a local `./output` directory so I have a persistent archive of my work.
    *   **User Story:** As an Obsidian user, I want key concepts in the generated Markdown to be automatically formatted as `[[WikiLinks]]` to build a knowledge graph when I open the `./output` directory as a vault.

#### **3. Technical Architecture & Stack**

*   **System Components (Dockerized):**
    1.  **Web App (FastAPI):** The primary service running the Python backend. It serves the UI, handles user requests, and dispatches long-running jobs.
    2.  **Worker (Celery):** A separate service that executes time-consuming tasks (e.g., fetching transcripts, calling LLMs) asynchronously to keep the Web App responsive.
    3.  **Cache (Redis):** A Redis instance acting as the message broker for Celery and as a database for caching session data (e.g., Research Cluster state).

*   **Technology Stack:**
    *   **Backend:** **FastAPI** (for modern, async Python web development).
    *   **Frontend:** **HTMX** (for creating a dynamic UI without complex JavaScript).
    *   **Containerization:** **Docker & Docker Compose** (for reproducible environments and simple deployment).
    *   **LLM Abstraction:** **LiteLLM** (to provide a unified interface for multiple LLM providers).
    *   **Task Queue & Cache:** **Celery & Redis**.

#### **4. Project Structure & Conventions**

The project will be organized in a git repository with the following structure:

```
/
├── .dockerignore
├── .env.example            # Template for environment variables
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── README.md
├── requirements.txt
├── setup.sh                # Interactive setup script
└── src/
    ├── __init__.py
    ├── main.py             # FastAPI application entrypoint and routes
    ├── core/               # Core business logic
    │   ├── llm_services.py # Logic for LiteLLM, cost estimation, cleaning
    │   └── youtube_services.py # Logic for fetching transcripts
    ├── models.py           # Pydantic models for data validation
    ├── templates/          # HTMX/HTML templates
    │   ├── base.html
    │   └── ...
    └── worker.py           # Celery worker definition and tasks
```

#### **5. Security, Configuration & Deployment**

*   **Secrets Management:** All sensitive data (API keys) will be managed via a `.env` file, which is explicitly excluded from version control by `.gitignore`. A `.env.example` file will serve as a template.
*   **Gitignore:** A comprehensive `.gitignore` file will be included to exclude the `.env` file, logs, Python virtual environments, cache files, and the `./output` directory.
*   **Deployment:** The application is intended to be run via `docker-compose up`. An interactive `setup.sh` script will be created to:
    1.  Copy `.env.example` to `.env`.
    2.  Allow the user to specify a custom port.
    3.  (Optional) Guide the user through running Certbot to generate SSL certificates for a custom domain.

#### **6. Implementation Plan (Milestones)**

**Milestone 1: Project Scaffolding & Containerization**
1.  Initialize the git repository.
2.  Create the file structure outlined in section 4.
3.  Create a comprehensive `.gitignore` file.
4.  Create the `.env.example` file with placeholders for API keys and `APP_PORT`.
5.  Create a `Dockerfile` that sets up a Python environment and installs `requirements.txt`.
6.  Create a `docker-compose.yml` file defining the `web-app`, `worker`, and `redis` services.
7.  Implement a basic "Hello World" FastAPI endpoint in `src/main.py` that serves a simple `index.html`.
8.  Ensure `docker-compose up` successfully builds and runs the services.

**Milestone 2: Core Services & Configuration UI**
1.  Implement structured logging to the container's standard output.
2.  In `src/core/llm_services.py`, create a wrapper function around LiteLLM to handle API calls.
3.  In `src/core/youtube_services.py`, implement a function to fetch video transcripts.
4.  Create the `/settings` page (`settings.html` and FastAPI routes) to allow users to set their LLM provider and API key (values will be handled as environment variables, not saved in a database).
5.  Implement the cost estimation logic based on token count.

**Milestone 3: Single Video Feature**
1.  Create the UI for the "Single Video" feature.
2.  In `src/worker.py`, define a Celery task `generate_single_summary(video_url)`. This task will:
    *   Fetch the transcript.
    *   Generate a summary using the configured LLM.
    *   Save the result to the `./output` directory.
3.  In `src/main.py`, create API endpoints to:
    *   Dispatch the Celery task.
    *   Allow the frontend to poll for the task's result.
4.  Implement the "Download" button on the frontend.

**Milestone 4: Research Cluster (Ingestion & State)**
1.  Design a data structure (e.g., a Python dictionary) to represent a Research Cluster's state and define how it will be stored in Redis (e.g., using a session ID as the key).
2.  Create the UI for creating/loading clusters and adding URLs.
3.  In `src/worker.py`, create a Celery task `process_cluster_transcripts(session_id)` that fetches all transcripts for a given cluster and updates its state in Redis.
4.  Implement the optional "Clean Transcripts" feature as another Celery task that operates on the fetched transcripts.
5.  Update the UI to show the real-time status of transcript processing.

**Milestone 5: Research Cluster (Synthesis & Linking)**
1.  Engineer the final, detailed prompt for the synthesis LLM call.
2.  In `src/worker.py`, create the final Celery task `synthesize_cluster_report(session_id)`.
3.  Implement the logic to identify keywords and convert them into `[[WikiLinks]]` in the final Markdown output.
4.  Save the final report to the `./output` directory.
5.  Add the final "Download Report" button to the UI.

**Milestone 6: Deployment & Finalization**
1.  Develop the `setup.sh` script to automate the configuration process.
2.  Thoroughly test all features, including the cost-limiting mechanism and error handling for invalid URLs or failed API calls.
3.  Write the final `README.md`, including a project description, feature list, and clear, step-by-step instructions for installation and usage, complemented by screenshots or GIFs.
4.  Ensure the entire application is stable and provides a polished user experience.