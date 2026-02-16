"""
Streamlit Voice Agent UI
Talk directly to the AI receptionist through your browser.
"""

import os
import streamlit as st
import streamlit.components.v1 as components
from livekit import api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# LiveKit configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "devkey")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "secret")

# Page config
st.set_page_config(page_title="AI Receptionist", page_icon="🎙️", layout="wide")


# Generate token function
def generate_token(room_name: str, participant_name: str) -> str:
    """Generate a LiveKit access token."""
    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    token.with_identity(participant_name)
    token.with_name(participant_name)
    token.with_grants(
        api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        )
    )
    return token.to_jwt()


# Custom CSS
st.markdown(
    """
<style>
    .main { background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%); }
    .stApp { background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%); }
    h1, h2, h3 { color: #00d4ff !important; }
    .status-box {
        background: rgba(0, 212, 255, 0.1);
        border: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 15px;
        padding: 20px;
        text-align: center;
        margin: 20px 0;
    }
    .agent-avatar {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        background: linear-gradient(135deg, #00d4ff, #0099cc);
        margin: 0 auto 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 50px;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 20px rgba(0, 212, 255, 0.5); }
        50% { box-shadow: 0 0 40px rgba(0, 212, 255, 0.8); }
    }
</style>
""",
    unsafe_allow_html=True,
)

# Title
st.markdown(
    "<h1 style='text-align: center;'>🎙️ AI Receptionist</h1>", unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align: center; color: #888;'>Click Connect and start talking!</p>",
    unsafe_allow_html=True,
)

# Session state
if "room_name" not in st.session_state:
    st.session_state.room_name = "receptionist-room"
if "user_name" not in st.session_state:
    st.session_state.user_name = "visitor"

# Settings in sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    room_name = st.text_input("Room Name", value=st.session_state.room_name)
    user_name = st.text_input("Your Name", value=st.session_state.user_name)
    st.session_state.room_name = room_name
    st.session_state.user_name = user_name

    st.markdown("---")
    st.markdown("### Server Info")
    st.code(f"URL: {LIVEKIT_URL}")

# Main content
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown(
        """
    <div class="status-box">
        <div class="agent-avatar">🤖</div>
        <h3>Office Receptionist</h3>
        <p style="color: #888;">Ready to assist you</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Generate token and create embedded LiveKit component
    try:
        token = generate_token(room_name, user_name)
        ws_url = LIVEKIT_URL

        # Embedded HTML with LiveKit JS SDK
        livekit_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/livekit-client@2/dist/livekit-client.umd.js"></script>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: transparent;
                    color: white;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    padding: 20px;
                }}
                .btn {{
                    padding: 15px 40px;
                    font-size: 18px;
                    border: none;
                    border-radius: 50px;
                    cursor: pointer;
                    margin: 10px;
                    transition: all 0.3s ease;
                    font-weight: bold;
                }}
                .btn-connect {{
                    background: linear-gradient(90deg, #00d4ff, #0099cc);
                    color: white;
                }}
                .btn-connect:hover {{
                    transform: scale(1.05);
                    box-shadow: 0 0 30px rgba(0, 212, 255, 0.6);
                }}
                .btn-disconnect {{
                    background: linear-gradient(90deg, #ff6b6b, #cc0000);
                    color: white;
                }}
                .btn:disabled {{
                    opacity: 0.5;
                    cursor: not-allowed;
                }}
                .status {{
                    padding: 10px 20px;
                    border-radius: 20px;
                    margin: 15px 0;
                    font-weight: bold;
                    font-size: 16px;
                }}
                .status.disconnected {{ background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }}
                .status.connecting {{ background: rgba(255, 193, 7, 0.2); color: #ffc107; }}
                .status.connected {{ background: rgba(0, 255, 136, 0.2); color: #00ff88; }}
                .visualizer {{
                    width: 200px;
                    height: 60px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 4px;
                    margin: 20px 0;
                }}
                .bar {{
                    width: 6px;
                    background: linear-gradient(180deg, #00d4ff, #0099cc);
                    border-radius: 3px;
                    transition: height 0.1s ease;
                }}
                .transcript {{
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 15px;
                    padding: 20px;
                    margin-top: 20px;
                    width: 100%;
                    max-width: 600px;
                    min-height: 250px;
                    max-height: 350px;
                    overflow-y: auto;
                    font-size: 15px;
                }}
                .transcript-title {{
                    color: #00d4ff;
                    font-size: 14px;
                    margin-bottom: 15px;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                .message {{
                    margin: 12px 0;
                    padding: 12px 16px;
                    border-radius: 12px;
                    animation: fadeIn 0.3s ease;
                }}
                @keyframes fadeIn {{
                    from {{ opacity: 0; transform: translateY(10px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}
                .message.user {{ 
                    background: rgba(0, 212, 255, 0.15); 
                    border-left: 3px solid #00d4ff;
                    margin-left: 20px;
                }}
                .message.agent {{ 
                    background: rgba(0, 255, 136, 0.15); 
                    border-left: 3px solid #00ff88;
                    margin-right: 20px;
                }}
                .message-label {{
                    font-size: 11px;
                    opacity: 0.7;
                    margin-bottom: 4px;
                    text-transform: uppercase;
                }}
                .empty-state {{
                    color: #666;
                    text-align: center;
                    padding: 40px;
                    font-style: italic;
                }}
                audio {{ display: none; }}
            </style>
        </head>
        <body>
            <div id="status" class="status disconnected">● Disconnected</div>
            
            <div class="visualizer" id="visualizer">
                <div class="bar" style="height: 20px;"></div>
                <div class="bar" style="height: 30px;"></div>
                <div class="bar" style="height: 25px;"></div>
                <div class="bar" style="height: 40px;"></div>
                <div class="bar" style="height: 35px;"></div>
                <div class="bar" style="height: 45px;"></div>
                <div class="bar" style="height: 30px;"></div>
                <div class="bar" style="height: 25px;"></div>
            </div>
            
            <div>
                <button id="connectBtn" class="btn btn-connect" onclick="connect()">🎤 Connect</button>
                <button id="disconnectBtn" class="btn btn-disconnect" onclick="disconnect()" style="display: none;">🔌 Disconnect</button>
            </div>
            
            <div id="transcript" class="transcript">
                <div class="transcript-title">💬 Conversation</div>
                <div id="messages">
                    <div class="empty-state">Start talking after connecting...</div>
                </div>
            </div>
            
            <audio id="audioElement" autoplay></audio>
            
            <script>
                const wsUrl = "{ws_url}";
                const token = "{token}";
                let room = null;
                let localAudioTrack = null;
                let animationId = null;
                
                const statusEl = document.getElementById('status');
                const connectBtn = document.getElementById('connectBtn');
                const disconnectBtn = document.getElementById('disconnectBtn');
                const messagesEl = document.getElementById('messages');
                const bars = document.querySelectorAll('.bar');
                
                function updateStatus(status, text) {{
                    statusEl.className = 'status ' + status;
                    statusEl.textContent = text;
                }}
                
                function addMessage(text, type) {{
                    // Remove empty state
                    const emptyState = messagesEl.querySelector('.empty-state');
                    if (emptyState) emptyState.remove();
                    
                    const div = document.createElement('div');
                    div.className = 'message ' + type;
                    
                    const label = document.createElement('div');
                    label.className = 'message-label';
                    label.textContent = type === 'user' ? '🗣️ You' : '🤖 Agent';
                    
                    const content = document.createElement('div');
                    content.textContent = text;
                    
                    div.appendChild(label);
                    div.appendChild(content);
                    messagesEl.appendChild(div);
                    
                    // Auto scroll
                    const transcript = document.getElementById('transcript');
                    transcript.scrollTop = transcript.scrollHeight;
                }}
                
                function animateBars(active) {{
                    if (active && !animationId) {{
                        function animate() {{
                            bars.forEach(bar => {{
                                const height = Math.random() * 40 + 10;
                                bar.style.height = height + 'px';
                            }});
                            animationId = requestAnimationFrame(animate);
                        }}
                        animate();
                    }} else if (!active && animationId) {{
                        cancelAnimationFrame(animationId);
                        animationId = null;
                        bars.forEach(bar => bar.style.height = '20px');
                    }}
                }}
                
                async function connect() {{
                    try {{
                        updateStatus('connecting', '● Connecting...');
                        connectBtn.disabled = true;
                        
                        room = new LivekitClient.Room({{
                            adaptiveStream: true,
                            dynacast: true,
                        }});
                        
                        // Handle audio tracks
                        room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {{
                            console.log('Track subscribed:', track.kind, participant.identity);
                            if (track.kind === 'audio') {{
                                const audioElement = document.getElementById('audioElement');
                                track.attach(audioElement);
                                animateBars(true);
                            }}
                        }});
                        
                        room.on(LivekitClient.RoomEvent.TrackUnsubscribed, (track) => {{
                            if (track.kind === 'audio') {{
                                track.detach();
                                animateBars(false);
                            }}
                        }});
                        
                        // Handle data messages (transcriptions)
                        room.on(LivekitClient.RoomEvent.DataReceived, (payload, participant, kind, topic) => {{
                            try {{
                                const data = JSON.parse(new TextDecoder().decode(payload));
                                console.log('Data received:', data);
                                if (data.type === 'transcription' && data.text) {{
                                    addMessage(data.text, data.speaker === 'agent' ? 'agent' : 'user');
                                }}
                            }} catch (e) {{
                                console.error('Error parsing data:', e);
                            }}
                        }});
                        
                        room.on(LivekitClient.RoomEvent.Disconnected, () => {{
                            updateStatus('disconnected', '● Disconnected');
                            connectBtn.style.display = 'inline-block';
                            disconnectBtn.style.display = 'none';
                            connectBtn.disabled = false;
                            animateBars(false);
                        }});
                        
                        room.on(LivekitClient.RoomEvent.ParticipantConnected, (participant) => {{
                            console.log('Participant connected:', participant.identity);
                            if (participant.identity.startsWith('agent')) {{
                                addMessage('Agent has joined the room', 'agent');
                            }}
                        }});
                        
                        await room.connect(wsUrl, token);
                        console.log('Connected to room:', room.name);
                        
                        localAudioTrack = await LivekitClient.createLocalAudioTrack({{
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true,
                        }});
                        
                        await room.localParticipant.publishTrack(localAudioTrack);
                        console.log('Published local audio track');
                        
                        updateStatus('connected', '● Connected - Start talking!');
                        connectBtn.style.display = 'none';
                        disconnectBtn.style.display = 'inline-block';
                        
                    }} catch (error) {{
                        console.error('Connection error:', error);
                        updateStatus('disconnected', '● Error: ' + error.message);
                        connectBtn.disabled = false;
                    }}
                }}
                
                async function disconnect() {{
                    if (room) {{
                        await room.disconnect();
                        room = null;
                    }}
                    if (localAudioTrack) {{
                        localAudioTrack.stop();
                        localAudioTrack = null;
                    }}
                }}
            </script>
        </body>
        </html>
        """

        # Render the embedded component
        components.html(livekit_html, height=650)

    except Exception as e:
        st.error(f"Error: {str(e)}")

# Instructions at bottom
st.markdown("---")
st.markdown(
    """
### 📋 Quick Start
1. Ensure Docker & agent are running
2. Click **Connect** and allow microphone
3. Start talking - see live transcripts!
"""
)