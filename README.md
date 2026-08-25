# Research Agent Assessment
### By Vinayak Mishra


## Demo

### Live Link

https://research-agent-flax.vercel.app/

### Video Demo

## Installation

```bash
git clone https://github.com/Vinayak2005917/Research-Agent
cd Research-Agent
pip install -r requirements.txt
```

## Features

- Multi-file document ingestion
- Semantic retrieval with Qdrant
- Web research
- Interactive human-in-the-loop clarification
- LangGraph-based orchestration
- Evidence-grounded synthesis
- Citation-aware final answers
- Independent answer evaluation
- Real-time research progress


## Tech Stack

- Python
- FastAPI
- javascript
- LangChain
- LangGraph
- Qdrant
- Sentence Transformers
- GPT 5.6 Luna
- Duck Duck Go Search API
- Jira.ai API 

## How It Works

### 1. Document ingestion

Explain:

Files → parsing → chunking → embeddings → Qdrant

### 2. Research

Explain how the research agent decides what to retrieve,
uses the document store/web tools, and collects evidence.

### 3. Human-in-the-loop

Explain that LangGraph interrupts execution when clarification
is required and resumes from the checkpoint after the user responds.

### 4. Synthesis

Explain how research notes are converted into the final cited answer.

### 5. Evaluation

Explain how the evaluator checks factual support and sends
failed answers back for correction.