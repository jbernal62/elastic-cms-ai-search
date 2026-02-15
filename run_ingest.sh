#!/bin/bash
cd /c/Users/jefer/Documents/cms-ai-search/backend
.venv/Scripts/python.exe -m scripts.ingest_data 2>&1 | tee /c/Users/jefer/Documents/ingest.log
