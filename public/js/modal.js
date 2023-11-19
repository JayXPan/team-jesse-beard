function showModal(message) {
    const modalOverlay = document.querySelector('.modal-overlay');
    const modalMessage = document.getElementById('modalMessage');
    
    modalMessage.textContent = message;
    modalOverlay.style.display = "flex";
}

function closeModal() {
    const modalOverlay = document.querySelector('.modal-overlay');
    modalOverlay.style.display = "none";
    location.reload();
}

function showEmailModal() {
    const modal = document.querySelector('.email-modal-overlay');
    modal.style.display = 'flex';
}

// Close the email modal
function closeEmailModal() {
    const modal = document.querySelector('.email-modal-overlay');
    modal.style.display = 'none';
}

// Submit the email
function submitEmail() {
    const email = document.getElementById('email').value;
    console.log('Entered email:', email);
    closeEmailModal();

    // Send the email to the server using fetch
    const path = "/verify_email/";  // Update the path as needed
    fetch(path, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: email }),
    })
    .then(response => response.json())
    .then(data => {
        // Handle the response from the server (if needed)
        console.log(data);
    })
    .catch(error => {
        // Handle errors
        console.error(error);
    });
}

document.getElementById('email').addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        submitEmail();
    }
});