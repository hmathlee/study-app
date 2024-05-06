const title = document.querySelector("title");
const header = document.querySelector("h1");
const inputElement = document.querySelector("input");
const form = document.querySelector("form");
form.addEventListener("submit", validateUserInfo);

const userInfo = {};

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
            break;

        // password
        case("Password"):
            // at least 8 characters, with at least one letter/number
            if (userInput.length < 8) {
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
                alert(JSON.stringify(data));
            })
            .catch(error => {
                alert(error);
            })

            form.submit();
            window.location.href = "/chatbot";

            break;

        // email
        default:
            // modify later
            if (!userInput.includes("@")) {
                return false;
            }

            userInfo.email = userInput;
            title.innerHTML = "Username";
            header.innerHTML = "Username";
            break;
    }

    return false;
}
