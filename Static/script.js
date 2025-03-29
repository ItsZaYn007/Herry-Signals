document.addEventListener("DOMContentLoaded", function () {
    setTimeout(() => {
        document.getElementById("loading").style.display = "none";
        document.getElementById("prediction-box").classList.remove("hidden");
    }, 1500);
});