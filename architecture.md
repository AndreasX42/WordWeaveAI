# WordWeaveAI Architecture

```mermaid
graph TB
    %% User Layer
    Users["Users"]

    %% Frontend & Load Balancer
    ALB["Application Load Balancer"]
    Frontend["Angular Frontend<br/>ECS Fargate"]
    RestAPI["Go REST API<br/>ECS Fargate"]

    %% Processing Pipeline
    SQS["SQS Queue"]
    VocabLambda["Vocab Lambda<br/>(LangGraph Agent)"]

    %% WebSocket Real-time Flow
    WSGateway["WebSocket API Gateway"]
    WSHandler["WebSocket Handler<br/>(Connect/Disconnect/Subscribe)"]
    WSNotifier["WebSocket Notifier<br/>(Streaming Updates)"]

    %% Data Layer
    DynamoUsers["DynamoDB Users"]
    DynamoVocab["DynamoDB Vocabulary"]
    DynamoWS["DynamoDB WebSocket<br/>Connections"]
    S3Audio["S3 Media Files"]

    %% External APIs
    OpenAI["OpenAI API"]
    ElevenLabs["ElevenLabs API"]
    Pexels["Pexels API"]

    %% Main Flow
    Users --> ALB
    ALB --> Frontend
    Frontend --> RestAPI
    RestAPI --> SQS
    RestAPI --> DynamoUsers
    RestAPI --> DynamoVocab

    %% Processing Flow
    SQS --> VocabLambda
    VocabLambda --> OpenAI
    VocabLambda --> ElevenLabs
    VocabLambda --> Pexels
    VocabLambda --> S3Audio
    VocabLambda --> DynamoVocab
    VocabLambda --> WSNotifier

    %% WebSocket Flow
    Users -.-> WSGateway
    WSGateway --> WSHandler
    WSHandler --> DynamoWS
    WSNotifier --> DynamoWS
    WSNotifier --> WSGateway
    WSGateway -.-> Users

    %% Styling
    style Users fill:#232f3e,stroke:#ff9900,stroke-width:2px,color:#ffffff
    style ALB fill:#ff9900,stroke:#232f3e,stroke-width:2px,color:#232f3e
    style Frontend fill:#1e88e5,stroke:#0d47a1,stroke-width:2px,color:#ffffff
    style RestAPI fill:#1e88e5,stroke:#0d47a1,stroke-width:2px,color:#ffffff
    style SQS fill:#9c27b0,stroke:#4a148c,stroke-width:2px,color:#ffffff
    style VocabLambda fill:#e91e63,stroke:#880e4f,stroke-width:2px,color:#ffffff
    style WSGateway fill:#ff9900,stroke:#232f3e,stroke-width:2px,color:#232f3e
    style WSHandler fill:#e91e63,stroke:#880e4f,stroke-width:2px,color:#ffffff
    style WSNotifier fill:#e91e63,stroke:#880e4f,stroke-width:2px,color:#ffffff
    style DynamoUsers fill:#3b48cc,stroke:#232f3e,stroke-width:2px,color:#ffffff
    style DynamoVocab fill:#3b48cc,stroke:#232f3e,stroke-width:2px,color:#ffffff
    style DynamoWS fill:#3b48cc,stroke:#232f3e,stroke-width:2px,color:#ffffff
    style S3Audio fill:#4caf50,stroke:#2e7d32,stroke-width:2px,color:#ffffff
    style OpenAI fill:#607d8b,stroke:#263238,stroke-width:2px,color:#ffffff
    style ElevenLabs fill:#607d8b,stroke:#263238,stroke-width:2px,color:#ffffff
    style Pexels fill:#607d8b,stroke:#263238,stroke-width:2px,color:#ffffff
```

## Architecture Flow

### 1. New Vocabulary Request

- User submits request via Angular frontend → Go REST API → SQS Queue
- **Vocab Lambda** function polls the SQS Queue and runs a LangGraph agent

### 2. Real-time WebSocket Updates

- **WebSocket Handler** manages connections and subscriptions
- **WebSocket Notifier** streams live updates during processing:
  - `processing_started`, `chunk_update`, `processing_completed`, `ddb_hit`, `processing_failed`
- Multiple users can subscribe to the same vocabulary word to get near real time updates of the execution flow

### 3. Data Management

- We use DynamoDB for storing User, Vocabulary and WebSocket connections data
- API calls to OpenAI, Elevenlabs, and Pexels are made to get text, audio and image data respectively
