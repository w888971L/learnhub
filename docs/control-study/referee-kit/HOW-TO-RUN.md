# How to Run the Referee Evaluation

## Files to send to each referee

### 1. Codebase files (source of truth)

The referee needs these actual source files to verify plan claims:

```
core/utils/grading.py          — grading engine
core/utils/cache_manager.py    — analytics cache
core/models.py                 — ORM models
core/views_lib/assignments/grade.py    — grading view
core/views_lib/courses/management.py   — course edit view
core/forms.py                  — Django forms
```

### 2. Plans (blinded)

```
referee-kit/plan-a.md
referee-kit/plan-b.md
referee-kit/plan-c.md
```

### 3. Rubric

```
referee-kit/rubric.md
```

### 4. Referee prompt

```
referee-kit/referee-prompt.md
```

## Running with OpenAI Codex CLI

```bash
# Install
npm install -g @openai/codex

# Set API key
export OPENAI_API_KEY=your-key-here

# Run from the learnhub project root
# Codex can read files from the repo directly
codex "$(cat docs/control-study/referee-kit/referee-prompt.md)

Please read these files:
- core/utils/grading.py
- core/utils/cache_manager.py
- core/models.py
- core/views_lib/assignments/grade.py
- core/views_lib/courses/management.py
- core/forms.py
- docs/control-study/referee-kit/rubric.md
- docs/control-study/referee-kit/plan-a.md
- docs/control-study/referee-kit/plan-b.md
- docs/control-study/referee-kit/plan-c.md

Score all three plans against the rubric."
```

## Running with Simon Willison's llm CLI

```bash
# Install
pip install llm
pip install llm-openai  # if needed

# Set API key
llm keys set openai

# Concatenate all files and pipe to the model
cat docs/control-study/referee-kit/referee-prompt.md \
    docs/control-study/referee-kit/rubric.md \
    docs/control-study/referee-kit/plan-a.md \
    docs/control-study/referee-kit/plan-b.md \
    docs/control-study/referee-kit/plan-c.md \
    core/utils/grading.py \
    core/utils/cache_manager.py \
    core/models.py \
    core/views_lib/assignments/grade.py \
    core/views_lib/courses/management.py \
    core/forms.py \
| llm -m gpt-4.1 "Score the three plans per the rubric"
```

## Running with direct OpenAI API

```bash
# For more control, use a Python script
python docs/control-study/referee-kit/run_referee.py
```

(Create `run_referee.py` if you want full control over the API call, temperature=0, etc.)

## Running with Gemini CLI (second referee)

Note: Gemini produced Plan B, so it is NOT a valid referee for this round.
For a second referee, use a model family that produced none of the plans:
- Mistral (via llm-mistral plugin)
- Grok (via xAI API)
- Llama (via llm-ollama plugin for local, or API)

```bash
# Example with Mistral
pip install llm-mistral
llm keys set mistral

cat [same files as above] | llm -m mistral-large "Score the three plans per the rubric"
```

## After running

1. Save each referee's output to `referee-kit/results/`
2. Compare scores across referees
3. Reveal blinding key and add to analysis doc
