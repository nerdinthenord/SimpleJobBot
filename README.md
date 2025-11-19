````markdown
# Simple Job Bot

Simple Job Bot is a small local web app that helps you tailor job applications using a local Ollama model, all running in Docker.

You paste your resume and a job description into a web page and it generates

* A job specific resume  
* A job specific cover letter  
* Three short written answers for common application questions  
* A simple fit score and label  

All output lives in plain text files under a local `job-packages` folder inside this project. Nothing is sent to any external API.

## What this project is and is not

This is not meant to be a perfect example of production grade code.

It is a vibe coded project that exists to show

* A simple split between a web app container and a model container  
* Local LLM usage through Ollama with no cloud calls  
* Guardrails for truthful, non fabricated output  
* Basic architecture, microservice style separation, and security conscious defaults  

If you want to fork it and clean up the code, add tests, or redesign the UI, go ahead. The point is that the moving parts are understandable.

## Behavior and guardrails

The prompts and helpers are written to keep the model under control.

### Resume behavior

The resume generator

* Aims for roughly two pages of text, about nine hundred to eleven hundred words  
* Includes every role from the base resume  
* Compresses older roles into shorter bullets instead of dropping them  
* Uses only facts from your pasted resume and the job description  
* Does not invent employers, job titles, dates, locations, tools, certifications, numbers, or metrics  
* Does not mention AI or tools in the resume  
* Uses a direct, professional tone rather than generic AI style wording  

### Cover letter behavior

The cover letter generator

* Writes a single page letter  
* Uses three to six concise paragraphs  
* References only experience that exists in your resume or is clearly implied by the job description  
* Avoids made up numbers and dramatic claims  
* Keeps the tone grounded and human and avoids obvious AI buzzwords  

### Short answer behavior

The short answer generator

* Produces three short answers for common application questions  
* Grounds all content in your actual experience from the resume  
* Does not fabricate achievements or specific metrics  
* Keeps each answer to three to six sentences  

Across all three generators the instructions say clearly

* Do not lie  
* Do not guess unknown facts  
* Do not mention AI, ChatGPT, language models, or tooling  

## Stack overview

Simple Job Bot runs as two containers using Docker Compose

* `simplejobbot-app`  
  * FastAPI app that serves the web interface on `http://localhost:8000`  
  * Handles the form, file management, and simple diagnostics  
  * Talks to Ollama over HTTP inside the Docker network  

* `simplejobbot-ollama`  
  * Official `ollama/ollama` image  
  * Serves the configured model  
  * Stores model files under the local `./ollama` folder  

Default model

* `llama3.2:3b`  

This model name is controlled by the `JOBBOT_MODEL` environment variable in `compose.yaml`.

## Requirements

You need

* Docker Desktop installed on your machine  
* Docker Compose available through Docker Desktop  
* A machine with at least sixteen gigabytes of memory for a comfortable experience  
* An internet connection the first time the model is downloaded into the Ollama container  

You do not need Ollama installed on the host. The project runs the official `ollama/ollama` container and stores model data in the local `ollama` folder inside this repository.

## System resources

Simple Job Bot uses an LLM through Ollama. Performance and stability depend on

* How much memory Docker is allowed to use  
* How many CPU cores Docker is allowed to use  
* The chosen model size  

The default model is `llama3.2:3b` to balance quality and speed on CPU.

Suggested settings for Docker Desktop

* Memory at least eight gigabytes  
* Four or more virtual CPUs  

If you see errors in the Ollama logs about memory limitations, either lower the model size or increase the Docker memory limit in Docker Desktop settings.

## Quick start

Clone the repository and start the stack

```bash
git clone https://github.com/nerdinthenord/SimpleJobBot.git
cd SimpleJobBot
docker compose up -d
````

Then open this address in your browser

```text
http://localhost:8000
```

To stop the stack later

```bash
docker compose down
```
On first run Docker will start

* The Ollama container, which exposes the Ollama HTTP API inside the Compose network
* The Simple Job Bot container, which exposes the web interface on port 8000

The Ollama container will download the configured model the first time it is requested. The first job can take a bit longer while the model is loaded.

## Start and stop helper scripts

Two helper scripts let you start and stop the stack without remembering Docker commands.

From the `SimpleJobBot` folder, make the scripts executable once

```bash
chmod +x start_simplejobbot.sh stop_simplejobbot.sh
```

To start Simple Job Bot in the background

```bash
./start_simplejobbot.sh
```

This runs `docker compose up -d` and prints a message when the app is ready at `http://localhost:8000`.

To stop Simple Job Bot

```bash
./stop_simplejobbot.sh
```

This runs `docker compose down` and stops both containers.

You can always use the raw Docker commands instead if you prefer.

## Using the web interface

Once the stack is running, open

```text
http://localhost:8000
```

You will see

* A table of previously created job packages
* A form to create a new job package

To generate a package for a new job

1. Paste your resume text into the first large text area
2. Enter the company name, role title, and location
3. Choose a seniority hint if relevant
4. Paste the job description into the second large text area
5. Submit the form

While the model is running the page shows a status message. When it completes you will see

* A fit score and a short label
* A short explanation of the fit
* The full generated resume displayed as plain text
* The folder name on disk where the files were written

Each run creates a new folder under `job-packages` with a timestamped name. Inside that folder you will find

* `resume_full.txt`
* `cover_letter.txt`
* `short_answers.txt`
* `meta.json` with metadata for that run

You can open and edit any of these text files with your preferred editor.

## Data storage and privacy

Two local folders are important

* `job-packages`

  * Stores generated resumes, cover letters, answers, and metadata

* `ollama`

  * Stores downloaded models used by the Ollama container

These folders are listed in `.gitignore` so they are not committed if you use git. That keeps your job data and your local model files out of any remote repository.

## License and open source components

This project uses a custom non commercial license.

Short version

* Free for personal use
* Not allowed for resale or hosted commercial services
* No warranty

See the `LICENSE` file in the repository for the full text and conditions.

This project also makes use of several open source components, including but not limited to

* Python and the standard library
* FastAPI and Starlette
* Uvicorn
* Jinja2
* httpx
* The official `ollama/ollama` container image
* Models served through Ollama such as Meta Llama

Those components remain under their own respective licenses. By using this project you agree to follow the terms of those licenses as well.

## Changelog snapshot

Recent notable changes

* Switched the default model to `llama3.2:3b` to improve performance on CPU
* Split the application into `app` modules for routers, services, and models
* Added stronger guardrails around truthfulness and two page resume length
* Updated prompts to avoid AI flavored wording and to keep all experience while compressing older roles
* Updated the README to reflect the current architecture and behavior

## Summary flow

Typical use looks like this

```bash
git clone https://github.com/nerdinthenord/SimpleJobBot.git
cd SimpleJobBot
docker compose up -d
```

Then visit

```text
http://localhost:8000
```

Paste your resume and the job description, generate a package, and you will get editable text files for resume, cover letter, and short answers for that role, all stored locally under `job-packages`.


