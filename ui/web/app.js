// app.js

const chatHistory = document.getElementById('chatHistory');
const chatForm = document.getElementById('chatForm');
const queryInput = document.getElementById('queryInput');
const sendBtn = document.getElementById('sendBtn');
const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const uploadStatus = document.getElementById('uploadStatus');
const uploadSuccess = document.getElementById('uploadSuccess');

// API Base URL (Assuming frontend is served from the same host)
const API_URL = window.location.origin;
let currentSessionId = null;

// --- Chat Session Logic ---
const chatList = document.getElementById('chatList');
const newChatBtn = document.getElementById('newChatBtn');

async function createNewChat() {
    try {
        const res = await fetch(`${API_URL}/chat/session`, { method: 'POST' });
        if (res.ok) {
            const data = await res.json();
            currentSessionId = data.session_id;
            localStorage.setItem('lastSessionId', currentSessionId);
            chatHistory.innerHTML = `
                <div class="message ai-message">
                    <div class="avatar">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2c-.11.66.45 1.5 1.09 1.48.97-.04 1.76.71 1.9 1.67.06.45.6.85 1.04.85 1.05.02 1.83 1.05 1.5 2.05-.13.41.05 1.01.44 1.25.87.52.87 2 .02 2.53-.4.24-.6 1-.45 1.42.34.98-.44 2.01-1.48 2.05-.44 0-1 .4-1.05.85-.14.96-.92 1.71-1.9 1.67-.64-.02-1.2.82-1.1 1.48a2 2 0 0 1-2 2 2 2 0 0 1-2-2c.11-.66-.45-1.5-1.09-1.48-.97.04-1.76-.71-1.9-1.67-.06-.45-.6-.85-1.04-.85-1.05-.02-1.83-1.05-1.5-2.05.13-.41-.05-1.01-.44-1.25-.87-.52-.87-2-.02-2.53.4-.24.6-1 .45-1.42-.34-.98.44-2.01 1.48-2.05.44 0 1-.4 1.05-.85.14-.96.92-1.71 1.9-1.67.64.02 1.2-.82 1.1-1.48a2 2 0 0 1 2-2z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                    </div>
                    <div class="content">
                        Hello! I am your private RAG assistant. Upload some documents on the left, and then ask me any questions about them.
                    </div>
                </div>
            `;
            fetchChats();
        }
    } catch (e) {
        console.error("Failed to create chat", e);
    }
}

async function fetchChats() {
    try {
        const res = await fetch(`${API_URL}/chat/sessions`);
        if (res.ok) {
            const data = await res.json();
            if (data.sessions.length === 0) {
                chatList.innerHTML = `<div style="text-align: center; color: var(--text-muted); font-size: 12px; margin-top: 10px;">No previous chats.</div>`;
            } else {
                chatList.innerHTML = data.sessions.map(s => `
                    <div class="chat-item ${s.session_id === currentSessionId ? 'active' : ''}" onclick="loadChat('${s.session_id}')" title="${s.title}" style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">💬 ${s.title}</span>
                        <button onclick="deleteChat(event, '${s.session_id}')" title="Delete Chat" style="background: none; border: none; cursor: pointer; opacity: 0.6; padding: 0 5px;">🗑️</button>
                    </div>
                `).join('');
            }
            return data.sessions;
        }
    } catch (e) {
        console.error("Failed to fetch chats", e);
    }
    return [];
}

async function loadChat(sessionId) {
    try {
        const res = await fetch(`${API_URL}/chat/session/${sessionId}`);
        if (res.ok) {
            const data = await res.json();
            currentSessionId = data.session_id;
            localStorage.setItem('lastSessionId', currentSessionId);
            
            chatHistory.innerHTML = `
                <div class="message ai-message">
                    <div class="avatar">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2c-.11.66.45 1.5 1.09 1.48.97-.04 1.76.71 1.9 1.67.06.45.6.85 1.04.85 1.05.02 1.83 1.05 1.5 2.05-.13.41.05 1.01.44 1.25.87.52.87 2 .02 2.53-.4.24-.6 1-.45 1.42.34.98-.44 2.01-1.48 2.05-.44 0-1 .4-1.05.85-.14.96-.92 1.71-1.9 1.67-.64-.02-1.2.82-1.1 1.48a2 2 0 0 1-2 2 2 2 0 0 1-2-2c.11-.66-.45-1.5-1.09-1.48-.97.04-1.76-.71-1.9-1.67-.06-.45-.6-.85-1.04-.85-1.05-.02-1.83-1.05-1.5-2.05.13-.41-.05-1.01-.44-1.25-.87-.52-.87-2-.02-2.53.4-.24.6-1 .45-1.42-.34-.98.44-2.01 1.48-2.05.44 0 1-.4 1.05-.85.14-.96.92-1.71 1.9-1.67.64.02 1.2-.82 1.1-1.48a2 2 0 0 1 2-2z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                    </div>
                    <div class="content">
                        Chat restored. Let's continue!
                    </div>
                </div>
            `;
            
            for (const turn of data.history) {
                addUserMessage(turn.user_query);
                
                const div = document.createElement('div');
                div.className = 'message ai-message';
                
                let sourcesHtml = '';
                if (turn.sources && turn.sources.length > 0) {
                    const uniqueSources = [];
                    const seen = new Set();
                    for (const s of turn.sources) {
                        const key = s.page_number ? `${s.file_name}#page=${s.page_number}` : s.file_name;
                        if (!seen.has(key)) {
                            seen.add(key);
                            uniqueSources.push(s);
                        }
                    }
                    sourcesHtml = `<div class="sources" style="display: flex; margin-top: 12px; gap: 8px; flex-wrap: wrap;">${uniqueSources.map(s => {
                        const href = s.page_number ? `${API_URL}/files/${encodeURIComponent(s.file_name)}#page=${s.page_number}` : `${API_URL}/files/${encodeURIComponent(s.file_name)}`;
                        const label = s.page_number ? `📄 ${s.file_name} (Pg. ${s.page_number})` : `📄 ${s.file_name}`;
                        const safeName = s.file_name.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                        const safeUrl = href.replace(/'/g, "\\'");
                        return `<button type="button" class="source-badge" onclick="openPdfViewer('${safeUrl}', '${safeName}')">${label}</button>`;
                    }).join('')}</div>`;
                }
                
                div.innerHTML = `
                    <div class="avatar">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2c-.11.66.45 1.5 1.09 1.48.97-.04 1.76.71 1.9 1.67.06.45.6.85 1.04.85 1.05.02 1.83 1.05 1.5 2.05-.13.41.05 1.01.44 1.25.87.52.87 2 .02 2.53-.4.24-.6 1-.45 1.42.34.98-.44 2.01-1.48 2.05-.44 0-1 .4-1.05.85-.14.96-.92 1.71-1.9 1.67-.64-.02-1.2.82-1.1 1.48a2 2 0 0 1-2 2 2 2 0 0 1-2-2c.11-.66-.45-1.5-1.09-1.48-.97.04-1.76-.71-1.9-1.67-.06-.45-.6-.85-1.04-.85-1.05-.02-1.83-1.05-1.5-2.05.13-.41-.05-1.01-.44-1.25-.87-.52-.87-2-.02-2.53.4-.24.6-1 .45-1.42-.34-.98.44-2.01 1.48-2.05.44 0 1-.4 1.05-.85.14-.96.92-1.71 1.9-1.67.64.02 1.2-.82 1.1-1.48a2 2 0 0 1 2-2z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                    </div>
                    <div class="content">
                        <div class="final-answer">${marked.parse(turn.ai_answer)}</div>
                        ${sourcesHtml}
                    </div>
                `;
                chatHistory.appendChild(div);
            }
            chatHistory.scrollTop = chatHistory.scrollHeight;
            fetchChats();
        }
    } catch (e) {
        console.error("Failed to load chat", e);
    }
}

async function deleteChat(event, sessionId) {
    event.stopPropagation(); // Prevent loading the chat when deleting
    if (!confirm('Are you sure you want to delete this chat session?')) {
        return;
    }
    
    try {
        const res = await fetch(`${API_URL}/chat/session/${sessionId}`, { method: 'DELETE' });
        if (res.ok) {
            if (sessionId === currentSessionId) {
                // If we deleted the current active chat, start a new one
                createNewChat();
            } else {
                fetchChats();
            }
        } else {
            alert("Failed to delete chat.");
        }
    } catch (e) {
        console.error("Delete chat failed", e);
    }
}

newChatBtn.addEventListener('click', createNewChat);

async function initChat() {
    const sessions = await fetchChats();
    if (sessions && sessions.length > 0) {
        let sessionToLoad = sessions[0].session_id;
        const savedSession = localStorage.getItem('lastSessionId');
        // If we have a saved session and it exists in our list, use it
        if (savedSession && sessions.find(s => s.session_id === savedSession)) {
            sessionToLoad = savedSession;
        }
        await loadChat(sessionToLoad);
    } else {
        createNewChat();
    }
}

// Initialize on page load
initChat();

// --- File Fetching Logic ---
const fileList = document.getElementById('fileList');

async function fetchFiles() {
    try {
        const res = await fetch(`${API_URL}/files`);
        if (res.ok) {
            const data = await res.json();
            
            if (data.files.length === 0 && (!data.folders || data.folders.length === 0)) {
                fileList.innerHTML = `<div style="text-align: center; color: var(--text-muted); font-size: 12px; margin-top: 10px;">No files or folders yet.</div>`;
                window.availableFiles = [];
            } else {
                // Group files by category
                const grouped = {};
                if (data.folders) {
                    data.folders.forEach(folder => {
                        grouped[folder] = [];
                    });
                }
                grouped["Uncategorized"] = grouped["Uncategorized"] || [];
                
                data.files.forEach(f => {
                    const cat = f.category || "Uncategorized";
                    if (!grouped[cat]) grouped[cat] = [];
                    grouped[cat].push(f);
                });

                let html = "";
                const categories = Object.keys(grouped).sort((a,b) => a === "Uncategorized" ? 1 : b === "Uncategorized" ? -1 : a.localeCompare(b));
                
                for (const cat of categories) {
                    const files = grouped[cat];
                    // Don't show Uncategorized if it's empty
                    if (cat === "Uncategorized" && files.length === 0) continue;
                    
                    const isExpanded = window.expandedFolders && window.expandedFolders.has(cat);
                    const icon = isExpanded ? '▼' : '▶';
                    
                    html += `<div class="category-header drop-target" style="cursor: pointer; display: flex; align-items: center; justify-content: space-between;" data-folder="${cat}" onclick="toggleFolder('${cat}')" ondragover="handleDragOver(event)" ondragleave="handleDragLeave(event)" ondrop="handleDropFolder(event, '${cat}')">
                                <span>📂 ${cat}</span>
                                <span style="font-size: 10px; opacity: 0.7;">${icon}</span>
                             </div>`;
                             
                    if (isExpanded) {
                        html += `<div class="folder-content">`;
                        html += files.map(f => `
                            <div class="file-item" draggable="true" ondragstart="handleDragStart(event, '${f.name}')">
                                <div class="file-icon">📄</div>
                                <div class="file-details">
                                    <span class="file-name" title="${f.name}">${f.name}</span>
                                    <span class="file-size">${f.size}</span>
                                </div>
                                <button class="delete-file-btn" onclick="deleteFile('${f.name}')" title="Delete file" style="background: none; border: none; cursor: pointer; opacity: 0.6; transition: opacity 0.2s;">🗑️</button>
                            </div>
                        `).join('');
                        html += `</div>`;
                    }
                }
                
                fileList.innerHTML = html;
                window.availableFiles = data.files.map(f => f.name);
            }
        }
    } catch (e) {
        console.error("Failed to fetch files", e);
    }
}

// Fetch initially on page load
fetchFiles();

async function deleteFile(filename) {
    if (!confirm(`Are you sure you want to delete ${filename}? This will remove it from the knowledge base.`)) {
        return;
    }
    
    try {
        const res = await fetch(`${API_URL}/files/${filename}`, { method: 'DELETE' });
        if (res.ok) {
            fetchFiles(); // Refresh the list
        } else {
            alert(`Failed to delete ${filename}`);
        }
    } catch (e) {
        console.error("Delete failed", e);
    }
}

// --- File Upload Logic ---
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        handleUpload(e.dataTransfer.files[0], dropZone.dataset.folder);
    }
});

// --- Folder & Drag Drop Logic ---
const newFolderBtn = document.getElementById('newFolderBtn');
if (newFolderBtn) {
    newFolderBtn.addEventListener('click', async () => {
        const folderName = prompt("Enter a name for the new folder:");
        if (folderName && folderName.trim()) {
            try {
                const res = await fetch(`${API_URL}/folders`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: folderName.trim() })
                });
                if (res.ok) {
                    const data = await res.json();
                    window.expandedFolders.add(data.folder);
                    fetchFiles();
                } else {
                    alert("Failed to create folder.");
                }
            } catch (e) {
                console.error("Error creating folder", e);
            }
        }
    });
}
window.expandedFolders = new Set();
window.toggleFolder = (cat) => {
    if (window.expandedFolders.has(cat)) {
        window.expandedFolders.delete(cat);
    } else {
        window.expandedFolders.add(cat);
    }
    fetchFiles();
};

window.handleDragStart = (e, filename) => {
    e.dataTransfer.setData('text/plain', filename);
    e.dataTransfer.effectAllowed = 'move';
};

window.handleDragOver = (e) => {
    e.preventDefault(); 
    e.dataTransfer.dropEffect = 'move';
    e.currentTarget.classList.add('dragover');
};

window.handleDragLeave = (e) => {
    e.currentTarget.classList.remove('dragover');
};

window.handleDropFolder = async (e, targetFolder) => {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');
    
    const filename = e.dataTransfer.getData('text/plain');
    if (filename) {
        try {
            const res = await fetch(`${API_URL}/files/move`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename, target_folder: targetFolder })
            });
            if (res.ok) {
                fetchFiles();
            } else {
                const data = await res.json();
                alert(`Move failed: ${data.detail}`);
            }
        } catch (err) {
            console.error("Failed to move file", err);
        }
    } else if (e.dataTransfer.files.length) {
        handleUpload(e.dataTransfer.files[0], targetFolder);
    }
};



fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleUpload(e.target.files[0]);
    }
});

let ingestionPollingInterval = null;

function checkIngestionStatus() {
    if (ingestionPollingInterval) return; // Already polling
    
    ingestionPollingInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API_URL}/ingest/status`);
            if (res.ok) {
                const data = await res.json();
                if (data.is_ingesting) {
                    if (data.progress) {
                        uploadStatus.innerText = data.progress;
                    } else {
                        uploadStatus.innerText = "Processing document in the background...";
                    }
                    uploadStatus.classList.remove('hidden');
                    uploadSuccess.classList.add('hidden');
                } else {
                    // Ingestion is done!
                    clearInterval(ingestionPollingInterval);
                    ingestionPollingInterval = null;
                    
                    // Only show success message if we were previously showing the processing indicator
                    if (!uploadStatus.classList.contains('hidden')) {
                        uploadStatus.classList.add('hidden');
                        uploadSuccess.innerText = "The document is successfully ingested. You can search now.";
                        uploadSuccess.classList.remove('hidden');
                        setTimeout(() => {
                            uploadSuccess.classList.add('hidden');
                            uploadSuccess.innerText = "Upload successful"; // Reset
                            uploadStatus.innerText = "Uploading...";
                        }, 5000);
                        
                        fetchFiles();
                    }
                }
            }
        } catch (e) {
            console.error("Failed to check ingestion status", e);
        }
    }, 2000); // Poll every 2 seconds
}

// Start polling on page load in case a file is already being processed
checkIngestionStatus();

async function handleUpload(file, folder = null) {
    const formData = new FormData();
    formData.append('file', file);
    
    let targetFolder = folder;
    if (!targetFolder && dropZone.dataset.folder && dropZone.dataset.folder !== 'Uncategorized') {
        targetFolder = dropZone.dataset.folder;
    }
    
    if (targetFolder && targetFolder !== 'Uncategorized') {
        formData.append('category', targetFolder);
    }

    uploadStatus.innerText = "Uploading...";
    uploadStatus.classList.remove('hidden');
    uploadSuccess.classList.add('hidden');

    try {
        const res = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        if (res.ok) {
            // Start polling to wait for chunking to finish
            checkIngestionStatus();
        } else {
            alert("Upload failed.");
            uploadStatus.classList.add('hidden');
        }
    } catch (err) {
        console.error(err);
        uploadStatus.classList.add('hidden');
    }
}

// --- Chat Logic ---

function addUserMessage(text) {
    const div = document.createElement('div');
    div.className = 'message user-message';
    div.innerHTML = `
        <div class="avatar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
        </div>
        <div class="content">${text}</div>
    `;
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function createAiMessage() {
    const div = document.createElement('div');
    div.className = 'message ai-message';
    
    // Setup the structure with a Thought Process block and a Final Answer block
    div.innerHTML = `
        <div class="avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2c-.11.66.45 1.5 1.09 1.48.97-.04 1.76.71 1.9 1.67.06.45.6.85 1.04.85 1.05.02 1.83 1.05 1.5 2.05-.13.41.05 1.01.44 1.25.87.52.87 2 .02 2.53-.4.24-.6 1-.45 1.42.34.98-.44 2.01-1.48 2.05-.44 0-1 .4-1.05.85-.14.96-.92 1.71-1.9 1.67-.64-.02-1.2.82-1.1 1.48a2 2 0 0 1-2 2 2 2 0 0 1-2-2c.11-.66-.45-1.5-1.09-1.48-.97.04-1.76-.71-1.9-1.67-.06-.45-.6-.85-1.04-.85-1.05-.02-1.83-1.05-1.5-2.05.13-.41-.05-1.01-.44-1.25-.87-.52-.87-2-.02-2.53.4-.24.6-1 .45-1.42-.34-.98.44-2.01 1.48-2.05.44 0 1-.4 1.05-.85.14-.96.92-1.71 1.9-1.67.64.02 1.2-.82 1.1-1.48a2 2 0 0 1 2-2z"></path><circle cx="12" cy="12" r="3"></circle></svg>
        </div>
        <div class="content">
            <div class="thought-process">
                <div class="thought-header">
                    <div class="typing-indicator" style="width: 24px;">
                        <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
                    </div>
                    <span>AI is thinking...</span>
                </div>
                <div class="thought-steps" style="display: flex;"></div>
            </div>
            <div class="final-answer" style="display: none;"></div>
            <div class="sources" style="display: none;"></div>
        </div>
    `;
    
    chatHistory.appendChild(div);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    return {
        container: div,
        steps: div.querySelector('.thought-steps'),
        answer: div.querySelector('.final-answer'),
        sources: div.querySelector('.sources'),
        headerText: div.querySelector('.thought-header span'),
        spinner: div.querySelector('.typing-indicator')
    };
}

function addThoughtStep(ui, message) {
    // Dim previous steps
    const prevSteps = ui.steps.querySelectorAll('.step-dot.active');
    prevSteps.forEach(dot => dot.classList.remove('active'));

    const stepDiv = document.createElement('div');
    stepDiv.className = 'thought-step';
    stepDiv.innerHTML = `
        <div class="step-dot active"></div>
        <span>${message}</span>
    `;
    ui.steps.appendChild(stepDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

async function streamAnswer(query, fileNameFilter = null) {
    const ui = createAiMessage();
    sendBtn.disabled = true;
    queryInput.disabled = true;

    try {
        const payload = { query: query, session_id: currentSessionId };
        if (fileNameFilter) payload.file_name_filter = fileNameFilter;
        
        const response = await fetch(`${API_URL}/query_stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error("API Error");

        // We use the Streams API to read Server-Sent Events (SSE) or chunked responses
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            
            // The python backend yields chunks separated by newlines
            const parts = buffer.split('\n');
            buffer = parts.pop(); // Keep the last incomplete part in the buffer
            
            for (const part of parts) {
                if (part.trim() === '') continue;
                
                try {
                    const data = JSON.parse(part);
                    
                    if (data.step === 'done') {
                        // Hide thinking spinner
                        ui.spinner.style.display = 'none';
                        ui.headerText.innerText = 'Finished thought process';
                        // Collapse steps slightly
                        ui.steps.style.opacity = '0.5';
                        
                        // Show Answer using Markdown
                        ui.answer.style.display = 'block';
                        ui.answer.innerHTML = marked.parse(data.answer);
                        
                        // Show Sources
                        if (data.sources && data.sources.length > 0) {
                            ui.sources.style.display = 'flex';
                            ui.sources.style.gap = '8px';
                            ui.sources.style.flexWrap = 'wrap';
                            
                            const uniqueSources = [];
                            const seen = new Set();
                            for (const s of data.sources) {
                                const key = s.page_number ? `${s.file_name}#page=${s.page_number}` : s.file_name;
                                if (!seen.has(key)) {
                                    seen.add(key);
                                    uniqueSources.push(s);
                                }
                            }
                            ui.sources.innerHTML = uniqueSources.map(s => {
                                const href = s.page_number ? `${API_URL}/files/${encodeURIComponent(s.file_name)}#page=${s.page_number}` : `${API_URL}/files/${encodeURIComponent(s.file_name)}`;
                                const label = s.page_number ? `📄 ${s.file_name} (Pg. ${s.page_number})` : `📄 ${s.file_name}`;
                                // Escape apostrophes and quotes for safe inline javascript
                                const safeName = s.file_name.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                                const safeUrl = href.replace(/'/g, "\\'");
                                return `<button type="button" class="source-badge" onclick="openPdfViewer('${safeUrl}', '${safeName}')">${label}</button>`;
                            }).join('');
                        }
                        
                        // Update the chat list so the new title appears
                        fetchChats();
                    } else {
                        addThoughtStep(ui, data.message);
                    }
                } catch (e) {
                    console.error("Parse error on chunk:", part, e);
                }
            }
        }
    } catch (err) {
        ui.headerText.innerText = 'Error occurred';
        ui.spinner.style.display = 'none';
        ui.answer.style.display = 'block';
        ui.answer.innerHTML = `<span style="color: #ef4444;">Sorry, something went wrong: ${err.message}</span>`;
    } finally {
        sendBtn.disabled = false;
        queryInput.disabled = false;
        queryInput.focus();
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
}

// PDF Viewer Logic
const pdfPanel = document.getElementById('pdfPanel');
const pdfIframe = document.getElementById('pdfIframe');
const closePdfBtn = document.getElementById('closePdfBtn');
const pdfPanelTitle = document.getElementById('pdfPanelTitle');
const contentWrapper = document.getElementById('contentWrapper');
const chatArea = document.getElementById('chatArea');

function openPdfViewer(url, title) {
    // Wait for a tiny timeout to let the UI settle if they double click
    setTimeout(() => {
        pdfPanelTitle.innerText = title;
        pdfIframe.src = url;
        
        // Show panel
        pdfPanel.classList.remove('hidden');
        contentWrapper.style.flexDirection = 'row';
        // Let flexbox do the shrinking of chatArea because of widths in CSS
    }, 50);
}

closePdfBtn.addEventListener('click', () => {
    pdfPanel.classList.add('hidden');
    // Clear iframe to stop loading/playing media if any, and free memory
    setTimeout(() => { pdfIframe.src = ""; }, 400); 
});

// Slash command autocomplete popup
const slashSuggestions = document.getElementById('slashSuggestions');
const activeFilterPill = document.getElementById('activeFilterPill');
const pillText = activeFilterPill.querySelector('.pill-text');
const pillClose = activeFilterPill.querySelector('.pill-close');

let currentFileNameFilter = null;

function setFileFilter(filename) {
    currentFileNameFilter = filename;
    if (filename) {
        pillText.innerText = `📄 ${filename}`;
        activeFilterPill.classList.remove('hidden');
    } else {
        activeFilterPill.classList.add('hidden');
    }
}

pillClose.addEventListener('click', () => {
    setFileFilter(null);
    queryInput.focus();
});

queryInput.addEventListener('input', (e) => {
    const val = queryInput.value;
    
    // Check if the user is typing a slash command
    const slashMatch = val.match(/^\/([^\s]*)$/);
    if (slashMatch) {
        const prefix = slashMatch[1].toLowerCase();
        
        // Find matching files
        if (window.availableFiles) {
            const matches = window.availableFiles.filter(f => 
                f.toLowerCase().includes(prefix) || 
                f.toLowerCase().startsWith(prefix)
            );
            
            if (matches.length > 0) {
                slashSuggestions.innerHTML = matches.map(m => 
                    `<div class="suggestion-item" data-value="${m}">
                        📄 <span style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${m}</span>
                    </div>`
                ).join('');
                
                // Add click events to suggestions
                slashSuggestions.querySelectorAll('.suggestion-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const selectedFile = item.getAttribute('data-value');
                        setFileFilter(selectedFile);
                        queryInput.value = ''; // Clear the input so they can type their actual question
                        slashSuggestions.classList.add('hidden');
                        queryInput.focus();
                    });
                });
                
                slashSuggestions.classList.remove('hidden');
            } else {
                slashSuggestions.classList.add('hidden');
            }
        }
    } else {
        slashSuggestions.classList.add('hidden');
    }
});

// Hide suggestions when clicking outside or pressing Escape
document.addEventListener('click', (e) => {
    if (!queryInput.contains(e.target) && !slashSuggestions.contains(e.target)) {
        slashSuggestions.classList.add('hidden');
    }
});
queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        slashSuggestions.classList.add('hidden');
    }
});

// Form Submit
chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    let query = queryInput.value.trim();
    if (!query) return;
    
    // Check for slash command at the start in case they hit Enter without clicking
    const slashMatch = query.match(/^\/([^\s]+)\s*(.*)/);
    if (slashMatch) {
        const prefix = slashMatch[1].toLowerCase();
        const restOfQuery = slashMatch[2].trim();
        
        // Search available options
        if (window.availableFiles) {
            const match = window.availableFiles.find(f => f.toLowerCase().includes(prefix) || f.toLowerCase().startsWith(prefix));
            
            if (match) {
                setFileFilter(match);
                query = restOfQuery || "Summarize this document."; // fallback if they just typed "/atomic"
            }
        }
    }
    
    addUserMessage(query);
    queryInput.value = '';
    
    streamAnswer(query, currentFileNameFilter || undefined);
});

// --- Auto-scroll helper for fileList during drag-and-drop ---
const fileListContainer = document.getElementById('fileList');
if (fileListContainer) {
    let scrollInterval = null;
    
    fileListContainer.addEventListener('dragover', (e) => {
        const threshold = 40; // Pixels from top/bottom to trigger scroll
        const scrollSpeed = 10;
        
        const rect = fileListContainer.getBoundingClientRect();
        const y = e.clientY - rect.top;
        
        if (y < threshold) {
            // Scroll up
            if (!scrollInterval) {
                scrollInterval = setInterval(() => {
                    fileListContainer.scrollTop -= scrollSpeed;
                }, 20);
            }
        } else if (rect.height - y < threshold) {
            // Scroll down
            if (!scrollInterval) {
                scrollInterval = setInterval(() => {
                    fileListContainer.scrollTop += scrollSpeed;
                }, 20);
            }
        } else {
            // Clear interval if not near edges
            if (scrollInterval) {
                clearInterval(scrollInterval);
                scrollInterval = null;
            }
        }
    });

    fileListContainer.addEventListener('dragleave', (e) => {
        // Only clear if we actually left the container
        const rect = fileListContainer.getBoundingClientRect();
        if (e.clientX <= rect.left || e.clientX >= rect.right || e.clientY <= rect.top || e.clientY >= rect.bottom) {
            if (scrollInterval) {
                clearInterval(scrollInterval);
                scrollInterval = null;
            }
        }
    });
    
    fileListContainer.addEventListener('drop', () => {
        if (scrollInterval) {
            clearInterval(scrollInterval);
            scrollInterval = null;
        }
    });
}

// --- Intercept Markdown Links in Chat ---
// If the LLM generates a markdown link, open it in our side panel instead of a new tab
chatHistory.addEventListener('click', (e) => {
    // Check if they clicked a standard markdown anchor link
    const link = e.target.closest('a');
    if (link) {
        const href = link.getAttribute('href');
        if (href) {
            e.preventDefault();
            let url = href;
            let filename = link.innerText || "Document";
            
            // If it's just a filename (not starting with http), route it through our API
            if (!url.startsWith('http')) {
                // Clean up any leading slashes or dots
                url = `${API_URL}/files/${url.replace(/^[\.\/]+/, '')}`;
            }
            
            openPdfViewer(url, filename);
        }
    }
});
