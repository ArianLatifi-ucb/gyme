let currentSlideIndex = 1;
let autoRotateTimer = null;

function showSlide(n) {
    const slides = document.querySelectorAll('.carousel-slide');
    const dots = document.querySelectorAll('.dot');

    if (n > slides.length) {
        currentSlideIndex = 1;
    }
    if (n < 1) {
        currentSlideIndex = slides.length;
    }

    slides.forEach(slide => slide.classList.remove('active'));
    dots.forEach(dot => dot.classList.remove('active'));

    slides[currentSlideIndex - 1].classList.add('active');
    dots[currentSlideIndex - 1].classList.add('active');
}

function changeSlide(n) {
    clearAutoRotate();
    currentSlideIndex += n;
    showSlide(currentSlideIndex);
    startAutoRotate();
}

function currentSlide(n) {
    clearAutoRotate();
    currentSlideIndex = n;
    showSlide(currentSlideIndex);
    startAutoRotate();
}

function autoRotate() {
    currentSlideIndex++;
    showSlide(currentSlideIndex);
}

function startAutoRotate() {
    autoRotateTimer = setInterval(autoRotate, 5000);
}

function clearAutoRotate() {
    if (autoRotateTimer) {
        clearInterval(autoRotateTimer);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    showSlide(currentSlideIndex);
    startAutoRotate();

    const carouselContainer = document.querySelector('.carousel-container');
    if (carouselContainer) {
        carouselContainer.addEventListener('mouseenter', clearAutoRotate);
        carouselContainer.addEventListener('mouseleave', startAutoRotate);
    }
});
