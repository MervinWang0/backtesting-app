// Default function for getting csrftoken
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

// Obtain the run_id
const querystring = window.location.search;
const url_params = new URLSearchParams(querystring);
const run_id = url_params.get("run_id");

// Define buttons that call functions
const jump_diffusion_checkbox = document.getElementById("is_jump_diffusion");
const regime_switching_checkbox = document.getElementById("is_regime_switching");
const is_t_checkbox = document.getElementById("is_t");
const run_mcs_btn = document.getElementById("run_mcs_btn");
const quicktest_all_btn = document.getElementById("quicktest_all_btn");
const quicktest_input_btn = document.getElementById("quicktest_input_btn");

// Instantiate variables for functions
const jump_params_id = ["std_log_jump_size", "mean_log_jump_size",
                        "exp_jumps"];
// Currently as mcs does not take in user input for daily mu and sigma,
// regime_switching params are none
const regime_switching_params_id = [];
const is_t_params_id = ["df"];
const checkbox_ids = ["is_jump_diffusion", "is_regime_switching",
    "is_t"
];

// Create an array of inputs. Obtained by selecting all input-fields of the input grid.
// This input list contains visible and hidden inputs
const input_grid = document.getElementById("input_container");
const param_divs = input_grid.querySelectorAll(".input-field");

// Add events to checkbox to show/hide params
jump_diffusion_checkbox.addEventListener("change", () => show_params(jump_params_id, jump_diffusion_checkbox));
regime_switching_checkbox.addEventListener("change", () => hide_params(regime_switching_params_id,
                                            regime_switching_checkbox));
is_t_checkbox.addEventListener("change", () => show_params(is_t_params_id, is_t_checkbox));

// Variable for output container
const output_container = document.getElementById("output_container");

// Add event to buttons to trigger actions
run_mcs_btn.addEventListener("click", run_graph);
quicktest_all_btn.addEventListener("click", () => quicktest(get_all_parameters()))
quicktest_input_btn.addEventListener("click", () => {
    input_params = remove_checkbox_ids(get_all_parameters());
    quicktest(input_params);
})

function run_graph(){
    if(!validate()){return;}
    graph_clear();
    bar_set_run();
    update_progress();
    graph_hide();
    hide_output();
    graph_mcs();
    graph_show()
    window.dispatchEvent(new Event('resize'));
}

function graph_hide() {
    const graph_container = document.getElementById("mcs_graph_container");
    graph_container.style.display = "none"
}

function graph_clear() {
    const graph_container = document.getElementById("mcs_graph_container");
    graph_container.innerHTML = "";
}

function graph_show() {
    const graph_container = document.getElementById("mcs_graph_container");
    graph_container.style.display = ""
}
// Takes in an array of ids and removes the checkbox ids
function remove_checkbox_ids(array) {
    for(const checkbox_id of checkbox_ids) {
        const index = array.indexOf(checkbox_id);
        if (index > -1) {
            array.splice(index, 1);
        }
    }
    // console.log(`This is the list of ids, which are visible,
    //     excluding the checkbox ids ${array}`);
    return array;
}
// Technically unnecessary if the mcs is only run with visible inputs,
// but as a fail safe, clear the hidden outputs. Also prevents manual
// change of checkboxes causing inputs to show values
function clear_hidden_output() {
    const input_container = document.getElementById("input_container");
    const input_container_divs = input_container.querySelectorAll("div");
    for (const input_div of input_container_divs) {
        const input_element = input_div.querySelector("input");
        if(input_element.closest('div').style.display == "none") {
            // console.log(`This is the element to clear value ${input_element.id}`);
            input_element.value = "";
        }
    }
}
function clear_input() {
    const input_container = document.getElementById("input_container");
    const input_container_divs = input_container.querySelectorAll("div");
    for (const input_div of input_container_divs) {
        const input_element = input_div.querySelector("input");
        input_element.value = "";
    }
}
// function reset() {

// }
// This function passes the run_id and mcs params 
// to a views function which calls mcs simulate and graphs it
function graph_mcs() {
    show_bar();
    bar_set_run();
    // Pass data to views function
    const cleaned_params = get_cleaned_params();
    // console.log(cleaned_params)
    fetch("/mcs_graph/", {
        method: "POST",
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(cleaned_params)
    })
    .then(response => response.json())
    .then(data => {
        // graph_show();
        bar_set_data_calculated();
        //  For graph
        const mcs_graph_container = document.getElementById('mcs_graph_container');
        // Clear data
        mcs_graph_container.innerHTML = '';
        let range = document.createRange();
        let fragment = range.createContextualFragment(data["mcs_graph_html"]);
        // console.log(`This is what html of graph looks like ${fragment}`);
        mcs_graph_container.append(fragment);
        // Make visible output
        // console.log(data);
        // console.log(data["mcs_metrics"]);
        show_output()
        bar_set_completed();
        range.createContextualFragment(add_rows(data["mcs_metrics"]))
                }
        )
    // Handles the case when the Mcs fails
    .catch(error => {
        console.error("MCS calculation failed", error);
        bar_set_error();
        });
}


const percentage_metrics = ["Total Return", "Mean Daily Return", "CAGR",
    "Volatility", "Max Drawdown", "Win Rate"
]
// This function builds the output table given the data. Returns undefined
function add_rows(data) {
    function isNumericString(str) {
        return !Number.isNaN(Number(str));
    }
    // These row identifier is used to determine which metric the val belongs to
    // Which is used to determine if it should be converted to %
    let row_identifier = '';
    let num_conversions = 0

    const tbody = output_container.querySelector('tbody');
    // Clear the table first
    tbody.innerHTML = '';
    // Data is an array of objects
    // console.log(`This is the data to build rows with ${JSON.stringify(data)}`)
    // console.log(data.length)
    data.forEach(obj => {
        // Create a row for each object
        const row = tbody.insertRow();
        // For each element of the object
        Object.values(obj).forEach(value => {
            // console.log(`This is the value should not be null ${value}`)
            if(isNumericString(value)) {
                // convert to number, operate, tu
                value = Number(value)
                if (percentage_metrics.includes(row_identifier)) {
                    num_conversions += 1;
                    value = value * 100;
                    value = value.toPrecision(5) + "%";
                }
                else {
                    value = Number(value).toPrecision(5);
                }

            }
            else {
                console.log(`${value} could not be converted to number`);
                row_identifier = value;
                // Does nothing if unable to convert to number
            }
            // Add content to cell
            const cell = row.insertCell();
            cell.textContent = value;
        });
    });

    // Testing to see that all the metrics are converted correctly
    // if (num_conversions !== percentage_metrics.length * 10) {
    //     throw new RangeError("The number of metrics converted " +
    //         "to percentages should be equal to number of percentage metrics"
    //     + `Number of conversions = ${num_conversions} vs `
    //     + `Number of percentage metrics = ${percentage_metrics.length * 11}` )
    // }
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
    console.log(`This is the new ${get_param_list()}`)
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
    console.log(`This is the new ${get_param_list()}`)
}

const cannot_negative_id_list = ["num_sims", "df", "exp_jumps", "std_log_jump_size"]
const must_int_id_list = ["num_sims", "df", "exp_jumps",]
const isIntegerString = (str) => Number.isInteger(Number(str)) && str.trim() !== "";
// Checks if the correct parameters are filled in
function validate(){
    // Obtain list of input ids that are displayed
    // If any of their values are empty string alert
    for(const input_id of get_param_list()) {
        const input = document.getElementById(input_id);
        // console.log(input.style.display)
        if(input.closest("div").style.display === "" && input.value === "" 
            && input.type !== "checkbox"){
            alert(`Please fill in the field of ${input.name}.`);
            return false;
        }
        else if (input.closest("div").style.display === "" &&
                cannot_negative_id_list.includes(input.id) && 
                input.value < 0) {
            alert(`${input.name} cannot be negative.`);
            return false;
        }
        else if (input.closest("div").style.display === "" &&
                must_int_id_list.includes(input.id) &&
                !isIntegerString(input.value)) {
            alert(`${input.name} must be an integer.`);
            return false;
        }
    }
    return true;
}

function get_cleaned_params() {
    // Store the cleaned params
    cleaned_params = {"run_id" : run_id};
    // Get the id of visible params in an array
    params = get_param_list();

    // Loop through visible params
    for (const element_id of params) {
        const element = document.getElementById(element_id);
        // For checkboxes special case
        if (element.type == "checkbox") {
            cleaned_params[element.id] = element.checked;
        }
        // Otherwise just pair id and value
        else {
            cleaned_params[element.id] = element.value;
        }
    }
    console.log(`These are the cleaned params to be 
        passed to mcs views = ${cleaned_params}`);
    return cleaned_params;
}
// This should independently turn on/off checkboxes,
// Fill in visible parameters,
// Hide non visible parametrs
function quicktest(param_list) {
    // console.log(`This is the param_list used for quicktest
    //     ${param_list}`);
    graph_clear();
    bar_set_reset();
    hide_output();
    graph_hide();

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
        // console.log("This is the data returned by quicktest\n");
        // console.log(JSON.stringify(data));
        for(const [key, value] of Object.entries(data)) {

            // The key is the id of the param, value is its value
            // console.log(`This is the key ${key}`)
            // console.log(`This is the value ${value}`)
            const element = document.getElementById(key);

            // First fill in the values
            element.value = value;

            // Make checkboxes turn off / on 
            if (element.type == "checkbox") {
                // .checked and not .value for visual change
                element.checked = value;

                // Event must be dispatched to trigger event listener
                const event = new Event('change');
                element.dispatchEvent(event);
            }
            }
        // Clear the params which are hidden
        // console.log(`Clearing hidden outputs`)
        clear_hidden_output();
        }
        )
}

// Obtain the a list of the input ids, those which are displayed
function get_param_list(){
    // console.log(`Obtaining the list of visible inputs`);
    const input_ids = [];
    // Input container is a div containing divs, which contain input elements
    const input_container = document.getElementById("input_container");
    const input_container_divs = input_container.querySelectorAll("div");
    for (const input_div of input_container_divs) {
        const input_element = input_div.querySelector("input");
        // console.log(`This is the input element ${input_element.id}`);
        // If the div containing the input is visible, add it to list
        if (input_element.closest("div").style.display == "") {
            input_ids.push(input_element.id);
        }
    }
    // console.log(`This is the list of visible inputs ${input_ids}`);
    return input_ids
}

// This returns a list of all param ids, visible or hidden
function get_all_parameters() {
    const input_ids = [];
    // Input container is a div containing divs, which contain input elements
    const input_container = document.getElementById("input_container");
    const input_container_divs = input_container.querySelectorAll("div");
    for (const input_div of input_container_divs) {
        const input_element = input_div.querySelector("input");
        input_ids.push(input_element.id);
    }
    // console.log(`This is the list of all inputs ${input_ids}`);
    return input_ids
}


// A Function to hide the output table
function hide_output() {
    const output_table = document.getElementById("output_container");
    output_table.style.display = "none";
}

// A Function to show the output table
function show_output() {
    const output_table = document.getElementById("output_container");
    output_table.style.display = "";
}

function show_bar() {
    const progress_wrapper = document.getElementById("progress-wrapper");
    progress_wrapper.style.display = "";
}

function hide_bar() {
    const progress_wrapper = document.getElementById("progress-wrapper");
    progress_wrapper.style.display = "none";
}
function bar_set_reset() {
    progress_bar.style.background = "linear-gradient(90deg, #3b82f6, #8b5cf6);";
    bar_state = "Monte Carlo Simulation Not Started"
    update_progress()
}
function bar_set_run() {
    progress_bar.style.background = "linear-gradient(90deg, #3b82f6, #8b5cf6);";
    progress_bar.style.animation = "width 0.3s ease;";
    bar_state = "Running Monte Carlo Simulation";
}

function bar_set_error() {
    bar_state = "Error";
}

function bar_set_data_calculated() {
    bar_state = "Data Calculated, Displaying Data";
}

function bar_set_completed() {
    bar_state = "Monte Carlo Simulation Finished";
}

// Progress Bar JS specific to backtest.html
let progress_bar = document.querySelector(".progress-bar");
let loading_text = document.querySelector(".loading-text");
let bar_width = 0;
let bar_state = "Monte Carlo Simulation Not Started";

function update_progress() {
    // progress_bar.style.background = "linear-gradient(90deg, #3b82f6, #8b5cf6);";
    // progress_bar.stylee.animation = "width 0.3s ease;";
    // console.log(`This is the state = ${bar_state}`)
    // console.log(`This is the width = ${bar_width}`)
    // Other functions will update state, and this function is called once per second.
    switch(bar_state) {
        case "Monte Carlo Simulation Not Started":
            bar_width = 0;
            progress_bar.style.background = "linear-gradient(90deg, #3b82f6, #8b5cf6);";
            break;
        case "Running Monte Carlo Simulation":
            bar_width = 30;
            progress_bar.style.background = "linear-gradient(90deg, #3b82f6, #8b5cf6);";
            break;
        case "Data Calculated, Displaying Data":
            bar_width = 80;
            progress_bar.style.background = "linear-gradient(90deg, #3b82f6, #8b5cf6);";
            break;
        case "Monte Carlo Simulation Finished":
            bar_width = 100;
            progress_bar.style.background = "linear-gradient(90deg, #3b82f6, #8b5cf6);";
            progress_bar.style.animation = "none";
            break;
        case "Error":
            hide_output();
            width = 0;
            progress_bar.style.background= "red"
            break;
        default:
            hide_output();
            bar_state = "Error"
            width = 0;
            progress_bar.style.background = "red"
            break;
    }
    // Updates the progress bar
    progress_bar.style.width = bar_width + "%";
    progress_bar.textContent = bar_width + "%";

    // Updates the loading text
    loading_text.textContent = bar_state;
    if(bar_state === "Monte Carlo Simulation Finished") {return;}
    if(bar_state === "Error") {return;}
    setTimeout(update_progress, 200);
}
