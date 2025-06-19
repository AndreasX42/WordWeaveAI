# WordWeaveAI: Intelligent Vocabulary Learning with AI Agents

**WordWeaveAI** is an vocabulary learning platform that leverages the power of AI agents to create comprehensive and personalized vocabulary. 
Our agent system automatically generates translations, synonyms, pronunciation guides, usage examples, conjugation tables, 
and multimedia content to accelerate your vocabulary learning.

## 📖 Stack

`Frontend` [Angular 20](https://angular.dev/) \
`Backend` [Go 1.24](https://golang.org/) [Python 3.12+](https://www.python.org/) [AWS Lambda](https://aws.amazon.com/lambda/) \
`LLM Frameworks` [LangChain](https://www.langchain.com/) [LangGraph](https://python.langchain.com/docs/langgraph/) [OpenAI](https://www.openai.com/) \
`API Frameworks` [Gin Web Framework](https://gin-gonic.com/) \
`DBs` [Amazon DynamoDB](https://aws.amazon.com/dynamodb/) \
`CI/CD` [AWS CodePipeline](https://aws.amazon.com/codepipeline/) [AWS CodeBuild](https://aws.amazon.com/codebuild/) [AWS CDK](https://aws.amazon.com/cdk/)


## 📊 Agent Workflow

The LangGraph agent processes vocabulary through an optimized workflow:

1. **Validation** → Ensures word is valid and processable
2. **Classification** → Determines part of speech and linguistic category
3. **Translation** → Generates accurate translations
4. **Parallel Processing** → Simultaneously handles:
   - Syllable breakdown
   - Synonym generation
   - Pronunciation guides
   - Usage examples
   - Conjugation patterns
   - Media/audio generation
  
<img width="723" alt="image" src="https://github.com/user-attachments/assets/e2e5cfb1-0f46-4eed-b9cf-c0b5a979ff96" />


## 🗺️ Architecture

<img width="914" alt="image" src="https://github.com/user-attachments/assets/ec4b3a76-7c36-4724-a31a-528b599152e6" />

### 🔄 Flow Overview

1. **New vocabulary request**
- User submits request via Angular frontend → Go REST API → SQS Queue
- **Vocab Lambda** function polls the SQS Queue and runs a LangGraph agent

2. **Real-time updates** 
- **WebSocket Handler** manages connections and subscriptions
- **WebSocket Notifier** streams live updates during processing:
  - `processing_started`, `chunk_update`, `processing_completed`, `ddb_hit`, `processing_failed`
- Multiple users can subscribe to the same vocabulary word to get near real time updates of the execution flow

3. **Data management** 
- We use DynamoDB for storing User, Vocabulary and WebSocket connections data
- API calls to OpenAI, Elevenlabs, and Pexels are made to get text, audio and image data respectively


## 🛠️ Development

### 📁 Directory Structure

```
/
├── agent/                 # LangGraph AI Agent
├── restapi/               # Go REST API
├── frontend/              # Angular Frontend
├── aws-infra/             # AWS CDK Infrastructure
└── README.md
```




