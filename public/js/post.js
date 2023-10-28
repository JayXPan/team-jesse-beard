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
    fetchData();
    setupWebSocket();
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
        postElement.innerHTML = `
            <h3>${post.title}</h3>
            <p>${post.description}</p>
            <img src="/static/images/${post.image}" alt="${post.title} style="width: 100%; max-height: 100px;">
            <div>
                <strong>Highest bid:</strong> $${post.current_bid || post.starting_price}
            </div>
            <div>
                <strong>Time remaining:</strong> ${post.duration} minutes
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
    });
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
    
    const response = await fetch(`/place-bid/${postId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            bid: bidValue
        })
    });
    
    if (response.ok) {
        const data = await response.json();
        // Update the UI accordingly, for example, display a success message or update the highest bid.
        alert('Bid placed successfully!');
    } else {
        const errorData = await response.json();
        alert(errorData.error);
    }
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

let ws;

function setupWebSocket() {
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";

    ws = new WebSocket(wsProtocol + '://' + window.location.host + '/ws');

    ws.onopen = (event) => {
        console.log('WebSocket connection opened:', event);
        // You can send a message to the server if needed
        // ws.send('Hello server!');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // Assuming the server sends a message type "postsUpdated" when there's new post data
        if (data.type === 'postsUpdated') {
            fetchData();
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket encountered an error:', error);
    };

    ws.onclose = (event) => {
        console.log('WebSocket connection closed:', event);
        // You can add logic to attempt reconnection if desired
        setTimeout(setupWebSocket, 5000); // Try to reconnect every 5 seconds
    };
}