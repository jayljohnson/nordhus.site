
var klaroConfig = {
    version: 1,
    elementID: 'klaro',
    lang: 'en',
    
    // Simple, clean styling
    styling: {
        theme: ['light', 'top', 'wide']
    },
    
    // Clear, honest messaging
    translations: {
        en: {
            consentModal: {
                title: 'Cookie Preferences',
                description: 'This website uses cookies to understand how you use the site and improve your experience.',
            },
            googleAnalytics: {
                description: 'Collects anonymous usage statistics to help improve the website. Toggle to enable/disable.'
            },
        }
    },
    
    // Define your services
    services: [
        {
            name: 'googleAnalytics',
            title: 'Google Analytics',
            purposes: ['analytics'],
            required: false,
            optOut: false,
            onlyOnce: true,
            default: true,
            
            // This function runs when user consents
            callback: function(consent, service) {
                if (consent && window.location.hostname !== 'localhost') {
                    // Only load Google Analytics in production
                    if (typeof gtag !== 'undefined') {
                        gtag('config', 'G-5KRKCPHCGX');
                    }
                }
            }
        }
    ]
};

// Wait for Klaro to load, then initialize
document.addEventListener('DOMContentLoaded', function() {
    function initKlaro() {
        if (typeof klaro !== 'undefined') {
            klaro.setup(klaroConfig);
        } else {
            setTimeout(initKlaro, 100);
        }
    }
    
    initKlaro();
});