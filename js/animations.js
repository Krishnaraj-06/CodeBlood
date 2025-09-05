// Smooth animations for AttendIQ
document.addEventListener('DOMContentLoaded', function() {
    // Fade in animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    // Observe all elements with animation classes
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });

    // Floating shapes animation
    const shapes = document.querySelectorAll('.floating-shapes .shape');
    shapes.forEach((shape, index) => {
        shape.style.animationDelay = `${index * 2}s`;
    });

    // Particle animation
    const particles = document.querySelectorAll('.particles');
    particles.forEach(particle => {
        particle.style.animationDuration = '20s';
    });

    // Smooth scroll for navigation
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Mobile menu toggle
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
            navToggle.classList.toggle('active');
        });
    }
});

// Add smooth loading animations
window.addEventListener('load', function() {
    document.body.classList.add('loaded');
    
    // Animate stats
    const statNumbers = document.querySelectorAll('.stat-number');
    statNumbers.forEach(stat => {
        const finalValue = stat.textContent;
        if (finalValue.includes('+') || finalValue.includes('%')) {
            animateNumber(stat, finalValue);
        }
    });
});

function animateNumber(element, finalValue) {
    const isPercentage = finalValue.includes('%');
    const isPlus = finalValue.includes('+');
    const numericValue = parseInt(finalValue.replace(/[^0-9]/g, ''));
    
    let current = 0;
    const increment = numericValue / 50;
    const timer = setInterval(() => {
        current += increment;
        if (current >= numericValue) {
            current = numericValue;
            clearInterval(timer);
        }
        
        let displayValue = Math.floor(current);
        if (isPercentage) displayValue += '%';
        if (isPlus) displayValue += '+';
        
        element.textContent = displayValue;
    }, 30);
}

