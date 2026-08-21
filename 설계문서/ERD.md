```mermaid
erDiagram
    USERS ||--o{ ANALYSIS_SESSIONS : has
    USERS |o..o{ PROBLEMS : made
    USERS ||--o{ USER_SKILL_REPORTS : has
    USERS ||--o{ COACH_MESSAGES : receives
    PROBLEMS ||--|{ RUBRICS : has
    USER_SKILL_REPORTS o|--o{ PROBLEMS : generates
    ANALYSIS_SESSIONS ||--o{ USER_ANSWERS : has
    USER_ANSWERS ||--o| ANALYSIS_RESULTS : graded
    USER_SKILL_REPORTS ||--o{ COACH_MESSAGES : delivers
    PROBLEMS ||..o{ ANALYSIS_SESSIONS : referenced
    ANALYSIS_RESULTS ||--o| CHAT_SESSIONS : has
    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : has

    USERS {
        uuid id PK
        text user_name
        datetime created_at
    }

    PROBLEMS {
        uuid id PK
        string title
        bool created_by_user
        uuid user_id FK "nullable"
        uuid source_report_id FK "nullable"
        string university "nullable"
        int year "nullable"
        text content
        text model_answer "nullable"
    }

    RUBRICS {
        uuid id PK
        uuid problem_id FK
        string criteria
        text description "nullable"
    }

    ANALYSIS_SESSIONS {
        uuid id PK
        uuid user_id FK
        uuid problem_id FK
        datetime created_at
    }

    USER_ANSWERS {
        uuid id PK
        uuid session_id FK
        text user_answer
        string status
    }

    ANALYSIS_RESULTS {
        uuid id PK
        uuid answer_id FK
        json grammar_result
        json criteria_scores
        text overall_comment
        datetime created_at
    }

    USER_SKILL_REPORTS {
        uuid id PK
        uuid user_id FK
        string period_type
        datetime period_start
        datetime period_end
        int review_count
        json skill_scores
        text overall_skill_comment
        text next_learning_goal
        json recommended_actions
        datetime created_at
    }

    COACH_MESSAGES {
        uuid id PK
        uuid user_id FK
        uuid skill_report_id FK
        string recipient_email
        string message_type
        string title
        text content
        string status
        datetime scheduled_at
        datetime sent_at
        datetime created_at
    }

    CHAT_SESSIONS {
        uuid id PK
        uuid result_id FK
        datetime created_at
    }

    CHAT_MESSAGES {
        uuid id PK
        uuid chat_id FK
        string role
        text content
        datetime created_at
    }
```
