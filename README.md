# Simple Job Bot

## About this project

This is not a showcase of perfect programming or advanced engineering.

Simple Job Bot was vibe coded as a personal project to explore

* basic architecture and splitting things into small services
* running everything locally in Docker
* keeping data on your own machine and thinking about security first
* using a local AI model with simple guard rails and clear prompts

The goal is to keep it small, local, and easy to understand.
It is an example of how to wire tools together, not a polished product or a production grade template.

##What it does
Simple Job Bot is a local job application helper that runs fully inside Docker and uses an Ollama model to write job specific material for you.

It generates

* A job specific resume
* A job specific cover letter
* A short fit explanation and score
* Three short written answers for typical application questions

All output files are stored locally inside this project so you keep full control of your data.

---

## What you need

You must have

* Docker Desktop installed
* Docker Compose available through Docker Desktop
* An internet connection the first time the model downloads inside the Ollama container

You do not need Ollama installed on your host.
This project runs the official `ollama/ollama` container and stores all models inside the local `ollama` folder.

---

## Quick start

To clone and start Simple Job Bot

```
git clone https://github.com/nerdinthenord/SimpleJobBot.git
cd SimpleJobBot
docker compose up -d
```

Then open this address in your browser

```
http://localhost:8000
```

To stop it later

```
docker compose down
```

On first run Docker will start

* The Ollama container, which exposes the Ollama API inside the Docker network
* The Simple Job Bot container, which exposes a web interface on port 8000

The Ollama container will download the configured model the first time it is used. This may take some time on the very first job you run.

The default model used by this project is

```
llama3.2:3b
```

This is configured in `compose.yaml` and gives a good balance of quality and performance for resume and cover letter writing.

---

## Start and stop helper scripts

This repository includes two helper scripts so you do not have to remember Docker commands

* `start_simplejobbot.sh` to start the stack in the background
* `stop_simplejobbot.sh` to stop and clean up

From the `SimpleJobBot` folder make the scripts executable once

```
chmod +x start_simplejobbot.sh stop_simplejobbot.sh
```

To start Simple Job Bot

```
./start_simplejobbot.sh
```

This runs `docker compose up -d` behind the scenes and brings up the app at `http://localhost:8000`.

To stop Simple Job Bot

```
./stop_simplejobbot.sh
```

This runs `docker compose down` and stops both the application container and the Ollama container.

You can always use the raw Docker commands instead if you prefer

```
docker compose up -d
docker compose down
```

---

## Using the web interface

Once the stack is running, open

```
http://localhost:8000
```

You will see

* A table of previously created job packages
* A form to create a new job package

To generate a package for a new job

1. Paste your resume text into the first large text area
2. Fill in the company name, role title, and any other fields shown
3. Paste the job description into the second large text area
4. Select the seniority hint if the form offers it
5. Click the button to generate the package

While the model is running the page will show a status message. When the process completes you will see

* A fit score and a simple label that describes the fit
* A short explanation of why the job is a fit
* The full generated resume as plain text on the page
* A note showing which folder on disk contains the files for this job

Each run creates a new folder under `job-packages` with a timestamped name. Inside that folder you will find

* `resume_full.txt`
* `cover_letter.txt`
* `short_answers.txt`
* `meta.json` with metadata for that run

You can open and edit any of these text files with your preferred editor.

---

## System resources and models

Simple Job Bot uses an Ollama model inside Docker. The experience depends on

* Docker memory limit
* Number of CPU cores given to Docker
* The model you choose in `JOBBOT_MODEL`

A practical baseline

* Host machine with at least sixteen gigabytes of memory
* Docker Desktop memory set to at least eight gigabytes
* Four or more virtual CPUs allocated to Docker
* Model `llama3.2:3b` for a good balance of quality and speed

Larger models such as `llama3` with eight billion parameters require more memory inside the container. If Docker has too little memory you may see errors from Ollama that say the model requires more memory than is available. In that case either

* increase the Docker memory limit in Docker Desktop settings, or
* switch to a smaller model such as `llama3.2:3b` or `llama3.2:1b`

To change the model that Simple Job Bot requests, edit `compose.yaml` and update the environment section for the application service

```
environment:
  - OLLAMA_HOST=http://ollama:11434
  - JOBBOT_MODEL=llama3.2:3b
  - HOST_OUTPUT_ROOT=./job-packages
```

After editing `compose.yaml` restart the stack

```
docker compose down
docker compose up -d
```

---

## Data storage and privacy

Two folders in this project are intended to remain local on your machine

* `job-packages`
  Stores generated resumes, cover letters, short answers, and metadata

* `ollama`
  Stores the downloaded model files used by the Ollama container

These folders are listed in `.gitignore` so they are not committed if you use git. This keeps your job data and your local models out of your remote repository.

A minimal `.gitignore` looks like

```
__pycache__/
*.pyc

job-packages/
ollama/
```

---

## Summary

Typical usage

```
git clone https://github.com/nerdinthenord/SimpleJobBot.git
cd SimpleJobBot
docker compose up -d
```

Then visit

```
http://localhost:8000
```

Paste your resume and the job description, generate a package, and your editable text files for resume, cover letter, and short answers will be stored under `job-packages`.
