const loginEmail = document.getElementById("login-email");
const loginPassword = document.getElementById("login-password");
const loginErrorMsg = document.getElementById("login-err");
const loginForm = document.getElementById("login-form");

function validateLogin(event) {
    if (loginEmail.length == 0) {
        loginErrorMsg.innerHTML = "Please provide your email.";
    }
    else if (loginPassword.length == 0) {
        loginErrorMsg.innerHTML = "Please provide your password.";
    }
    else {
        fetch("/verify-login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                email: loginEmail.value,
                username: "",
                password: loginPassword.value
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status == "OK") {
                loginErrorMsg.innerHTML = "";
                window.location.href = "/chatbot";
            }
            else {
                loginErrorMsg.innerHTML = data.status;
                loginErrorMsg.style.color = "red";
            }
        })
        .catch(error => {
            alert(error);
        })
    }

    return false;
}