const queryBox = document.getElementById("query");
queryBox.addEventListener("keydown", preventEnterDefault);

// Prevent default textarea behavior
// Print user message to page and send message to FastAPI endpoint
// Retrieve GPT response and output it to page
function preventEnterDefault(e) {
    if (e.keyCode == 13) {
        e.preventDefault();

        const chat = document.querySelector("ul");
        const userMessage = queryBox.value;

        const msgListElement = document.createElement("li");
        msgListElement.innerHTML = userMessage;

        chat.appendChild(msgListElement);
        queryBox.value = "";

        fetch("/chatbot", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({query: userMessage})
        })
        .then(response => response.json())
        .then(data => {
            const GPTListElement = document.createElement("li");
            GPTListElement.innerHTML = data.result;
            chat.appendChild(GPTListElement);
        })
        .catch((error) => {
            alert("Oops, something went wrong!");
        });
    }
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
            alert(JSON.stringify(data));
        })
        .catch(error => {
            alert(error);
        })
    }

    return false;
}