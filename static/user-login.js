function validateLogin(event) {
    const loginEmail = document.getElementById("login-email").value;
    const loginPassword = document.getElementById("login-password").value;
    const loginErrorMsg = document.getElementById("login-err");

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
                email: loginEmail,
                username: "",
                password: loginPassword
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status == "OK") {
                loginErrorMsg.innerHTML = "";
                fetch("/chatbot", {method: "GET"});
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