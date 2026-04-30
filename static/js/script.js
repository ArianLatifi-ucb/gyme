// Smooth scrolling for navigation hash links (only on same page)
document.querySelectorAll('nav a').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        // Only handle hash links that start with #
        if (href.startsWith('#')) {
            const targetId = href.substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        }
        // Non-hash links will navigate normally
    });
});

// Placeholder for course sign up
function signUp(courseName) {
    alert(`Signing up for ${courseName}. This is a placeholder - actual functionality would require login and back-end.`);
}


// Function to view all courses
function viewAllCourses() {
    window.location.href = '/courses';
}

// Function to select a membership plan
function selectPlan(planName) {
    alert(`You've selected the ${planName} plan. This is a placeholder - actual functionality would require login and payment processing.`);
}

// Function to join a membership plan
function joinMembership(planName) {
    alert(`You're joining the ${planName} membership plan! Please log in or register to complete your membership.`);
}
