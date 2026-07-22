// Default function for getting csrftoken
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}
//ids declared here so that making a change in html only has to be changed here
// common ids
const asset_type_id = "asset_type";
const ticker_id = "ticker";
const strength_id = "strength";
const slippage_id = "slippage";
const initial_capital_id = "initial_capital";
const start_date_id = "start_date";
const end_date_id = "end_date";
const commission_id = "commission";

// Strategy specific
const short_window_id = "mac_short_window";
const long_window_id = "mac_long_window";
const rsi_window = "rsi_window";
const bollinger_window = "bollinger_window";
const z_window = "z_window";
const rsi_overbought = "rsi_overbought";
const rsi_oversold = "rsi_oversold";
const z_upper = "z_upper";
const z_lower = "z_lower"
const mean_reversion_logic = "mean_reversion_logic";
const macd_short = "macd_short";
const macd_medium = "macd_medium";
const macd_long = "macd_long";
const donchian_window = "donchian_window";
const roc_window = "roc_window";
const stoc_window = "stoc_window";

// This defines some buttons that call functions
const strategy_btn = document.getElementById("strategy_btn")
const run_backtest_btn = document.getElementById("run_backtest_btn")
const view_mcs_btn = document.getElementById("view_mcs_btn")
const quicktest_btn = document.getElementById("quicktest_btn")

// divs serving as containers
const progress_bar_div = document.getElementById("progress_bar_container")

// chosen strategy id and param list have to be mutable as they change each time strategy is changed
let chosen_strategy_id = strategy_btn.value;
let param_list = get_param_list();

// The trigger of the buttons calling the function
strategy_btn.addEventListener("change", change_strategy)
run_backtest_btn.addEventListener("click", run_backtest)
run_backtest_btn.addEventListener("click", show_output)
view_mcs_btn.addEventListener("click", view_mcs)
quicktest_btn.addEventListener("click", () => quicktest(param_list))

// Array of input elements, used to obtain their values from webpage
const strategy_params = [];
let output_params = [];

// These lists are for error checking the value of input
const cannot_negative_id_list = ["mac_short_window", "mac_long_window", 
    "strength", "commission", "slippage", "initial_capital", short_window_id,
long_window_id, rsi_window]
const must_int_id_list = ["mac_short_window", "mac_long_window"]

// run_id is used to pass the entry of the backtest to MCS webpage
let run_id = {}

// Used to convert metrics to more readable form
const percentage_outputs = ["Total Return", "Mean Daily Return", "CAGR",
    "Max Drawdown",
]

const common_parameters = [asset_type_id, ticker_id, strength_id, slippage_id,
    initial_capital_id, commission_id, start_date_id, end_date_id
]
const moving_avg_cross = [...common_parameters, short_window_id, long_window_id
];

const mean_reversion = [...common_parameters, rsi_window,
    bollinger_window, z_window, rsi_overbought, rsi_oversold, z_upper,
    z_lower, mean_reversion_logic
];

const macd = [...common_parameters, macd_short, macd_medium, macd_long];

const breakout = [...common_parameters, donchian_window];

const momentum = [...common_parameters, macd_short, macd_medium, macd_long,
    rsi_window
];
const rate_of_change = [...common_parameters, roc_window];

const stoch_osc = [...common_parameters, stoc_window];
// Get the element that serves as a container for inputs to hide/show
const input_container = document.getElementById("input_container")
function get_param_list(){
    let temp_param_list = [];
    // console.log(`This is the chosen strategy id ${chosen_strategy_id} `)
    switch(String(chosen_strategy_id)) {
        case "Moving Average Crossover":
            // console.log("moving average strat reached")
            temp_param_list = moving_avg_cross;
            break;
        case "Mean Reversion":
            temp_param_list = mean_reversion;
            break;
        case "MACD":
            temp_param_list = macd;
            break;
        case "Breakout":
            temp_param_list = breakout;
            break;
        case "Momentum":
            temp_param_list = momentum;
            break;
        case "Rate Of Change":
            temp_param_list = rate_of_change;
            break;
        case "Stochastic Oscillator":
            temp_param_list = stoch_osc;
            break;
    }
    // console.log(`This is the SMA list${SMA}`)
    // console.log(`This is the MR list${MR}`)
    // console.log(`This is the temp param list${temp_param_list}`)
    return temp_param_list
}

// Hides the outputs
function hide_output() {
        // divs stores the output fields
        const output_container_div = document.getElementById("output_container");
        output_container_div.style.display = "none";
        // const divs = output_container_div.querySelectorAll(".output-field");

        // // Make each div invisible
        // for(const div of divs) {
        //     div.style.display = "none";
        // }
}

function clear_input() {
    // Turns the value of each input field to blank
    const divs = input_container.querySelectorAll(".input-field");

        // Make each input blank 
        for(const div of divs) {
            div.querySelector("input").value = "";
        }
}
// Used when switching strategy, should hide, output, graph, progress bar,
// and set input params to empty
function reset() {
    // Turn the progress bar and graph invisible
    progress_bar_div.style.display = "none";
    equity_graph_container.style.display = "none";

    // Turns the progress bar to a blue background, in case of error.
    progress_bar.style.background = "linear-gradient(90deg, var(--color-white), var(--color-blue))";

    // Make the progress bar start from initial state
    state = "Backtest Not Run";

    // Turn output params invisible
    hide_output()

    // Turn each input field blank
    clear_input()
}


// Used to hide the parameters not valid to the chosen strategy
function change_strategy(){
    // Hide and clear params, and output metrics/graph
    reset();
    chosen_strategy_id = strategy_btn.value;

    // This turns the container holding inputs inivisble if strategy is none
    if (chosen_strategy_id !== "none") {
        input_container.style.display = "";
    }
    else {
        input_container.style.display = "none";
    }

    param_list = get_param_list();
    param_list.forEach(input_id => strategy_params.push(document.getElementById(input_id)));

    // console.log("Changing Strategy")
    // Iterate through the divs, and if the input id matches the params make it visible
    // Else it stays/becomes invisible
    const all_strategy_div = document.querySelectorAll(".input-field")
    all_strategy_div.forEach(element => {
        // console.log(param_list);
        // console.log(element);
        // console.log(element.querySelector("input").id);
        if(param_list.includes(element.querySelector("input").id)){
            element.style.display = "";
        }
        else{
            element.style.display = "none";
        }
        
    });
}

// Runs backtest when run button is clicked and input passed
function run_backtest(){
    upgrade_progress(); // Sets initial state of progress bar
    // Only show the bar after run backtest is clicked
    progress_bar_div.style.display = "";
    if (!validate()) {
        state = "Error"
        output_container.style.display = "none";
        progress_bar_div.style.display = "none";
        return;}
    else {
     // TODO create function for initializing clear state
    // state has to be reset in the case of multiple backtest runs occuring
    state = "Backtest Not Run";
    progress_bar.style.animation = "pulse 1.5s infinite";

    // When run_backtest occurs, the old graph should disappear, TODO create initial_state function
    equity_graph_container.innerHTML = '';
    graph_backtest();
    view_mcs_btn.disabled = false;
    }
}

// Checks if all the inputs of a strategy is passed
// TODO need to update the input iteration with global array and not the
// locally constructed array
function validate(){
const isIntegerString = (str) => Number.isInteger(Number(str)) && str.trim() !== "";
const is_visible = (input) => input.closest("div").style.display == ""
    for(const input of strategy_params) 
        {
            if(param_list.includes(input.id) && input.value == "" && is_visible(input)){
                alert(`Please enter the require fields ${input.name}`)
                return false;
            }
            // Negative number error handling
            if(cannot_negative_id_list.includes(input.id) && input.value < 0 && is_visible(input)){
                alert(`${input.name} cannot be negative`);
                return false;
            }
            // Integer number handling
            // console.log(!Number.isInteger(input.value))
            if(must_int_id_list.includes(input.id) && !isIntegerString(input.value) && is_visible(input)){
                alert(`${input.name} must be an integer`);
                return false;
            }
        }
    return true;
}

// clean_params is used to pass data to fetch requests
function clean_params(input_array) {
    // console.log("Cleaning params")
    // CLean the params
    const cleaned_params = {};

    // Ticker list is to handle situation of multiple tickers
    const ticker_lst = [];
    for(const input of strategy_params) {
        // console.log(`This is input name ${input.name}`)
        // console.log(`This is input value ${input.value}`)
        // console.log(`This is input id ${input.id}`)
        if (input.name.includes("ticker")){
            ticker_lst.push(input.value);
        }
        else {
            cleaned_params[input.name] = input.value;
        }
    }
    cleaned_params["tickers"] = ticker_lst;

    // Input is expected as a percentage but used in backtest as a multiple. 1% => 0.01
    cleaned_params["commission"] = cleaned_params["commission"] / 100;

    // Name is not taken as input so it has to be taken from button 
    cleaned_params['strategy_name'] = chosen_strategy_id;
    // console.log(`Cleaned params ${cleaned_params}`)
    return cleaned_params
}

// Does the heavy lifting of the webpage.
// The function sends the data to the appropriate views function.
// It then receives the data, and graphs it 
// TBD split metric cleaning? It may be too long
function graph_backtest() {
    // Set state, rather unnecessary as it's so fast it's not visible TBD if remove
    state = "Cleaning Parameters";

    cleaned_params = clean_params(strategy_params);
    // Testing
    // alert(`These are the cleaned parameters to be passed ${cleaned_params}`)
    // console.log(cleaned_params)

    // Update state, this state remains for a long time
    state = "Performing Backtest";
    // Pass data to views function
    fetch("/backtest_graph/", {
        method: "POST",
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(cleaned_params)
    })

    // Turns string into JS object
    .then(response => response.json())

    // Operate on the JS data, basically a dictonary
    .then(data => {
        // Update state
        state = "Backtest Calculated";

        //  For graph
        const equity_graph_container = document.getElementById('equity_graph_container');
        // Clear data
        const range = document.createRange();
        const fragment = range.createContextualFragment(data["equity_graph_html"]);
        equity_graph_container.append(fragment);
        equity_graph_container.style.display = "";

        // For metrics
        const output_container_div = document.getElementById("output_container");
        const divs = output_container_div.querySelectorAll(".output-field");

        // Make the value of each metric field an empty string 
        for(const div of divs) {
            para = div.querySelector("p");
            para.innerHTML = "";
        }

        // For each metric calculated turn it visible and place the value in it
        // console.log(data["metrics"])
        for(const [key, value] of Object.entries(data["metrics"])) {
            // console.log(key);
            let paragraph = document.getElementById(key);

            // Guard against the case where the element is not found
            if (paragraph == null) {continue;}

            // console.log(paragraph);
            // Convert some of the metrics to percentage
            if (percentage_outputs.includes(key)) {
                paragraph.innerHTML = `${(value * 100).toFixed(2)}%`;
            }
            else {
                paragraph.innerHTML = `${value.toFixed(4)}`;
            }
            // Make the div storing the metric visible
            paragraph.parentElement.style.display = '';
            // console.log(paragraph.parentElement);
        // Makes run_id a dict as needed by URLSearchParams
        run_id = {"run_id" : data["run_id"]};
        state = "Backtest Run Complete";
        }
    })
    // Handles the case when the backtest fails
    .catch(error => {
        console.error("Backtest calculation failed", error);
        state = "Error";
    });
}

// Simple function to open MCS link when mcs button clicked
function view_mcs() {
    // The disabled is set to false when run_backtest is executed
    if (!view_mcs_btn.disabled) {
        let url = "monte_carlo_simulation/"
        // console.log(run_id)
        const params = new URLSearchParams(run_id)
        const querystring = params.toString()
        url += "?" + querystring
        // console.log(querystring)
        // console.log(url)
        window.open(url, '_blank').focus()
    }
}

// Progress Bar JS specific to backtest.html
let progress_bar = document.querySelector(".progress-bar");
let loading_text = document.querySelector(".loading-text");
let width = 0;
let state = "Backtest Not Run"

// state is updated at various points of other functions which in turn updates bar
function upgrade_progress() {
    console.log(`This is the state = ${state}`)
    console.log(`This is the width = ${width}`)
    // Other functions will update state, and this function is called once per second.
    switch(state) {
        case "Backtest Not Run":
            width = 0;
            break;
        case "Cleaning Parameters":
            width = 10;
            break;
        case "Performing Backtest":
            width = 30;
            break;
        case "Backtest Calculated":
            width = 80;
            break;
        case "Backtest Run Complete":
            width = 100;
            // The return is just to stop the repeated calls of this fn
            // loading_text.style.animation = "none";
            progress_bar.style.animation = "none";
            break;
        case "Error":
            width = 0;
            progress_bar.style.background= "red"
            break;
        default:
            state = "Error"
            width = 0;
            progress_bar.style.background = "red"
            break;
    }
    // Updates the progress bar
    progress_bar.style.width = width + "%";
    progress_bar.textContent = width + "%";

    // Updates the loading text
    loading_text.textContent = state;
    if(state === "Backtest Run Complete") {return;}
    if(state === "Error") {return;}
    setTimeout(upgrade_progress, 50);
}

// Just a simple function that displays the output grid
function show_output() {
    let output_container = document.getElementById("output_container");
    output_container.style.display = "";
}

// Sets the various parameters with some random input
function quicktest(param_list) {
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