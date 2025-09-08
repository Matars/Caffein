# 4DT911-ProjectVis

A full-stack web application built with Vue.js (TypeScript), Flask (Python), and MongoDB.

## Project Structure

```
4dt911-projectvis/
├── frontend/          # Vue.js + TypeScript frontend
├── backend/           # Flask + Python backend
├── docker-compose.yml # Docker configuration
├── pnpm-workspace.yaml # PNPM workspace configuration
└── README.md
```

## Tech Stack

- **Frontend**: Vue.js 3 + TypeScript + Vite + Pinia + Vue Router
- **Backend**: Flask + Python 3.11 + PyMongo
- **Database**: MongoDB
- **Package Manager**: PNPM
- **Containerization**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- PNPM
- Docker and Docker Compose

### Development Setup

1. **Clone and setup:**

   ```bash
   git clone <repository-url>
   cd 4dt911-projectvis
   pnpm run setup  # Sets up Python venv and installs all dependencies
   ```

2. **Start with Docker (Recommended):**

   ```bash
   pnpm run docker:up
   ```

   This will start:
   - Frontend: http://localhost:3000
   - Backend: http://localhost:5001
   - MongoDB: localhost:27017

3. **Or start manually:**

   ```bash
   # Activate Python virtual environment
   source .venv/bin/activate

   # Terminal 1: Start MongoDB (if not using Docker)
   mongod

   # Terminal 2: Start both frontend and backend
   pnpm dev

   # Or start individually:
   # pnpm frontend:dev
   # pnpm backend:dev
   ```

   cd frontend
   pnpm install
   pnpm dev

   ```

   ```

### Available Scripts

- `pnpm setup` - Set up Python virtual environment and install all dependencies
- `pnpm dev` - Start both frontend and backend in development mode
- `pnpm frontend:dev` - Start only frontend
- `pnpm backend:dev` - Start only backend
- `pnpm backend:install` - Install Python dependencies in virtual environment
- `pnpm docker:up` - Start all services with Docker Compose
- `pnpm docker:down` - Stop all Docker services
- `pnpm build` - Build frontend for production

## Features

- ✅ Vue.js 3 with TypeScript and Composition API
- ✅ Flask REST API with CORS support
- ✅ MongoDB integration with PyMongo
- ✅ Docker containerization
- ✅ PNPM workspace for monorepo management
- ✅ Environment-based configuration
- ✅ Health check endpoints
- ✅ Error handling and loading states

## API Endpoints

- `GET /api/hello` - Returns hello message from database
- `GET /api/health` - Returns system health status

## Environment Variables

### Frontend (.env)

```
VITE_API_URL=http://localhost:5001/api
```

### Backend (.env)

```
FLASK_APP=app.py
FLASK_ENV=development
MONGO_URI=mongodb://mongodb:27017/
DATABASE_NAME=projectvis_db
```

## Docker Configuration

The project includes a complete Docker setup with:

- MongoDB with initialization script
- Flask backend with hot reload
- Vue.js frontend with development server
- Shared network for service communication

## Development Notes

- Frontend runs on port 3000
- Backend runs on port 5000
- MongoDB runs on port 27017
- All services are configured for hot reload during development

## Suggestions for a good README

Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name

Choose a self-explaining name for your project.

## Description

Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges

On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals

Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation

Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage

Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support

Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap

If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing

State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment

Show your appreciation to those who have contributed to the project.

## License

For open source projects, say how it is licensed.

## Project status

If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
