// Default function for getting csrftoken
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

// This defines some buttons that call functions
const strategy_btn = document.getElementById("strategy")
const run_backtest_btn = document.getElementById("run_backtest")
const view_mcs_btn = document.getElementById("view_mcs_btn")

// The trigger of the buttons calling the function
strategy_btn.addEventListener("change", show_params)
run_backtest_btn.addEventListener("click", run_backtest)
view_mcs_btn.addEventListener("click", view_mcs)

// Shows strategy specific params and hides others
function show_params(){
    //  Turns chosen strategy's param visible and others invisible
    const all_strategy_params = document.querySelectorAll(".strategy_parameters");
    const chosen_strategy_id = this.value;
    all_strategy_params.forEach(div => {
        if (div.id === chosen_strategy_id){
            div.style.display = ""
        }
        else {
            div.style.display = "none";
        }
        })
}

// Runs backtest when run button is clicked and input passed
function run_backtest(){
    if (!validate()) {return;}
    graph_backtest()
    view_mcs_btn.disabled = false
}

// Checks if all the inputs of a strategy is passed
function validate(){
    // Determine the strategy
    const chosen_strategy_id = strategy_btn.value;
    // alert(`chosen strategy id is ${chosen_strategy_id}`);
    // alert(`strategy btn value is ${strategy_btn.value}`);
    if (chosen_strategy_id === "none") 
        {alert("Please select a strategy"); return;}
    // Check if any strategy params are empty
    const strategy_div = document.getElementById(chosen_strategy_id);
    const strategy_params = strategy_div.querySelectorAll('input')
    for(const input of strategy_params) {
        // alert(`${input.value}`)
        if (input.value == "") {
            alert(`Please enter the required fields ${input.name}`);
            return false
        } 
    }
    return true
}

// Convert input params into suitable format and pass to views function
// Stores the run_id too. As an obj
let run_id = {}
function graph_backtest() {
    // Clean the data
    const chosen_strategy_id = strategy_btn.value;
    const strategy_div = document.getElementById(chosen_strategy_id);
    const strategy_params = strategy_div.querySelectorAll('input');
    const cleaned_params = {};
    const ticker_lst = [];
    for(const input of strategy_params) {
        if (input.name.includes("ticker")){
            ticker_lst.push(input.value);
        }
        else {
            cleaned_params[input.name] = input.value;
        }
    }
    cleaned_params["tickers"] = ticker_lst;
    cleaned_params['strategy_name'] = chosen_strategy_id;
    alert(`These are the cleaned parameters to be passed ${cleaned_params}`)

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
    .then(data => {
        //  For graph
        const equity_graph_container = document.getElementById('equity_graph_container');
        // Clear data
        equity_graph_container.innerHTML = '';
        const range = document.createRange();
        const fragment = range.createContextualFragment(data["equity_graph_html"]);
        equity_graph_container.append(fragment);

        // For metrics
        const metrics_container_div = document.getElementById("metrics_container");
        const paragraphs = metrics_container_div.querySelectorAll("p");

        // Turn all metric paragraphs blank first
        for(const para of paragraphs) {
            para.style.display = "none";
        }
        // For each metric calculated
        // console.log(data["metrics"])
        for(const [key, value] of Object.entries(data["metrics"])) {
            // console.log(key)
            let paragraph = document.getElementById(key);
            // console.log(paragraph)
            paragraph.innerHTML = `${key}: ${value}`;
            paragraph.style.display = '';
        // Makes run_id a dict as needed by URLSearchParams
        run_id = {"run_id" : data["run_id"]};
        }
    })
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