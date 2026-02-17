# Frontend Setup Guide - LiveKit Agent React UI

## Problem: "Agent didn't join the room"

This error occurs when the frontend connects to LiveKit but the Python agent backend isn't running or isn't configured to join rooms automatically.

## Solution: Run Both Backend and Frontend

### Step 1: Start the Python Agent Backend (REQUIRED)

The Python agent must be running BEFORE you connect from the frontend. Open a terminal and run:

```powershell
# Make sure you're in the project root directory
cd D:\New-AI-receptionist\AI-Receptionist

# Activate virtual environment (if using one)
.\venv\Scripts\Activate.ps1

# Start the agent in development mode
python main.py dev
```

You should see output like:
```
INFO - Prewarming: Loading Silero VAD model...
INFO - Prewarming complete. Available agents: ['hospital', 'medical', 'clinic', 'default']
INFO - Worker started
```

**Keep this terminal running!** The agent needs to be active to join rooms.

### Step 2: Start the Frontend

In a NEW terminal window:

```powershell
# Navigate to the frontend directory
cd D:\New-AI-receptionist\AI-Receptionist\frontend\agent-starter-react

# Install dependencies (first time only)
npm install

# Start the development server
npm run dev
```

The frontend will start at http://localhost:3000

### Step 3: Test the Connection

1. Open http://localhost:3000 in your browser
2. Click "Start call" button
3. Allow microphone access when prompted
4. The agent should join within 2-3 seconds
5. You should see "Agent is listening, ask it a question"
6. Start speaking!

## Configuration Details

### Frontend (.env.local)
```env
LIVEKIT_API_KEY=APIUqVpoHBZMFhq
LIVEKIT_API_SECRET=AuVbF4xiQf1hyHI7eexx9NMeyhfkejsKtoTtwrOgxv1P
LIVEKIT_URL=wss://testin-9uuc19ri.livekit.cloud
AGENT_NAME=hospital
```

### Backend (.env)
```env
LIVEKIT_URL=wss://testin-9uuc19ri.livekit.cloud
LIVEKIT_API_KEY=APIUqVpoHBZMFhq
LIVEKIT_API_SECRET=AuVbF4xiQf1hyHI7eexx9NMeyhfkejsKtoTtwrOgxv1P
AGENT_TYPE=hospital
```

## How Agent Dispatch Works

1. **Frontend creates a room**: When you click "Start call", the frontend creates a new LiveKit room with a random name like `voice_assistant_room_1234`

2. **Frontend requests agent**: The room configuration includes `agentName: "hospital"` which tells LiveKit to dispatch a hospital agent

3. **Backend agent joins**: Your running Python agent (main.py) listens for new rooms and automatically joins when one is created

4. **Connection established**: Once the agent joins, the voice conversation begins

## Troubleshooting

### "Agent didn't join the room"
- **Cause**: Python agent backend is not running
- **Fix**: Make sure `python main.py dev` is running in a separate terminal

### "Connection failed"
- **Cause**: Wrong LiveKit credentials or URL
- **Fix**: Verify credentials match in both `.env` and `frontend/agent-starter-react/.env.local`

### "Microphone not working"
- **Cause**: Browser permissions
- **Fix**: Check browser settings and allow microphone access for localhost

### Agent joins but doesn't respond
- **Cause**: Missing API keys (OpenAI, Deepgram, Cartesia)
- **Fix**: Check your root `.env` file has all required API keys

### Database errors
- **Cause**: PostgreSQL connection issues
- **Fix**: Verify `DATABASE_URL` in `.env` is correct and database is accessible

## Quick Test Commands

Test if agent can connect to LiveKit:
```powershell
python main.py dev
```

Test if frontend can build:
```powershell
cd frontend/agent-starter-react
npm run build
```

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Browser UI    │ ◄─────► │  LiveKit Cloud   │ ◄─────► │  Python Agent   │
│  (React/Next)   │  WebRTC │  (Voice Server)  │  WebRTC │   (main.py)     │
└─────────────────┘         └──────────────────┘         └─────────────────┘
        │                                                          │
        │                                                          │
        └──────────────────────────────────────────────────────────┘
                    Both connect to same LiveKit room
```

## Development Workflow

1. Start backend: `python main.py dev` (Terminal 1)
2. Start frontend: `npm run dev` (Terminal 2)
3. Open browser: http://localhost:3000
4. Make changes to code
5. Backend: Restart `python main.py dev`
6. Frontend: Auto-reloads (hot reload enabled)

## Production Deployment

For production, you'll need to:
1. Deploy the Python agent to a server (Docker recommended)
2. Build and deploy the Next.js frontend
3. Use production LiveKit credentials
4. Set up proper domain and SSL certificates

See `DEPLOYMENT.md` for detailed production setup instructions.
