// Admin panel functionality for managing courses
document.addEventListener('DOMContentLoaded', function() {
    loadCourses();
    document.getElementById('course-form').addEventListener('submit', saveCourse);
});

function saveCourse(e) {
    e.preventDefault();
    const name = document.getElementById('course-name').value;
    const description = document.getElementById('course-description').value;
    const duration = document.getElementById('course-duration').value;
    const schedule = document.getElementById('course-schedule').value;
    const instructor = document.getElementById('course-instructor').value;

    const course = {
        name,
        description,
        duration,
        schedule,
        instructor
    };

    // Save to localStorage (front-end only)
    let courses = JSON.parse(localStorage.getItem('gyme-courses')) || [];
    courses.push(course);
    localStorage.setItem('gyme-courses', JSON.stringify(courses));

    alert('Course saved successfully!');
    clearForm();
    loadCourses();
}

function clearForm() {
    document.getElementById('course-form').reset();
}

function loadCourses() {
    const courses = JSON.parse(localStorage.getItem('gyme-courses')) || [];
    const container = document.getElementById('current-courses');
    container.innerHTML = '';

    if (courses.length === 0) {
        container.innerHTML = '<p>No courses added yet.</p>';
        return;
    }

    courses.forEach((course, index) => {
        const courseDiv = document.createElement('div');
        courseDiv.className = 'course';
        courseDiv.innerHTML = `
            <h4>${course.name}</h4>
            <p>${course.description}</p>
            <p><strong>Duration:</strong> ${course.duration} minutes</p>
            <p><strong>Schedule:</strong> ${course.schedule}</p>
            <p><strong>Instructor:</strong> ${course.instructor}</p>
            <button onclick="editCourse(${index})">Edit</button>
            <button onclick="deleteCourse(${index})">Delete</button>
        `;
        container.appendChild(courseDiv);
    });
}

function editCourse(index) {
    const courses = JSON.parse(localStorage.getItem('gyme-courses')) || [];
    const course = courses[index];
    document.getElementById('course-name').value = course.name;
    document.getElementById('course-description').value = course.description;
    document.getElementById('course-duration').value = course.duration;
    document.getElementById('course-schedule').value = course.schedule;
    document.getElementById('course-instructor').value = course.instructor;

    // Remove the course so it can be re-added with edits
    courses.splice(index, 1);
    localStorage.setItem('gyme-courses', JSON.stringify(courses));
    loadCourses();
}

function deleteCourse(index) {
    if (confirm('Are you sure you want to delete this course?')) {
        const courses = JSON.parse(localStorage.getItem('gyme-courses')) || [];
        courses.splice(index, 1);
        localStorage.setItem('gyme-courses', JSON.stringify(courses));
        loadCourses();
    }
}
