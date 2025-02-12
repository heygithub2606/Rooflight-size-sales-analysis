
document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('UserUpdateForm');
    const usernameField = document.getElementById('username');
    const emailField = document.getElementById('email');

    function showValidation(field, isValid, message) {


        if (isValid) {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
            field.setCustomValidity('');
        } else {
            field.classList.remove('is-valid');
            field.classList.add('is-invalid');
            field.setCustomValidity(message);
        }
    }

    // Username validation logic
    usernameField.addEventListener('input', function () {
        const username = usernameField.value.trim(); // Trim leading/trailing spaces
        const maxLength = 20;
        let isValid = true;
        let message = '';
    
        // Trim input to max length
        if (username.length > maxLength) {
            usernameField.value = username.slice(0, maxLength); // Stop further input after maxLength
            isValid = false;
            message = `Username cannot exceed ${maxLength} characters.`;
        }
        else if (/^\s/.test(username) || /\s$/.test(username)) {
            isValid = false;
            message = 'Username cannot start or end with a space.';
        }
    
        // Disallow single-character usernames (like "a" or "1")
        else if (username.length === 1) {
            isValid = false;
            message = 'Username cannot be a single character.';
        }
    
        // Check if username length is valid (min 3 characters)
        else if (username.length < 3) {
            isValid = false;
            message = 'Username must be at least 3 characters long.';
        }
    
        // Disallow starting or ending with an underscore or period, and ensure no consecutive underscores or periods
        else if (/^[_\.]|[_\.]$/.test(username) || /__|\.{2,}/.test(username)) {
            isValid = false;
            message = 'Username cannot start or end with an underscore or period, and only one underscore or period is allowed between words.';
        }
    
        // Disallow multiple consecutive spaces or invalid characters
        else if (/[_\.\s]{2,}/.test(username)) {
            isValid = false;
            message = 'Username cannot have consecutive underscores, periods, or spaces.';
        }
        else if (/^(?:[a-zA-Z]\s)+[a-zA-Z]$/.test(username)) {
            isValid = false;
            message = 'Usernames with single characters separated by spaces are not allowed.';
        }
    
        // Only allow letters, numbers, underscores, or periods (with underscores or periods between words)
        else if (!/^[a-zA-Z0-9]+([_\.][a-zA-Z0-9]+)*$/.test(username)) {
            // This error checks invalid characters not allowed
            isValid = false;
            message = 'Username must only contain letters, numbers, and one underscore or period between words. No other special characters are allowed.';
        }
    
        // Disallow usernames that are entirely numeric
        else if (/^\d+$/.test(username)) {
            isValid = false;
            message = 'Username cannot be entirely numeric.';
        }
    
        // NEW VALIDATION: Disallow consecutive identical characters (e.g., "aa", "11", etc.)
        else if (/([a-zA-Z0-9])\1{2,}/.test(username)) {
            isValid = false;
            message = 'Username cannot contain consecutive identical characters.';
        }
    
        // Display validation message dynamically
        showValidation(usernameField, isValid, message);
    
        // Handle the error message display
        const messageContainer = document.querySelector('#username-error-message'); // Error message element
    
        if (!isValid) {
            if (!messageContainer) {
                const errorDiv = document.createElement('div');
                errorDiv.id = 'username-error-message';
                errorDiv.className = 'invalid-feedback';  // Bootstrap class for error message
                errorDiv.innerText = message;
                usernameField.parentNode.appendChild(errorDiv);
            } else {
                messageContainer.innerText = message;
            }
        } else if (messageContainer) {
            messageContainer.remove();  // Remove error message if input becomes valid
        }
    });

    // Email validation logic
    emailField.addEventListener('input', function () {
        const email = emailField.value.trim(); // Trim leading/trailing spaces
        let isValid = true;
        let message = '';
    
        // Define regex for basic email format validation
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        
        // Define max length for email
        const maxLength = 30;
    
        // Check if email is empty
        if (email.length === 0) {
            isValid = false;
            message = 'Email address is required.';
        }
        // Check if email length exceeds the maximum length
        else if (email.length > maxLength) {
            emailField.value = email.slice(0, maxLength); // Stop further input after maxLength
            isValid = false;
            message = `Email address cannot exceed ${maxLength} characters.`;
        }
        // Check for leading/trailing spaces
        else if (/^\s/.test(email) || /\s$/.test(email)) {
            isValid = false;
            message = 'Email address cannot start or end with a space.';
        }
        // Check basic email format
        else if (!emailRegex.test(email)) {
            isValid = false;
            message = 'Please enter a valid email address.';
        }
        // Ensure no invalid characters
        else if (/[^a-zA-Z0-9._%+-@]/.test(email)) {
            isValid = false;
            message = 'Email address contains invalid characters.';
        }
        // NEW VALIDATION 1: Ensure email starts with a letter
        else if (!/^[a-zA-Z]/.test(email)) {
            isValid = false;
            message = 'Email address must start with a letter.';
        }
        // NEW VALIDATION 2: Ensure ".com" does not appear more than once
        else if (email.match(/\.com/g)?.length > 1) {
            isValid = false;
            message = 'Email address cannot contain ".com" more than once.';
        }
        // NEW VALIDATION 3: Ensure email does not start or end with special characters
        else if (/^[^a-zA-Z0-9]|[^a-zA-Z0-9]$/.test(email)) {
            isValid = false;
            message = 'Email address cannot start or end with a special character.';
        }
        // NEW VALIDATION 4: Ensure no special characters between the email string (except '.' and '@')
        else if (/[^a-zA-Z0-9._@]/.test(email)) {
            isValid = false;
            message = 'Email address can only contain letters, numbers, periods, and "@" symbols.';
        }
        // NEW VALIDATION 5: Ensure no consecutive special characters like '..' or '@.'
        else if (/([._%+-]{2,})/.test(email)) {
            isValid = false;
            message = 'Email address cannot have consecutive special characters.';
        }
    
        // Display validation message dynamically
        showValidation(emailField, isValid, message);
    
        // Handle the error message display
        const messageContainer = document.querySelector('#email-error-message'); 
    
        if (!isValid) {
            if (!messageContainer) {
                const errorDiv = document.createElement('div');
                errorDiv.id = 'email-error-message';
                errorDiv.className = 'invalid-feedback';  
                errorDiv.innerText = message;
                emailField.parentNode.appendChild(errorDiv);
            } else {
                messageContainer.innerText = message;
            }
        } else if (messageContainer) {
            messageContainer.remove();  
        }
    });

 
});