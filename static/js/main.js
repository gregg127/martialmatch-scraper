document.addEventListener('DOMContentLoaded', function() {
    const greeting = document.querySelector('h1');
    greeting.addEventListener('click', function() {
        this.style.transform = 'scale(1.1)';
        setTimeout(() => {
            this.style.transform = 'scale(1)';
        }, 200);
    });
});
