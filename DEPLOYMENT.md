# TrynDraft Deployment Guide

## Prerequisites

1. **Docker** and **Docker Compose** installed
2. **Git** for version control
3. **Node.js 18+** (for frontend development)
4. **Python 3.12+** (for backend development)

## Quick Start (Development)

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd tryndraft

# Copy environment file
cp .env.example .env

# Edit .env file with your settings
nano .env  # or use any text editor

# Start all services
./deploy.sh  # Linux/Mac
# or
.\deploy.ps1  # Windows PowerShell