document.addEventListener('DOMContentLoaded', function() {
    // Initialize Socket.IO connection
    const socket = io();
    
    // DOM elements
    const statusIndicator = document.getElementById('status-indicator');
    const uptimeElement = document.getElementById('uptime');
    const guildsElement = document.getElementById('guilds-count');
    const commandsElement = document.getElementById('commands-count');
    const gamblingElement = document.getElementById('gambling-count');
    const activeUsersElement = document.getElementById('active-users');
    const eventsFeed = document.getElementById('events-feed');
    const commandForm = document.getElementById('command-form');
    const commandInput = document.getElementById('command-input');
    const commandResponse = document.getElementById('command-response');
    
    // Connect to WebSocket
    socket.on('connect', function() {
        console.log('Connected to WebSocket');
        socket.emit('request_status');
    });
    
    // Handle status updates
    socket.on('status_update', function(data) {
        updateDashboard(data);
    });
    
    // Handle bot events
    socket.on('bot_event', function(data) {
        addEventToFeed(data);
    });
    
    // Handle form submission for commands
    if (commandForm) {
        commandForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const command = commandInput.value.trim();
            
            if (command) {
                // Send command to server
                fetch('/api/bot/command', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ command: command })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        commandResponse.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                    } else {
                        commandResponse.innerHTML = `<div class="alert alert-success">${data.response.response}</div>`;
                    }
                    
                    // Clear the input
                    commandInput.value = '';
                })
                .catch(error => {
                    console.error('Error:', error);
                    commandResponse.innerHTML = `<div class="alert alert-danger">Failed to send command</div>`;
                });
            }
        });
    }
    
    // Function to update dashboard with new status
    function updateDashboard(data) {
        if (statusIndicator) {
            statusIndicator.className = data.connected ? 'status-indicator status-online' : 'status-indicator status-offline';
            statusIndicator.title = data.connected ? 'Online' : 'Offline';
        }
        
        if (uptimeElement) {
            const uptime = formatUptime(data.uptime);
            uptimeElement.textContent = uptime;
        }
        
        if (guildsElement) guildsElement.textContent = data.guilds;
        if (commandsElement) commandsElement.textContent = data.commands_used;
        if (gamblingElement) gamblingElement.textContent = data.gambling_sessions;
        if (activeUsersElement) activeUsersElement.textContent = data.active_users;
        
        // Update events feed
        if (eventsFeed && data.latest_events) {
            // Clear current events
            eventsFeed.innerHTML = '';
            
            // Add new events
            data.latest_events.forEach(event => {
                const eventElement = document.createElement('div');
                eventElement.className = 'event-item animate-fade-in';
                
                let eventContent = '';
                if (event.type === 'command') {
                    eventContent = `<strong>${event.user}</strong> used command <code>/${event.command}</code>`;
                    if (event.amount) {
                        eventContent += ` with amount ${event.amount}`;
                    }
                } else if (event.type === 'message') {
                    eventContent = `<strong>${event.user}</strong> sent a message in <em>${event.channel}</em>`;
                }
                
                eventElement.innerHTML = `
                    ${eventContent}
                    <div class="event-timestamp">${event.timestamp}</div>
                `;
                
                eventsFeed.prepend(eventElement);
            });
        }
    }
    
    // Function to add a new event to the feed
    function addEventToFeed(event) {
        if (!eventsFeed) return;
        
        const eventElement = document.createElement('div');
        eventElement.className = 'event-item animate-fade-in';
        
        let eventContent = '';
        if (event.type === 'command_used') {
            eventContent = `<strong>${event.user}</strong> used command <code>/${event.command}</code>`;
        } else if (event.type === 'gambling_result') {
            const resultText = event.result === 'win' ? 'won' : 'lost';
            eventContent = `<strong>${event.user}</strong> ${resultText} a gambling game with ${event.amount} coins`;
        }
        
        const timestamp = new Date().toLocaleTimeString();
        eventElement.innerHTML = `
            ${eventContent}
            <div class="event-timestamp">${timestamp}</div>
        `;
        
        eventsFeed.prepend(eventElement);
        
        // Limit the number of events
        if (eventsFeed.children.length > 20) {
            eventsFeed.removeChild(eventsFeed.lastChild);
        }
    }
    
    // Function to format uptime
    function formatUptime(seconds) {
        if (!seconds) return '0m 0s';
        
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        let result = '';
        if (days > 0) result += `${days}d `;
        if (hours > 0) result += `${hours}h `;
        if (minutes > 0) result += `${minutes}m `;
        result += `${secs}s`;
        
        return result;
    }
    
    // Fetch initial status
    fetch('/api/bot/status')
        .then(response => response.json())
        .then(data => {
            updateDashboard(data);
        })
        .catch(error => {
            console.error('Error fetching bot status:', error);
        });
    
    // Auto-refresh status every 10 seconds
    setInterval(() => {
        fetch('/api/bot/status')
            .then(response => response.json())
            .then(data => {
                updateDashboard(data);
            })
            .catch(error => {
                console.error('Error fetching bot status:', error);
            });
    }, 10000);
});
