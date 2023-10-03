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