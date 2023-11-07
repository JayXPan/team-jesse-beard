let ws = null;

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
    const auctionsWon = document.getElementById("auctions-won");
    const auctionsCreated = document.getElementById("auctions-created");
    allPosts.innerHTML = '';
    auctionsWon.innerHTML = '';
    const currentUsername = document.getElementById("usernameText").textContent;
    posts.forEach(post => {
        const postElement = document.createElement("div");
        const currentTime = new Date();
        const endTime = new Date(post.end_time);
        let bidLabel = 'Highest bid:';
        let bidValue = post.current_bid || post.starting_price;
        let winnerSectionHTML = '';

        if (currentTime > endTime) {
            bidLabel = 'Winning bid:';
            bidValue = post.winning_bid || bidValue;

            if (post.winner) {
                winnerSectionHTML = `<div><strong>Winner:</strong> ${post.winner}</div>`;
            }
        }

        postElement.setAttribute("data-id", post.id);
        postElement.innerHTML = `
            <h3>${post.title}</h3>
            <p>${post.description}</p>
            <img src="/static/images/${post.image}" alt="${post.title} style="width: 100%; max-height: 100px;">
            <div class="bid-display">
                <strong>${bidLabel}</strong> <span class="bid-value">$${bidValue}</span>
            </div>
            ${winnerSectionHTML}
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
        // Add to All Auctions
        const postCloneForAll = postElement.cloneNode(true);
        const timeDisplayAll = postCloneForAll.querySelector('.time-remaining');
        startCountdown(endTime, timeDisplayAll);
        allPosts.appendChild(postCloneForAll);

        // For Auctions Won by the user
        if (currentTime > endTime && post.winner === currentUsername) {
            const postCloneForWon = postElement.cloneNode(true);
            const timeDisplayWon = postCloneForWon.querySelector('.time-remaining');
            startCountdown(endTime, timeDisplayWon);
            auctionsWon.appendChild(postCloneForWon);
        } 

        // For Auctions Created by the user
        if (currentUsername === post.username) {
            const postCloneForCreated = postElement.cloneNode(true);
            const timeDisplayCreated = postCloneForCreated.querySelector('.time-remaining');
            startCountdown(endTime, timeDisplayCreated);
            auctionsCreated.appendChild(postCloneForCreated);
        }
        
        const timeDisplay = postElement.querySelector('.time-remaining');
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
        const ws_message = {
            type: "newPostRequest"
        };
        ws.send(JSON.stringify(ws_message));
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

/**
 * Setup the WebSocket connection and event listeners
 */
function setupWebSocket() {
    // Determine the WebSocket protocol based on the current window protocol
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";

    // Initialize WebSocket with the appropriate URL
    ws = new WebSocket(wsProtocol + '://' + window.location.host + '/websocket');

    ws.onopen = () => {
        console.log('WebSocket connection opened');
    };

    // Handle incoming WebSocket messages
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'bidUpdate') {
            updateBid(data.auction_id, data.value);
        } else if (data.type === 'newPost') {
            const posts = data.post.map(convertArrayToPostObject);
            displayPosts(posts);
        } else if (data.error) {
            alert(data.error);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket encountered an error:', error);
    };

    ws.onclose = (event) => {
        if(event.code == 1001) {
            console.log("WebSocket closed due to page refresh or navigation.");
        } else {
            console.log(`WebSocket closed unexpectedly with code ${event.code}. Reason: ${event.reason}`);
            console.log("WebSocket closed unexpectedly. Trying to reconnect...");
            setTimeout(setupWebSocket(), 5000);  // Try to reconnect every 5 seconds
        }
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

/**
 * Update the displayed bid value for an auction
 */
function updateBid(auction_id, value) {
    const bidValueElement = document.querySelector(`[data-id='${auction_id}'] .bid-value`);
    if (bidValueElement) {
        bidValueElement.textContent = `$${value}`;
    }
}

/**
 * Start a countdown timer for the auction, updating the displayed time remaining
 */
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

/**
 * Toggle the visibility of a dropdown menu
 */
function toggleDropdown(dropdownId) {
    // Hide all dropdowns first
    const dropdownContents = document.querySelectorAll('.dropdown-content');
    dropdownContents.forEach(dropdown => {
        dropdown.style.display = 'none';
    });

    // Show the clicked dropdown
    const dropdownContent = document.getElementById(dropdownId);
    dropdownContent.style.display = dropdownContent.style.display === 'none' ? 'block' : 'none';
}

/**
 * Convert an array of post data to a structured post object
 */
function convertArrayToPostObject(arr) {
    return {
        id: arr[0],
        username: arr[1],
        title: arr[2],
        description: arr[3],
        image: arr[4],
        starting_price: arr[5],
        current_bid: arr[6],
        current_bidder: arr[7],
        end_time: arr[8],
        duration: arr[9],
        winner: arr[10],
        winning_bid: arr[11],
        likes: arr[12],
        liked: arr[13]
    };
}