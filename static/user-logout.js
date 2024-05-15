function userLogout() {
    fetch("/logout", {
        method: "GET"
    })
    .catch(error => {
        alert(error);
    })
    fetch("/chatbot", {
        method: "GET"
    })
    .catch(error => {
        alert(error);
    })
}