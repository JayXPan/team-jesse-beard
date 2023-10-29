/**
 * Fetch the posts from the server in JSON format.
 */
async function getJSON() {
    try {
        const response = await fetch('/get-posts/');
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
        throw error;
    }
}

/**
 * Fetch and display posts.
 */
async function fetchData() {
    try {
        const data = await getJSON();
        displayPosts(data.posts);
    } catch (error) {
        console.error('Error handling the JSON data:', error);
    }
}

// Call fetchData once on page load
window.addEventListener('load', function() {
    setupWebSocket();
    fetchData();
});

/**
 * Display the posts to the page.
 * @param {Array} posts - List of posts to display.
 */
function displayPosts(posts) {
    const allPosts = document.getElementById("all-posts");
    allPosts.innerHTML = '';  
    posts.forEach(post => {
        const postElement = document.createElement("div");
        // const currentTime = new Date();
        // const endTime = new Date(post.end_time);
        // const timeDifference = endTime - currentTime;
        // let timeDisplay;
        // if (timeDifference <= 0) {
        //     timeDisplay = "Expired";
        // } else {
        //     const minutesRemaining = Math.floor(timeDifference / (1000 * 60));
        //     timeDisplay = `${minutesRemaining} minutes`;
        // }
        postElement.setAttribute("data-id", post.id);
        postElement.innerHTML = `
            <h3>${post.title}</h3>
            <p>${post.description}</p>
            <img src="/static/images/${post.image}" alt="${post.title} style="width: 100%; max-height: 100px;">
            <div class="bid-display">
                <strong>Highest bid:</strong> <span class="bid-value">$${post.current_bid || post.starting_price}</span>
            </div>
            <div>
                <div class="time-remaining"></div>
            </div>
            <div class="bid-section">
                <input type="number" id="bid-input-${post.id}" min="${post.current_bid + 1 || post.starting_price + 1}" placeholder="Enter your bid">
                <button onclick="placeBid(${post.id})">Place Bid</button>
            </div>
            <button 
                id="like-btn-${post.id}" 
                onclick="toggleLike(${post.id})"
            >
                ${post.liked ? 'Dislike' : 'Like'} (${post.likes})
            </button>
            <footer>Posted by: ${post.username}</footer>
        `;
        allPosts.appendChild(postElement);
        const timeDisplay = postElement.querySelector('.time-remaining');
        const endTime = new Date(post.end_time);
        startCountdown(endTime, timeDisplay);
    });
}

/**
 * Handle the post submission form, send data to the server and update UI accordingly.
 * @param {Event} event - The form submission event.
 */
async function handlePostSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const response = await fetch('/make-post/', {
        method: 'POST',
        body: formData
    });
    
    if (response.ok) {
        const responseData = await response.json();
        const message = `Post by ${responseData.username}: "${responseData.title}" has been successfully created!`;
        showModal(message);
        fetchData();
    } else {
        const errorData = await response.json();
        showModal(errorData.error);
    }
}

/**
 * Toggles the like state of a specific post.
 * @param {number} postId - The ID of the post whose like status is to be toggled.
 */
async function toggleLike(postId) {
    const response = await fetch(`/toggle-like/${postId}`, { method: 'POST' });
    
    if (response.ok) {
        const data = await response.json();
        const likeBtn = document.querySelector(`#like-btn-${postId}`);
        likeBtn.innerText = `${data.likedByUser ? 'Dislike' : 'Like'} (${data.likes})`;
    } else {
        const errorData = await response.json();
        showModal(errorData.error);
    }
}

let ws = null;

function setupWebSocket() {
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";

    ws = new WebSocket(wsProtocol + '://' + window.location.host + '/websocket');

    ws.onopen = () => {
        console.log('WebSocket connection opened');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'postsUpdated') {
            fetchData();
        } else if (data.type === 'bidUpdate') {
            updateBid(data.auction_id, data.value);
        }
        if (data.error) {
            alert(data.error);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket encountered an error:', error);
    };

    ws.onclose = (event) => {
        console.log('WebSocket connection closed:', event);
        setTimeout(setupWebSocket, 5000); // Try to reconnect every 5 seconds
    };
}

/**
 * Place a bid for a specific auction item.
 * @param {number} postId - The ID of the post on which the bid is to be placed.
 */
async function placeBid(postId) {
    const bidValue = document.getElementById(`bid-input-${postId}`).value;
    if (!bidValue) {
        alert('Please enter a bid amount.');
        return;
    }

    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'bid',
            value: bidValue,
            auction_id: postId
        }));
    }
}

function updateBid(auction_id, value) {
    const bidValueElement = document.querySelector(`[data-id='${auction_id}'] .bid-value`);
    if (bidValueElement) {
        bidValueElement.textContent = `$${value}`;
    }
}

function startCountdown(endTime, displayElement) {
    function updateTimer() {
        const currentTime = new Date();
        let difference = endTime - currentTime;

        if (difference <= 0) {
            clearInterval(interval);
            displayElement.innerHTML = "<strong>Time Remaining:</strong> Expired";
            return;
        }

        // Calculate days, hours, minutes, and seconds remaining
        const days = Math.floor(difference / (1000 * 60 * 60 * 24));
        difference -= days * (1000 * 60 * 60 * 24);

        const hours = Math.floor(difference / (1000 * 60 * 60));
        difference -= hours * (1000 * 60 * 60);

        const minutes = Math.floor(difference / (1000 * 60));
        difference -= minutes * (1000 * 60);

        const seconds = Math.floor(difference / 1000);

        displayElement.innerHTML = `<strong>Time Remaining:</strong> ${days}d ${hours}h ${minutes}m ${seconds}s`;
    }

    const interval = setInterval(updateTimer, 1000);
    updateTimer();
}