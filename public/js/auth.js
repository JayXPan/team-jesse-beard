async function loginUser() {
    const formData = new FormData(document.querySelector('.login form'));
    
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
    const formData = new FormData(document.querySelector('.registration form'));
    
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

document.querySelector('.login input[type="submit"]').addEventListener('click', (event) => {
    event.preventDefault(); 
    loginUser();             
});

document.querySelector('.registration input[type="submit"]').addEventListener('click', (event) => {
    event.preventDefault();
    registerUser();
});
