// Default function for getting csrftoken
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}




// This is to handle the function that displays / hides strategy params
//  Whenever the strategy select is used
const strategy_btn = document.getElementById("strategy")
strategy_btn.addEventListener("change", show_params)

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
const run_backtest_btn = document.getElementById("run_backtest")
run_backtest_btn.addEventListener("click", run_backtest)
function run_backtest(){
    if (!validate()) {return;}
    console.log("Validate passed")
    graph_backtest()
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
function graph_backtest() {
    // Clean the data
    const chosen_strategy_id = strategy_btn.value;
    const strategy_div = document.getElementById(chosen_strategy_id);
    const strategy_params = strategy_div.querySelectorAll('input');
    const cleaned_params = {};
    const ticker_lst = []
    for(const input of strategy_params) {
        if (input.name.includes("ticker")){
            ticker_lst.push(input.value)
        }
        else {
            cleaned_params[input.name] = input.value
        }
    }
    cleaned_params["tickers"] = ticker_lst
    // alert(`These are the cleaned parameters to be passed ${cleaned_params}`)

    // Pass data to views function
    fetch("/backtest_graph/", {
        method: "POST",
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(cleaned_params)
    })
}