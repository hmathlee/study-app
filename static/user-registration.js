const title = document.querySelector("title");
const header = document.querySelector("h1");
const inputElement = document.querySelector("input");
const registrationErrorMsg = document.getElementById("reg-err");
const registrationForm = document.getElementById("reg-form");
registrationForm.addEventListener("submit", validateUserInfo);

const userInfo = {};
registrationErrorMsg.style.color = "red";

function validateUserInfo(event) {
    event.preventDefault();
    const userInput = inputElement.value;
    inputElement.value = "";

    switch(title.innerHTML) {
        // username
        case("Username"):
            userInfo.username = userInput;
            title.innerHTML = "Password";
            header.innerHTML = "Password";

            // Hide the password for security
            inputElement.type = "password";
            break;

        // password
        case("Password"):
            // at least 8 characters, with at least one letter/number
            if (userInput.length < 8) {
                registrationErrorMsg.innerHTML = "Your password must be at least 8 characters long."
                return false;
            }

            var letters = 0;
            var numbers = 0;
            for (let i = 0; i < userInput.length; i++) {
                const char = userInput[i];
                if (/^[a-zA-Z]$/.test(char)) {
                    letters += 1;
                }
                else if (/^[0-9]$/.test(char)) {
                    numbers += 1;
                }
            }

            if (letters == 0 || numbers == 0) {
                registrationErrorMsg.innerHTML = "Your password must include at least one letter and at least one number.";
                return false;
            }

            userInfo.password = userInput;

            fetch("/register-user", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(userInfo)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status == "OK") {
                    window.location.href = "/chatbot";
                }
                else {
                    registrationErrorMsg.innerHTML = data.status;
                }
            })
            .catch(error => {
                alert(error);
            })
            break;

        // email
        default:
            // modify later
            if (!userInput.includes("@")) {
                registrationErrorMsg.innerHTML = "Please input a valid email address.";
            }
            else {
                userInfo.email = userInput;
                fetch("/register-user", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(userInfo)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status == "OK") {
                        title.innerHTML = "Username";
                        header.innerHTML = "Username";
                    }
                    else {
                        registrationErrorMsg.innerHTML = data.status;
                    }
                })
                .catch(error => {
                    alert(error);
                })
            }
            break;
    }

    return false;
}