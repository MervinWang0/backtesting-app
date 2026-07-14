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
const run_mcs_btn = document.getElementById("run_mcs_btn");
const quicktest_btn = document.getElementById("quicktest_btn");

// Instantiate variables for functions
const jump_params_id = ["std_log_jump_size", "mean_log_jump_size",
                        "exp_jumps"];
// Currently as mcs does not take in user input for daily mu and sigma,
// regime_switching params are none
const regime_switching_params_id = [];
const is_t_params_id = ["df"];
const cleaned_params = {"run_id" : run_id};

// Create an array of inputs. Obtained by selecting all input-fields of the input grid.
// This input list contains visible and hidden inputs
const input_grid = document.getElementById("input_container")
const param_divs = input_grid.querySelectorAll(".input-field");
const inputs = [];
for(const div of param_divs){
    inputs.push(div.querySelector("input"));
}
console.log(inputs);

// Obtain variables for quicktest
const param_list = get_param_list()

// Add events to checkbox to show/hide params
jump_diffusion_checkbox.addEventListener("change", () => show_params(jump_params_id, jump_diffusion_checkbox));
regime_switching_checkbox.addEventListener("change", () => hide_params(regime_switching_params_id,
                                            regime_switching_checkbox));
is_t_checkbox.addEventListener("change", () => show_params(is_t_params_id, is_t_checkbox));

// Variable for output container
const output_container = document.getElementById("output_container");

// Add event to buttons to trigger actions
run_mcs_btn.addEventListener("click", run_graph);
quicktest_btn.addEventListener("click", () => quicktest(param_list))

function run_graph(){
    if(!validate()){return;}
    graph_mcs()
}

function reset() {
    // Hide the output table
    output_container.style.display = "none";

    // Turn all input fields to none
    for (const input of inputs) {
        input.value = "";
    }
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
        console.log(`This is what html of graph looks like ${fragment}`);
        mcs_graph_container.append(fragment);});

        // Make visible output
        output_container.style.display = "";
}

// Given an array of input ids and a checkbox, make them visible if checkbox is true
function show_params(input_id_array, checkbox){
    for(const element_id of input_id_array) {
        let element = document.getElementById(element_id)
        // console.log(element)
        if (checkbox.checked) {
            element.closest("div").style.display = "";
        }
        else {
            element.closest("div").style.display = "none";
        }
    }
    console.log(`This is the new ${param_list}`)
}

// Given an array of input ids and a checkbox, make them hidden if checkbox is true
function hide_params(input_id_array, checkbox){
    for(const element_id of input_id_array) {
        let element = document.getElementById(element_id)
        if (checkbox.checked) {
            element.closest("div").style.display = "none";
        }
        else {
            element.closest("div").style.display = "";
        }
    }
    console.log(`This is the new ${param_list}`)
}

const cannot_negative_id_list = []
const must_int_id_list = []
// Checks if the correct parameters are filled in
function validate(){
    // Obtain list of input ids that are displayed
    // If any of their values are empty string alert
    for(const input of inputs) {
        // console.log(input.style.display)
        if(input.closest("div").style.display === "" && input.value === "" 
            && input.type !== "checkbox"){
            alert(`Please fill in the field of ${input.name}`);
            return false;
        }
        else if(input.closest("div").style.display === "") {
            cleaned_params[input.id] = input.value;
        }
    }
    return true;
}

// Sets the various parameters with some random input
function quicktest(param_list) {
    console.log(`This is the param_list used for quicktest
        ${param_list}`);
    reset();
    // Pass param list to a view function and expect a list of values to update input with
    fetch("/get_quicktest_input/", {
        method: "POST",
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(param_list)
    })

 
    // Parse data
   .then(response => response.json())

    // Operate on the JS data, basically a dictonary
    .then(data => 
        {
        for(const input_id of param_list)
            {
            html_input = document.getElementById(input_id);
            html_input.value = data[input_id]
            }

        })
}

// Obtain the a list of the input ids, those which are displayed
function get_param_list(){
    const input_ids = []
    for(const input of inputs)
        input_ids.push(input.id)
    return input_ids
}