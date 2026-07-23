// This Js has to be imported or parts of it copied to make use of some elements of components.html


// --------------------------------------------------------------------------------
// -------------------------------  Loading bar    ------------------------------------------
// --------------------------------------------------------------------------------
// Create variables to refer to the progress bar and loading text
console.log("Loaded component.js");
let progress_bar = document.querySelector(".progress-bar");
let loading_text = document.querySelector(".loading-text");
let width = 0;

function upgrade_progress() {
    console.log("updating bar");
    console.log(`progress_bar is ${progress_bar}`);
    console.log(`loading_text is ${loading_text}`);
    if (width < 100) {
        width++
        console.log(`This is the width = ${width}`)
        progress_bar.style.width = (15 + 0.85 * width) + "%";
        progress_bar.textContent = width + "%";
        setTimeout(upgrade_progress, 30);
    } else {
        // console.log(`This is the width = ${width}`)
        // progress_bar.style.width = "100%";
        loading_text.textContent = "Finished";
        loading_text.style.animation = "none";

    }
}
upgrade_progress();