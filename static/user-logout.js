function userLogout() {
    fetch("/logout", {
        method: "GET"
    })
    .catch(error => {
        alert(error);
    })
    window.location.href = "/chatbot";
}