// Main JavaScript for AttendIQ Landing Page

document.addEventListener('DOMContentLoaded', function() {
    // Initialize countdown timer
    initCountdownTimer();
    
    // Initialize smooth scrolling for navigation
    initSmoothScrolling();
    
    // Initialize mobile navigation
    initMobileNav();
    
    // Initialize scroll animations
    initScrollAnimations();
});

// Countdown Timer Functionality
function initCountdownTimer() {
    const timerDisplay = document.querySelector('.timer-display');
    if (!timerDisplay) return;
    
    // Set target date (24 hours from now)
    const targetDate = new Date();
    targetDate.setHours(targetDate.getHours() + 24);
    
    function updateTimer() {
        const now = new Date();
        const difference = targetDate - now;
        
        if (difference <= 0) {
            // Timer expired
            timerDisplay.innerHTML = '<span class="timer-unit">00</span>:<span class="timer-unit">00</span>:<span class="timer-unit">00</span>';
            return;
        }
        
        const hours = Math.floor(difference / (1000 * 60 * 60));
        const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((difference % (1000 * 60)) / 1000);
        
        const hoursStr = hours.toString().padStart(2, '0');
        const minutesStr = minutes.toString().padStart(2, '0');
        const secondsStr = seconds.toString().padStart(2, '0');
        
        timerDisplay.innerHTML = `
            <span class="timer-unit">${hoursStr}</span>:
            <span class="timer-unit">${minutesStr}</span>:
            <span class="timer-unit">${secondsStr}</span>
        `;
    }
    
    // Update timer every second
    updateTimer();
    setInterval(updateTimer, 1000);
}

// Smooth Scrolling for Navigation
function initSmoothScrolling() {
    const navLinks = document.querySelectorAll('.nav-link[href^="#"]');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            
            if (targetSection) {
                const offsetTop = targetSection.offsetTop - 70; // Account for fixed navbar
                
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
}

// Mobile Navigation Toggle
function initMobileNav() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            navToggle.classList.toggle('active');
        });
        
        // Close mobile menu when clicking on a link
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                navMenu.classList.remove('active');
                navToggle.classList.remove('active');
            });
        });
    }
}

// Scroll Animations
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);
    
    // Observe elements for animation
    const animateElements = document.querySelectorAll('.feature-card, .testimonial-card, .stat-card, .about-feature');
    animateElements.forEach(el => {
        observer.observe(el);
    });
}

// Interactive Demo Button
function initDemoButton() {
    const demoButton = document.querySelector('.btn-demo');
    if (demoButton) {
        demoButton.addEventListener('click', function() {
            // Show demo modal or redirect to demo page
            alert('Demo functionality coming soon! This would typically open an interactive demo or redirect to a demo page.');
        });
    }
}

// Feature Demo Buttons
function initFeatureButtons() {
    const featureButtons = document.querySelectorAll('.btn-feature');
    featureButtons.forEach(button => {
        button.addEventListener('click', function() {
            const featureName = this.closest('.feature-card').querySelector('.feature-title').textContent;
            alert(`Demo for ${featureName} coming soon!`);
        });
    });
}

// Trust Logo Hover Effects
function initTrustLogos() {
    const trustLogos = document.querySelectorAll('.trust-logo');
    trustLogos.forEach(logo => {
        logo.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.05)';
        });
        
        logo.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
}

// Statistics Counter Animation
function initStatsCounter() {
    const statNumbers = document.querySelectorAll('.stat-number');
    
    const observerOptions = {
        threshold: 0.5
    };
    
    const statsObserver = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounter(entry.target);
                statsObserver.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    statNumbers.forEach(stat => {
        statsObserver.observe(stat);
    });
}

function animateCounter(element) {
    const target = parseInt(element.textContent.replace(/\D/g, ''));
    const duration = 2000;
    const step = target / (duration / 16);
    let current = 0;
    
    const timer = setInterval(() => {
        current += step;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        
        if (element.textContent.includes('+')) {
            element.textContent = Math.floor(current) + '+';
        } else if (element.textContent.includes('%')) {
            element.textContent = Math.floor(current) + '%';
        } else if (element.textContent.includes('/')) {
            element.textContent = Math.floor(current) + '/5';
        } else {
            element.textContent = Math.floor(current);
        }
    }, 16);
}

// Initialize additional functionality
document.addEventListener('DOMContentLoaded', function() {
    initDemoButton();
    initFeatureButtons();
    initTrustLogos();
    initStatsCounter();
});

