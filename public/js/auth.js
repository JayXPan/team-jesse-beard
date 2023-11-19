
document.getElementById('verificationLink').addEventListener('click', function(event) {
    event.preventDefault();
    const line = document.getElementById("usernameText").textContent.trim();
    const username = line.substring(0, 5);
    console.log(username)
    if (username === "Guest") {
        showModal('Please login to verify email.');
    } else {
        showEmailModal();
    }
    });

async function loginUser() {
    const formData = new FormData(document.querySelector('.loginNew form'));
    
    const response = await fetch('/login/', {
        method: 'POST',
        body: formData
    });

    const responseData = await response.json();

    if (response.status === 200) {
        showModal('Login successful. You can close this modal now.');
    } else {
        showModal(responseData.detail);
    }
}

async function registerUser() {
    const formData = new FormData(document.querySelector('.registerNew form'));
    
    const response = await fetch('/register/', {
        method: 'POST',
        body: formData
    });

    const responseData = await response.json();

    if (response.status === 200) {
        showModal('Registration successful. Please log in.');
    } else {
        showModal(responseData.detail);
    }
}

document.querySelector('.loginNew input[type="submit"]').addEventListener('click', (event) => {
    event.preventDefault(); 
    loginUser();             
});

document.querySelector('.registerNew input[type="submit"]').addEventListener('click', (event) => {
    event.preventDefault();
    registerUser();
});
