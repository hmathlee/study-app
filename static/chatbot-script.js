window.addEventListener("beforeunload", function(e) {
    if (document.visibilityState == "hidden") {
        fetch("/logout", {method: "GET"})
        .catch(error => {
            alert(error);
        });
    }
});

const queryBox = document.getElementById("query");
queryBox.addEventListener("keydown", handleQueryEnter);

const followupButtonContainer = document.getElementsByClassName("follow-up-queries-container")[0];
const followupButtons = followupButtonContainer.children;

for (let i = 0; i < followupButtons.length; i++) {
    followupButtons[i].addEventListener("click", handleFollowupButtonClick);
}

function handleQueryEnter(e) {
    if (e.keyCode == 13) {
        e.preventDefault();
        const userQuery = queryBox.value;
        sendQuery(userQuery);
    }
}

function handleFollowupButtonClick() {
    if (this.tagName == "BUTTON") {
        const userQuery = this.innerHTML;
        sendQuery(userQuery);
    }
}


function sendQuery(userQuery) {
    const msgListElement = document.createElement("li");
    msgListElement.innerHTML = userQuery;
    msgListElement.className = "user-msg";

    const chat = document.querySelector("#chat-box");
    chat.appendChild(msgListElement);
    queryBox.value = "";

    const GPTListElement = document.createElement("li");
    GPTListElement.innerHTML = "Thinking...";
    GPTListElement.className = "ai-msg";
    chat.appendChild(GPTListElement);
    chat.scrollTo(0, chat.scrollHeight);

    fetch("/chatbot", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({query: userQuery})
    })
    .then(response => response.json())
    .then(data => {
        const GPTResponse = data.result;

        // Parse GPT response
        const words = GPTResponse.split(/[ /]);
        for (const word of words) {

        }

        GPTListElement.innerHTML = GPTResponse;
        for (let i = 0; i < followupButtons.length; i++) {
            followupButtons[i].innerHTML = data.followups[i];
        }
    })
    .catch((error) => {
        alert("Oops, something went wrong!");
    })
    .finally(() => chat.scrollTo(0, chat.scrollHeight));
}


function validateFileUpload() {
    const fileUpload = document.getElementById("file-upload");
    const allowedExt = ["pdf"];

    const file = fileUpload.files[0];
    const fileExt = file.name.split('.').pop().toLowerCase();
    if (!allowedExt.includes(fileExt)) {
        alert("Invalid file type");
    }
    else {
        const formData = new FormData();
        formData.append("payload", file, file.name);

        const uploadStatus = document.getElementById("upload-status");

        fetch("/upload-files", {
            method: "POST",
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                alert("Local upload failed");
            }
            return response.json();
        })
        .then(data => {
            uploadStatus.style.color = "black";
            uploadStatus.innerHTML = "Uploading your files...";
            return fetch("/upload-to-google-cloud", {
                method: "POST",
            })
        })
        .then(response => {
            if (!response.ok) {
                alert("Cloud upload failed");
            }
            return response.json()
        })
        .then(data => {
            // Update message on-screen to indicate a successful cloud upload
            uploadStatus.style.color = "green";
            uploadStatus.innerHTML = "File uploaded!";
        })
        .catch(error => {
            alert(error);
        })
    }

    return false;
}
