#!/bin/sh
cd "$(dirname "$0")" && zip -r ../LeadForge.zip . -x '__pycache__/*' '*.pyc' '*.db'
