// Default function for getting csrftoken
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

// Obtain the run_id
const querystring = window.location.search;
const params = new URLSearchParams(querystring);
const run_id = params.get("run_id");

// Define buttons that call functions
const jump_diffusion_checkbox = document.getElementById("is_jump_diffusion");
const regime_switching_checkbox = document.getElementById("is_regime_switching");
const is_t_checkbox = document.getElementById("is_t");
const run_mcs_btn = document.getElementById("run_mcs_btn")

// Instantiate variables for functions
const jump_params_id = ["std_log_jump_size", "mean_log_jump_size",
                        "exp_jumps"];
const regime_switching_params_id = ["mu", "sigma"];
const is_t_params_id = ["df"];
const cleaned_params = {"run_id" : run_id}

// Create an array of inputs
const inputs_div = document.getElementById("input_wrapper");
const inputs = [];
for(const div of inputs_div.querySelectorAll("div")){
    inputs.push(div.querySelector('input'));
}

// Add events to checkbox to show/hide params
jump_diffusion_checkbox.addEventListener("change", () => show_params(jump_params_id, jump_diffusion_checkbox));
regime_switching_checkbox.addEventListener("change", () => hide_params(regime_switching_params_id,
                                            regime_switching_checkbox));
is_t_checkbox.addEventListener("change", () => show_params(is_t_params_id, is_t_checkbox));

// Add event to buttons to trigger actions
run_mcs_btn.addEventListener("click", run_graph);

function run_graph(){
    if(!validate()){return;}
    graph_mcs()
}

// This function passes the run_id and mcs params 
// to a views function which calls mcs simulate and graphs it
function graph_mcs() {
    // Pass data to views function
    console.log(cleaned_params)
    fetch("/mcs_graph/", {
        method: "POST",
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(cleaned_params)
    })
    .then(response => response.json())
    .then(data => {    //  For graph
        const mcs_graph_container = document.getElementById('mcs_graph_container');
        // Clear data
        mcs_graph_container.innerHTML = '';
        const range = document.createRange();
        const fragment = range.createContextualFragment(data["mcs_graph_html"]);
        mcs_graph_container.append(fragment);})
}

// Given an array of input ids and a checkbox, make them visible if checkbox is true
function show_params(input_id_array, checkbox){
    for(const element_id of input_id_array) {
        let element = document.getElementById(element_id)
        // console.log(element)
        if (checkbox.checked) {
            element.parentElement.style.display = "";
        }
        else {
            element.parentElement.style.display = "none";
        }
    }
}

// Given an array of input ids and a checkbox, make them hidden if checkbox is true
function hide_params(input_id_array, checkbox){
    for(const element_id of input_id_array) {
        let element = document.getElementById(element_id)
        if (checkbox.checked) {
            element.parentElement.style.display = "none";
        }
        else {
            element.parentElement.style.display = "";
        }
    }
}

// Checks if the correct parameters are filled in
function validate(){
    // Obtain list of input ids that are displayed
    // If any of their values are empty string alert
    for(const input of inputs) {
        // console.log(input.style.display)
        if(input.parentElement.style.display === "" && input.value === ""){
            alert(`Please fill in the field of ${input.name}`);
            return false;
        }
        else if(input.parentElement.style.display === "") {
            cleaned_params[input.id] = input.value;
        }
    }
    return true;
}

