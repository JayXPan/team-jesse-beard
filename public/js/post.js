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
fetchData();
setInterval(fetchData, 3000); // Poll the server every 3 seconds to update posts

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
            <footer>Posted by: ${post.username}</footer>
        `;
        allPosts.appendChild(postElement);
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

