function moveNavbar() {
    var navbar = document.getElementsByClassName("navbar")[0];
    var navbarUl = navbar.querySelector("ul");
    const navbarButton = document.getElementsByClassName("navbar-button")[0];
    if (navbarUl.style.width == "0px") {
        navbarUl.style.width = "100px";
    }
    else {
        navbarUl.style.width = "0px";
    }
}