async function getJSON() {
    try {
        const response = await fetch('/make-post/');
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

async function fetchData() {
    try {
        const data = await getJSON();

        const allPosts = document.getElementById("all-posts");

        const format = document.createElement("pre");

        format.textContent = JSON.stringify(data, null, 2);

        allPosts.appendChild(format);

    } catch (error) {
        console.error('Error handling the JSON data:', error);
    }
}


