```mermaid
erDiagram
    USERS ||--o{ DOCUMENTS : has
    USERS ||--o{ CHAT_SESSIONS : has
    DOCUMENTS ||--o{ ANALYSIS_RESULTS : has
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : has

    USERS {
        uuid user_id PK
        text user_name
        datetime created_at
    }

    DOCUMENTS {
        uuid document_id PK
        uuid user_id FK
        string title
        text content
        datetime created_at
    }

    ANALYSIS_RESULTS {
        uuid result_id PK
        uuid document_id FK
        json scores
        json corrections
        json agent_results
        datetime created_at
    }

    CHAT_SESSIONS {
        uuid session_id PK
        uuid user_id FK
        uuid document_id FK
        datetime created_at
    }

    CHAT_MESSAGES {
        uuid message_id PK
        uuid session_id FK
        string role
        text content
        datetime created_at
    }